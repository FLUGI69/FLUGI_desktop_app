import random
import hashlib
import re
import typing as t
import logging
from pathlib import Path
import sys

from playwright.async_api import expect, BrowserContext, Page, TimeoutError, Locator

from utils.handlers.widgets.info_bar import InfoBar
from utils.logger import LoggerMixin
from utils.dc.marine_traffic.search_data import MarineTrafficData
from services.backgound_tasks.playwright_context_manager import PlayWrightContextManager
from config import Config

class AsyncPlaywright(LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self,
        playwright_manager: PlayWrightContextManager,
        info_bar: InfoBar
        ):
        
        self.playwright_manager = playwright_manager
        
        self.info_bar = info_bar
        
        self.playwright = None
        
        self.browser_context: BrowserContext | None = None
        
        self.page: Page | None = None
        
        self.marine_traffic_list: t.List[MarineTrafficData] = []
        
        self.playwright_dir = Path(sys.executable).parent / "_internal" / "gui" / "playwright" \
            if getattr(sys, 'frozen', False) else Path(Config.marine_traffic.playwright_dir)
    
    def make_dir(self):
        
        self.playwright_dir.mkdir(parents = True, exist_ok = True)
        
        profiles_dir = self.playwright_dir / "playwright_profiles"
        
        profiles_dir.mkdir(parents = True, exist_ok = True)

        self.user_agent = random.choice(Config.marine_traffic.user_agents)
        
        self.accept_lang = random.choice(Config.marine_traffic.langs)
        
        profile_hash = hashlib.md5(f"{self.user_agent}|{self.accept_lang}".encode()).hexdigest()

        self.profile_dir = profiles_dir / profile_hash
        
        self.profile_dir.mkdir(parents = True, exist_ok = True)
    
    def random_viewport(self):
        
        return random.choice(Config.marine_traffic.viewports)
    
    async def build_browser_context(self):
        
        self.make_dir()
    
        width, height = self.random_viewport()

        self.playwright = await self.playwright_manager.start()
        
        self.browser_context = await self.playwright.chromium.launch_persistent_context(
            executable_path = str(self.playwright_dir / "chromium" / "chromium-1187" / "chrome-win" / "chrome.exe"),
            user_data_dir = str(self.profile_dir),
            headless = Config.marine_traffic.headless,
            viewport = {"width": width, "height": height},
            user_agent = self.user_agent,
            extra_http_headers = {"Accept-Language": self.accept_lang},
            ignore_https_errors = True,
            args = [
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-first-run",
            ],
        )
    
    async def ensure_page(self) -> Page:
        """
        Ensures that the Playwright persistent browser context and page are usable.
        Returns a Page object that is guaranteed to be alive.

        - If the browser context is None, a new context and page will be created.
        - If a page already exists but its URL is not "about:blank", the page will be closed
        and the context rebuilt to ensure a clean page.
        - This guarantees that every returned Page is in a clean state (about:blank)
        suitable for fast searches.
        - Any exceptions during page creation or context handling are caught, the context is
        rebuilt, and a new Page is created.
        
        Returns:
            Page -> usable Page object with URL set to about:blank
        """
        if self.browser_context is None:
        
            await self.build_browser_context()
        
        try:
            
            self.page = self.browser_context.pages[0] if len(self.browser_context.pages) > 0 else await self.browser_context.new_page()

            if self.page.url != "about:blank":
                
                await self.page.goto("about:blank", wait_until = "commit")
        
        except Exception:
            
            self.page = None

            try:
                
                await self.browser_context.close()
                
            except Exception:
                pass
            
            self.browser_context = None
            
            await self.build_browser_context()
            
            self.page = self.browser_context.pages[0] if len(self.browser_context.pages) > 0 else await self.browser_context.new_page()
           
        return self.page
    
    async def handle_cookies_banner(self, timeout: int = 4000):
        """
        Robustly handles GDPR / cookie consent popup.
        Works with iframe or shadow DOM.
        """
        try:
            
            popup_found = False

            popup_locator = self.page.locator("#qc-cmp2-ui")
            
            try:
                
                await popup_locator.wait_for(timeout = timeout)
                
                popup_found = True
                
            except TimeoutError:
                
                popup_found = False

            if popup_found is False:
                
                for frame in self.page.frames:
                    
                    popup_locator = frame.locator("#qc-cmp2-ui")
                    
                    try:
                        
                        await popup_locator.wait_for(timeout = 500)
                        
                        self.log.debug("Consent popup found in iframe: %s" % frame.url)
                        
                        popup_found = True
                        
                        break
                    
                    except TimeoutError:
                        continue

            if popup_found is False:
                
                self.log.debug("No consent popup appeared on the page")
                
                return

            agree_button = popup_locator.locator("button.css-1yp8yiu")
            
            self.info_bar.addText("🔔 Cookie consent felugró ablak észlelve, megpróbálom elfogadni...")
            
            try:
                
                await agree_button.click(timeout = timeout)
                
                self.log.info("Consent dialog detected and 'AGREE' button clicked successfully")
                
                self.info_bar.addText("✅ Cookie consent elfogadva")
                
            except TimeoutError:
                
                self.log.debug("Consent dialog exists, but 'AGREE' button was not found or clickable")

        except Exception as e:
            
            self.log.exception("Exception occurred while handling consent dialog: %s" % str(e))
    
    async def handle_searching(self, 
        ship_name: str,
        timeout: int = 5000
        ):
        
        try:

            toolbar_input = self.page.locator("input.MuiInputBase-input")
            
            await toolbar_input.wait_for(state = "visible", timeout = timeout)
            
            await toolbar_input.click()

            await toolbar_input.fill(ship_name)
            
            await toolbar_input.press("Enter")

            self.info_bar.addText("🔍 Keresés indítva a hajóra: %s" % ship_name)

            results_container = self.page.locator("div.MuiContainer-root").filter(has = self.page.locator("div.MuiListItem-root"))
    
            await results_container.wait_for(state = "visible", timeout = timeout)
            
            self.marine_traffic_list = []
            
            await self.collect_results(results_container, timeout = timeout)
            
            self.info_bar.addText("Végeztem a kereséssel: összesen %d találatot találtam a '%s' névvel◀◀◀" % (
                len(self.marine_traffic_list),
                ship_name
                )
            )
            
        except TimeoutError:
            
            self.info_bar.addText("ℹ️ Nincs találat vagy a találatok nem töltődtek be időben")
            
            self.log.warning("No search results found or they did not load in time")
            
        except Exception as e:
            
            self.info_bar.addText("❌ Hiba a hajó keresésénél: %s" % str(e))
            
            self.log.exception("Error during ship search: %s" % str(e))
    
    async def collect_results(self, results_container: Locator, timeout: int = 1500):
        """
        Collects and parses all paginated list items from the results container.
        Uses the 'next page' navigation button to iterate through pages sequentially,
        which correctly handles dynamic MUI pagination with ellipsis.
        """
        
        try:
            pagination = results_container.locator("nav[aria-label='pagination navigation']")
            
            try:
                await pagination.wait_for(state = "visible", timeout = timeout)
                
            except TimeoutError:
                
                self.log.info("No pagination detected -> collecting single page results")
                
                await self._extract_page_items(results_container)
                    
                return

            self.log.info("Pagination detected -> collecting paginated results")

            last_page_btn = pagination.locator("button.MuiPaginationItem-page").last
            
            last_page_text = await last_page_btn.inner_text()
            
            total_pages = int(last_page_text)
            
            self.log.debug("Total pages detected: %d" % total_pages)

            next_btn = pagination.locator("button[aria-label='Go to next page']")

            current_page = 1

            while current_page <= total_pages:

                count = await self._extract_page_items(results_container)
                
                self.log.debug("Extracted %d items from page %d" % (count, current_page))

                if current_page >= total_pages:
                    break

                prev_first_text = await results_container.locator("div.MuiListItem-root").first.text_content()

                await next_btn.click()

                try:
                    
                    await expect(
                        results_container.locator("div.MuiListItem-root").first
                    ).not_to_have_text(prev_first_text, timeout = 2000)
                
                except Exception:
                    
                    self.log.debug("Content check skipped after clicking next page")

                current_page += 1

            self.log.info("Finished collecting %d pages of results" % total_pages)

        except Exception as e:
            
            self.log.exception("Error collecting paginated results: %s" % (str(e)))
    
    async def _extract_page_items(self, results_container: Locator) -> int:
        """Extract all list items from the current page using a single JS evaluate call."""
        
        raw_items = await results_container.evaluate("""(container) => {
            const items = container.querySelectorAll('.MuiListItem-root');
            return Array.from(items).map(item => {
                const aTags = item.querySelectorAll('a');
                let hrefValue = null, viewOnMapHref = null, shipId = null;
                
                if (aTags.length > 0) {
                    hrefValue = aTags[0].getAttribute('href');
                    if (hrefValue) {
                        const m = hrefValue.match(/shipid:(\\d+)/);
                        shipId = m ? m[1] : null;
                    }
                    if (aTags.length > 1) {
                        viewOnMapHref = aTags[1].getAttribute('href');
                    }
                }
                
                const aTag = aTags.length > 0 ? aTags[0] : item;
                const h5 = aTag.querySelector('h5');
                const h5Text = h5 ? h5.innerText : '';
                
                const flagSpan = aTag.querySelector("span[role='img']");
                const flagValue = flagSpan ? flagSpan.getAttribute('aria-label') : null;
                
                const p = aTag.querySelector('p');
                const infoText = p ? p.innerText : '';
                
                const allPTags = aTag.querySelectorAll('p');
                const fullInfoText = Array.from(allPTags).map(el => el.innerText).join(', ');
                
                return { h5Text, hrefValue, viewOnMapHref, shipId, flagValue, infoText: fullInfoText || infoText };
            });
        }""")
        
        for raw in raw_items:
            
            self._parse_raw_item(raw)
        
        return len(raw_items)
    
    def _parse_raw_item(self, raw: dict):
        """Parse a raw JS-extracted dict into MarineTrafficData."""
        
        try:
            
            h5_text = raw.get("h5Text", "")
            
            ship_name_cleaned = re.sub(r"(\(.*?\)|\[.*?\])", "", h5_text).strip()
            
            info_text = raw.get("infoText", "")

            type_match = re.search(r"Type:\s*([^,]+)", info_text)
            
            type_value = type_match.group(1).strip() if type_match else None

            mmsi_match = re.search(r"MMSI:\s*(\d+)", info_text)
            
            mmsi_value = mmsi_match.group(1) if mmsi_match else None

            call_sign_match = re.search(r"Call Sign:\s*([\w\d]+)", info_text)
            
            call_sign_value = call_sign_match.group(1) if call_sign_match else None

            imo_match = re.search(r"IMO:\s*(\d+)", info_text)
            
            imo_value = imo_match.group(1) if imo_match else None

            ex_name_match = re.search(r"Ex Name:\s*(.+)", info_text, re.I)
            
            if ex_name_match is not None:
                
                ship_name_cleaned = f"{ship_name_cleaned} Ex name: {ex_name_match.group(1).strip()}"

            ship_id = raw.get("shipId")
            
            flag_value: str = raw.get("flagValue")

            self.marine_traffic_list.append(MarineTrafficData(
                id = None,
                ship_name = ship_name_cleaned,
                more_deatails_href = raw.get("hrefValue"),
                view_on_map_href = raw.get("viewOnMapHref"),
                ship_id = int(ship_id) if ship_id else None,
                type_name = type_value,
                flag = flag_value.lower() if flag_value else None,
                mmsi = int(mmsi_value) if mmsi_value else None,
                callsign = call_sign_value,
                imo = int(imo_value) if imo_value else None,
                reported_destination = None,
                matched_destination = None,
                position_received = None
                )
            )

        except Exception as e:
            
            self.log.warning("Failed to parse raw item: %s" % str(e))
    
    async def _extract_reported_time_and_location(self):
        
        try:
            
            block_locator = self.page.locator("#vesselDetails_summarySection")

            text = await block_locator.inner_text()

            location_match = re.search(r"located in the (.*?) \(reported", text)
            reported_match = re.search(r"reported (.*?)\)", text)

            location = location_match.group(1).strip() if location_match is not None else None
            reported = reported_match.group(1).strip() if reported_match is not None else None
            
            self.info_bar.addText("📍 Utolsó helyzet: %s – jelentve: %s" % (
                location, 
                reported
                )
            )
            
            self.log.debug("Extracted reported location and time: location = '%s', reported = '%s'" % (
                location if location is not None else "Unknown",
                reported if reported is not None else "Unknown"
                )
            )

        except Exception as e:
            
            self.log.exception("Failed extracting summary location/time: %s" % str(e))

    async def scrape_single_vessel_details(self, item: MarineTrafficData) -> MarineTrafficData:
        """
        Visit a single vessel's detail page and extract missing fields 
        (callsign, reported_destination, matched_destination, position_received, etc.)
        """
        
        field_label = {
            "flag": "Flag",
            "mmsi": "MMSI",
            "callsign": "Call sign",
            "imo": "IMO",
            "type_name": "General vessel type",
            "reported_destination": "Reported destination",
            "matched_destination": "Matched destination",
            "position_received": "Position received",
        }
        
        if item.more_deatails_href is None:
            return item
        
        detail_url = Config.marine_traffic.base_url + item.more_deatails_href
        
        self.info_bar.addText("🔍 %s részletes adatainak lekérése..." % item.ship_name)
        
        response = await self.page.goto(
            url = detail_url,
            wait_until = "domcontentloaded"
        )
        
        if response is None or response.status != 200:
            
            self.log.warning("Detail page returned status %s for %s" % (
                response.status if response else "None", 
                item.ship_name
            ))
            
            return item
        
        await self.handle_cookies_banner()
        
        ais_found = False
        
        try:
            
            await self.page.wait_for_selector("#vesselDetails_aisInfoSection", timeout = 8000)
            
            ais_found = True
            
        except Exception:
            
            self.log.debug("AIS section not found for %s on first attempt, retrying..." % item.ship_name)
        
        if not ais_found:
            
            response = await self.page.goto(
                url = detail_url,
                wait_until = "domcontentloaded"
            )
            
            if response is not None and response.status == 200:
                
                try:
                    
                    await self.page.wait_for_selector("#vesselDetails_aisInfoSection", timeout = 8000)
                    
                except Exception:
                    
                    self.log.debug("AIS section not found for %s after retry, trying with available data" % item.ship_name)
        
        missing_fields = {
            field: label for field, label in field_label.items()
            if getattr(item, field, None) is None
        }
        
        if len(missing_fields) > 0:
            
            extracted = await self.page.evaluate("""(labels) => {
                const result = {};
                for (const [field, label] of Object.entries(labels)) {
                    const th = Array.from(document.querySelectorAll('th'))
                        .find(el => el.textContent.trim() === label);
                    if (th) {
                        const td = th.nextElementSibling;
                        if (td) {
                            const firstText = td.childNodes[0];
                            result[field] = firstText ? firstText.textContent.trim() : td.innerText.trim();
                        }
                    }
                }
                return result;
            }""", missing_fields)
            
            for field, value in extracted.items():
                
                if value and value != "-":
                    
                    self.log.debug("Found data for '%s' on %s: %s" % (field, item.ship_name, value))
                    
                    setattr(item, field, value)
        
        self.log.debug("Detail scrape done for %s: callsign=%s, reported_dest=%s, matched_dest=%s, pos_received=%s" % (
            item.ship_name,
            item.callsign,
            item.reported_destination,
            item.matched_destination,
            item.position_received
            )
        )
        
        self.info_bar.addText("✅ %s adatai kinyerve" % item.ship_name)
        
        return item
        