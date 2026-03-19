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

        self.info_bar.addText("▶▶▶Starting the search on the Marine Traffic website with Playwright Chromium...")

        self.playwright = await self.playwright_manager.start()
        
        self.browser_context = await self.playwright.chromium.launch_persistent_context(
            executable_path = str(self.playwright_dir / "chromium" / "chromium-1187" / "chrome-win" / "chrome.exe"),
            user_data_dir = str(self.profile_dir),
            headless = True,
            viewport = {"width": width, "height": height},
            user_agent = self.user_agent,
            extra_http_headers = {"Accept-Language": self.accept_lang},
            ignore_https_errors = True,
            args = ["--start-maximized","--disable-blink-features=AutomationControlled"],
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
                
                await self.page.close()
                
                self.page = None
                
                raise Exception()
        
        except Exception:
            
            self.page = None

            try:
                
                await self.browser_context.close()
                
            except Exception:
                pass
            
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
                        
                        await popup_locator.wait_for(timeout = timeout)
                        
                        self.log.debug("Consent popup found in iframe: %s" % frame.url)
                        
                        popup_found = True
                        
                        break
                    
                    except TimeoutError:
                        continue

            if popup_found is False:
                
                self.log.debug("No consent popup appeared on the page")
                
                return

            agree_button = popup_locator.locator("button.css-1yp8yiu")
            
            self.info_bar.addText("🔔 Cookie consent popup detected, trying to accept it...")
            
            try:
                
                await agree_button.click(timeout = timeout)
                
                self.log.info("Consent dialog detected and 'AGREE' button clicked successfully")
                
                self.info_bar.addText("✅ Cookie consent accepted")
                
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

            self.info_bar.addText("🔍 Search started for ship: %s" % ship_name)

            results_container = self.page.locator("div.MuiContainer-root").filter(has = self.page.locator("div.MuiListItem-root"))
    
            await results_container.wait_for(state = "visible", timeout = timeout)
            
            self.marine_traffic_list = []
            
            await self.collect_results(results_container, timeout = timeout)
            
            self.info_bar.addText("Finished the search: found a total of %d results for the name '%s'◀◀◀" % (
                len(self.marine_traffic_list),
                ship_name
                )
            )
            
        except TimeoutError:
            
            self.info_bar.addText("ℹ️ No results found or the results did not load in time")
            
            self.log.warning("No search results found or they did not load in time")
            
        except Exception as e:
            
            self.info_bar.addText("❌ Error while searching for ship: %s" % str(e))
            
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
                
                list_items = await results_container.locator("div.MuiListItem-root").all()
                
                for item in list_items:
                    
                    await self._pharse_list_item(item)
                    
                return

            self.log.info("Pagination detected -> collecting paginated results")

            last_page_btn = pagination.locator("button.MuiPaginationItem-page").last
            
            last_page_text = await last_page_btn.inner_text()
            
            total_pages = int(last_page_text)
            
            self.log.debug("Total pages detected: %d" % total_pages)

            next_btn = pagination.locator("button[aria-label='Go to next page']")

            current_page = 1

            while current_page <= total_pages:

                list_items = await results_container.locator("div.MuiListItem-root").all()
                
                self.log.debug("Found %d list items on page %d" % (
                    len(list_items), 
                    current_page
                    )
                )

                for idx, list_item in enumerate(list_items, start = 1):
                    
                    try:
                        await self._pharse_list_item(list_item)
                        
                        self.log.debug("Parsed item %d on page %d" % (
                            idx, 
                            current_page
                            )
                        )
                        
                    except Exception as e:
                        
                        self.log.warning("Item parse failed on page %d: %s" % (
                            current_page, 
                            str(e)
                            )
                        )

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
    
    async def _pharse_list_item(self, list_item: Locator):
        
        try:
            
            a_tags = await list_item.locator("a").all()

            a_tag = None
            href_value = None
            view_on_map_href = None
            ship_id = None

            if len(a_tags) > 0:
      
                a_tag = a_tags[0]
                
                href_value = await a_tag.get_attribute("href")
                
                if href_value is not None:
                    
                    ship_id_match = re.search(r"shipid:(\d+)", href_value)
                    
                    if ship_id_match is not None:
                        
                        ship_id = ship_id_match.group(1)
                        
                    else:
                        
                        ship_id = None

                if len(a_tags) > 1:
                    
                    view_on_map_href = await a_tags[1].get_attribute("href")

            if a_tag is None:
                
                a_tag = list_item
            
            h5_elements = await a_tag.locator("h5").all()
            
            h5_text = await h5_elements[0].inner_text() if len(h5_elements) > 0 else ""
            
            ship_name_cleaned = re.sub(r"(\(.*?\)|\[.*?\])", "", h5_text).strip()

            flag_spans = await a_tag.locator("span[role='img']").all()
            
            flag_value = None
            
            if len(flag_spans) > 0:
                
                flag_attr = await flag_spans[0].get_attribute("aria-label")
                
                if flag_attr is not None:
                    
                    flag_value = flag_attr.lower()

            p_elements = await a_tag.locator("p").all()
            
            info_text = await p_elements[0].inner_text() if len(p_elements) > 0 else ""

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
                
                ex_name_value = ex_name_match.group(1).strip()
                
                ship_name_cleaned = f"{ship_name_cleaned} Ex name: {ex_name_value}"

            self.marine_traffic_list.append(MarineTrafficData(
                id = None,
                ship_name = ship_name_cleaned,
                more_deatails_href = href_value,
                view_on_map_href = view_on_map_href,
                ship_id = int(ship_id) if ship_id is not None else None,
                type_name = type_value,
                flag = flag_value,
                mmsi = int(mmsi_value) if mmsi_value is not None else None,
                call_sign = call_sign_value,
                imo = int(imo_value) if imo_value is not None else None,
                reported_destination = None,
                matched_destination = None
                )
            )

        except Exception as e:
            
            self.log.exception("Error parsing list item: %s" % str(e))
    
    async def _extract_reported_time_and_location(self):
        
        try:
            
            block_locator = self.page.locator("#vesselDetails_summarySection")

            text = await block_locator.inner_text()

            location_match = re.search(r"located in the (.*?) \(reported", text)
            reported_match = re.search(r"reported (.*?)\)", text)

            location = location_match.group(1).strip() if location_match is not None else None
            reported = reported_match.group(1).strip() if reported_match is not None else None
            
            self.info_bar.addText("📍 Last known position: %s - reported: %s" % (
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
        