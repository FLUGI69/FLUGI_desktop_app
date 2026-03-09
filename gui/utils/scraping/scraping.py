import aiohttp
import asyncio
from yarl import URL
from bs4 import BeautifulSoup
from pydantic import BaseModel
from datetime import datetime
import typing as t
import logging

from utils.logger import LoggerMixin
from config import Config
from utils.dc.ship_info import ShipInfo

class WebScraper(LoggerMixin):

    log: logging.Logger

    @classmethod
    async def search_ship_by_name_on_mahart(cls, name: str, url: str) -> t.Type['post_response_body']:
        
        if url != "":
            
            params = {'name': name}

            try:
                
                url_obj = URL(url).with_query(params)
                
            except Exception as e:
                
                cls.log.error("Invalid URL or parameters: %s" % (str(e),))
                
                return post_response_body(status = "error", ship = [], error = "Invalid URL or parameters")

            timeout = aiohttp.ClientTimeout(
                sock_connect = Config.web_scraper.sock_connect, 
                sock_read = Config.web_scraper.sock_read
            )

            try:
                async with aiohttp.ClientSession(timeout = timeout) as session:
                    
                    headers = {
                        "User-Agent": "WebScraperBot/1.0"
                    }

                    async with session.post(str(url_obj), headers = headers) as response:
                        
                        if response.status != 200:
                            
                            cls.log.error("POST request failed: %s" % (str(response.status)))
                            
                            return post_response_body(
                                status = "error",
                                ship = [],
                                error = "POST request failed: %s" % str(response.status)
                            )

                        elif response.status == 200:
                            
                            html = await response.text()

                            if not html:
                                
                                cls.log.warning("Empty response received for ship name %s from %s" % (str(name), str(url_obj)))
                                
                                return post_response_body(status = "error", ship = [], error = "Empty response received")

                            cls.log.info("Successfully fetched data for ship name %s from %s" % (str(name), str(url_obj)))
                            
                            response = cls.__fetch_mahart_port_html(
                                html = html, 
                                ship_name = name
                            )
                            
                            cls.log.debug("POST response: %s" % str(response))
                            
                            return response

            except aiohttp.ClientError as e:
                
                cls.log.error("HTTP request failed: %s" % (str(e),))
                
                return post_response_body(status = "error", ship = [], error = "HTTP request failed")

            except asyncio.TimeoutError:
                
                cls.log.error("Request timed out after %s seconds" % (str(timeout.total)))
                
                return post_response_body(status = "error", ship = [], error = "Request timed out")

    @classmethod
    def __fetch_mahart_port_html(cls, html: str, ship_name: str) -> t.Type['post_response_body']:
        
        try:

            soup = BeautifulSoup(html, 'html.parser')
            
            ship_divs = soup.select('div.col-sm-12.sh-head')
            
            ships = []

            for div in ship_divs:
                
                name_div = div.find('div', class_ = 'sh1')
                
                if name_div and ship_name.lower() in name_div.text.lower():
                    
                    try:
                        arrival_date_str = div.find('div', class_='sh2').text.strip()
                        arrival_time_str = div.find('div', class_='sh3').text.strip()
                        port = div.find('div', class_='sh4').text.strip()
                        ponton = div.find('div', class_='sh5').text.strip()
                        departure_date_str = div.find('div', class_='sh6').text.strip()
                        departure_time_str = div.find('div', class_='sh7').text.strip()

                        arrival_dt = datetime.strptime(f"{arrival_date_str} {arrival_time_str}", "%Y.%m.%d %H:%M")
                        departure_dt = datetime.strptime(f"{departure_date_str} {departure_time_str}", "%Y.%m.%d %H:%M")

                        ships.append(ShipInfo(
                            name = name_div.text.strip(),
                            arrival_date = arrival_dt,
                            port = port,
                            ponton = ponton,
                            departure_date = departure_dt
                        ))

                    except Exception as e:
                        
                        cls.log.warning("Skipping row due to parsing error: %s" % str(e))
                        
                        continue

            if ships:
                
                return post_response_body(status = "success", ship = ships, error = "")
            
            else:
                
                return post_response_body(status = "error", ship = [], error = "No matching ship found")

        except Exception as e:
            
            cls.log.error("HTML parsing error: %s" % (str(e)))
            
            return post_response_body(status = "error", ship = [], error = "HTML parsing error")
       
class post_response_body(BaseModel):
    status: str
    ship: list[ShipInfo]
    error: str