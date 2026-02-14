import logging
import time
import os
from typing import List, Dict, Optional, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException, WebDriverException
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class YahooFinanceScraper:
    """
    A robust scraper for Yahoo Finance 'Most Active' stocks using Selenium.
    Encapsulates navigation, interaction, and data extraction logic.
    """

    BASE_URL = "https://finance.yahoo.com/"
    
    # Locators
    NAV_CONTAINER = (By.ID, "navigation-container")
    MARKETS_MENU = (By.XPATH, "//*[@id='navigation-container']//*[self::a or self::span][normalize-space()='Markets' or contains(normalize-space(), 'Markets')]")
    STOCKS_MENU = (By.XPATH, "//*[@id='navigation-container']//*[self::a or self::span][normalize-space()='Stocks' or contains(normalize-space(), 'Stocks')]")
    TRENDING_MENU = (By.XPATH, "//*[@id='navigation-container']//*[self::a or self::span][normalize-space()='Trending' or contains(normalize-space(), 'Trending')]")
    MOST_ACTIVE_TAB = (By.ID, "tab-most-active")
    
    TABLE = (By.CSS_SELECTOR, "table")
    TABLE_ROWS = (By.CSS_SELECTOR, "table tbody tr")
    NEXT_BUTTON = (By.XPATH, "//*[@id='main-content-wrapper']/section[1]/div/div[4]/div[3]/button[3]")

    def __init__(self, headless: bool = False):
        """
        Initialize the scraper with a Chrome driver.
        
        Args:
            headless: Whether to run the browser in headless mode.
        """
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.add_argument("--headless")
        self.options.add_argument("--start-maximized")
        self.options.add_argument("--disable-infobars")
        self.options.add_argument("--disable-extensions")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Use system chromium-driver for Streamlit Cloud compatibility
        # On Streamlit Cloud, chromium-driver is installed via packages.txt
        chromium_driver_path = os.getenv('CHROMIUM_DRIVER_PATH', '/usr/bin/chromedriver')
        
        try:
            service = ChromeService(executable_path=chromium_driver_path)
            self.driver = webdriver.Chrome(service=service, options=self.options)
        except Exception as e:
            logger.warning(f"Failed to use system chromium-driver at {chromium_driver_path}: {e}")
            logger.info("Falling back to default driver...")
            # Fallback to default (for local development)
            self.driver = webdriver.Chrome(options=self.options)
        
        self.wait = WebDriverWait(self.driver, 15)
        logger.info("Browser initialized successfully.")

    def _wait_for_page_load(self, timeout: int = 5) -> None:
        """Wait for the document ready state to be complete."""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            logger.warning(f"Page load timeout for URL: {self.driver.current_url}")

    def _wait_visible(self, locator: tuple, timeout: int = 5) -> Any:
        """Wait for an element to be visible."""
        return WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located(locator))

    def _wait_clickable(self, locator: tuple, timeout: int = 5) -> Any:
        """Wait for an element to be clickable."""
        return WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable(locator))

    def _hover(self, element: Any) -> None:
        """Hover over a web element."""
        ActionChains(self.driver).move_to_element(element).pause(0.5).perform()

    def _safe_click(self, locator: tuple, timeout: int = 10) -> None:
        """Safely click an element by scrolling it into view first."""
        try:
            element = self._wait_clickable(locator, timeout)
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
            time.sleep(0.5) # Short pause for stability
            element.click()
        except (TimeoutException, StaleElementReferenceException) as e:
            logger.error(f"Failed to click element {locator}: {e}")
            raise

    def navigate_to_most_active(self) -> None:
        """Navigate through the menus to reach the 'Most Active' stocks page."""
        try:
            logger.info(f"Navigating to {self.BASE_URL}")
            self.driver.get(self.BASE_URL)
            self._wait_for_page_load()

            # Wait for navigation container
            self._wait_visible(self.NAV_CONTAINER)

            # Markets Menu
            markets = self._wait_visible(self.MARKETS_MENU)
            self._hover(markets)
            logger.info("Hovered over 'Markets' menu.")

            # Stocks Menu
            stocks = self._wait_visible(self.STOCKS_MENU)
            self._hover(stocks)
            logger.info("Hovered over 'Stocks' menu.")

            # Trending Menu
            trending = self._wait_clickable(self.TRENDING_MENU)
            trending.click()
            logger.info("Clicked 'Trending' menu.")
            self._wait_for_page_load()

            # Click Most Active Tab
            self._safe_click(self.MOST_ACTIVE_TAB)
            logger.info("Clicked 'Most Active' tab.")
            self._wait_for_page_load()

        except Exception as e:
            logger.error(f"Error during navigation: {e}")
            logger.error(traceback.format_exc())
            raise

    def scrape_current_page(self) -> List[Dict[str, str]]:
        """Scrape stock data from the current page's table."""
        data = []
        try:
            # Ensure table is present
            self._wait_visible(self.TABLE)
            rows = self.driver.find_elements(*self.TABLE_ROWS)
            
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 10:
                    continue
                
                stock_data = {
                    "symbol": cols[0].text.strip(),
                    "name": cols[1].text.strip(),
                    "price": cols[3].text.strip(),
                    "change": cols[4].text.strip(),
                    "volume": cols[6].text.strip(),
                    "market_cap": cols[8].text.strip(),
                    "pe_ratio": cols[9].text.strip()
                }
                data.append(stock_data)

        except StaleElementReferenceException:
            logger.warning("Stale element encountered during scraping. Retrying page...")
            time.sleep(1)
            return self.scrape_current_page()
        except Exception as e:
            logger.error(f"Error scraping page: {e}")
        
        return data

    def go_to_next_page(self) -> bool:
        """
        Attempt to click the 'Next' button.
        Returns True if successful, False if button not found or disabled.
        """
        try:
            # Capture first row text to verify page transition
            first_rows = self.driver.find_elements(*self.TABLE_ROWS)
            first_row_check = first_rows[0].text if first_rows else None

            # Find and click next button
            # Note: The specific locator for 'Next' can be tricky on Yahoo Finance.
            # We assume the locator provided (button[3]) is correct for the 'Next' arrow.
            btn = self._wait_clickable(self.NEXT_BUTTON, timeout=5)
            
            # Check if button is disabled (if applicable, though Yahoo mostly hides it)
            if "disabled" in btn.get_attribute("class"):
                return False

            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            self.driver.execute_script("arguments[0].click();", btn)
            
            # Wait for table to update
            if first_row_check:
                WebDriverWait(self.driver, 10).until(
                    lambda d: self._has_table_changed(first_row_check)
                )
            
            return True
        except TimeoutException:
            logger.info("No 'Next' button found or clickable. End of pagination.")
            return False
        except Exception as e:
            logger.error(f"Error navigating to next page: {e}")
            return False

    def _has_table_changed(self, old_first_row_text: str) -> bool:
        """Check if the table content has changed after navigation."""
        try:
            rows = self.driver.find_elements(*self.TABLE_ROWS)
            if not rows:
                return False
            return rows[0].text != old_first_row_text
        except StaleElementReferenceException:
            return False

    def close(self):
        """Close the browser instance."""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed.")

    def run(self):
        """
        Main execution method.
        Yields tuple (page_num, total_rows, current_data_snapshot) for progress tracking.
        """
        all_data = []
        page_num = 1
        
        try:
            self.navigate_to_most_active()
            
            while True:
                logger.info(f"Scraping page {page_num}...")
                page_data = self.scrape_current_page()
                all_data.extend(page_data)
                logger.info(f"Collected {len(page_data)} rows from page {page_num}. Total: {len(all_data)}")
                
                # Yield progress update
                yield page_num, len(all_data), all_data
                
                if not self.go_to_next_page():
                    break
                    
                page_num += 1
                
        except Exception as critical_error:
            logger.critical(f"Critical failure: {critical_error}")
            logger.critical(traceback.format_exc())
            # Don't raise here, let the caller handle partial data if needed, 
            # or re-raise if strictly required. 
            # For generator, we stop yielding.
        finally:
            self.close()

if __name__ == "__main__":
    scraper = YahooFinanceScraper(headless=True)
    data = []
    print("Starting scraper...")
    for page, total, current_data in scraper.run():
        data = current_data
        print(f"Progress: Page {page} done, {total} rows collected.")
    
    # Optional: Save to CSV or Process Logic
    print(f"Scraping completed. Total records: {len(data)}")
