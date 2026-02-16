"""
Enhanced WhatsApp Web Client with robust automation
Handles contact search, message sending, and error recovery
"""

import time
import urllib.parse
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from core.logger import get_logger
from .driver import WhatsAppDriver
from core.platform_utils import get_os

logger=get_logger(__name__)

class WhatsAppClient:
    """Enhanced WhatsApp automation client with Native and Web support"""
    
    def __init__(self):
        self.driver=None
        self.wait=None
        self.os = get_os()
    
    def _ensure_driver(self, browser='chrome'):
        """Ensure driver is initialized and on WhatsApp Web"""
        if not self.driver:
            self.driver=WhatsAppDriver.get_driver(browser=browser)
            self.wait=WebDriverWait(self.driver, 45)
        
        if 'web.whatsapp.com' not in self.driver.current_url:
            logger.info("Navigating to WhatsApp Web...")
            self.driver.get('https://web.whatsapp.com')
            
            logger.info("Waiting for WhatsApp Web to load (scan QR if needed)...")
            try:
                self.wait.until(
                    lambda d: d.find_elements(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]') or
                             d.find_elements(By.XPATH, '//canvas[@aria-label]')
                )
                
                if self.driver.find_elements(By.XPATH, '//canvas[@aria-label]'):
                    logger.info("QR Code detected - Please scan with your phone")
                    print("\n📱 SCAN QR CODE: Open WhatsApp on your phone and scan the QR code in Safari\n")
                    
                    self.wait=WebDriverWait(self.driver, 90)
                    self.wait.until(EC.presence_of_element_located(
                        (By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
                    ))
                    logger.info("QR Code scanned successfully")
                    print("✅ Connected to WhatsApp Web\n")
                    time.sleep(3)
                    
            except TimeoutException:
                logger.error("Timeout waiting for WhatsApp Web to load")
                raise Exception("WhatsApp Web failed to load. Please check your internet connection.")
            
            self.wait=WebDriverWait(self.driver, 45)
        
        try:
            self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
            ))
            time.sleep(1)
        except TimeoutException:
            logger.warning("Search box not immediately available, refreshing...")
            self.driver.refresh()
            time.sleep(3)
            self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
            ))
            self.wait=WebDriverWait(self.driver, 45)
    
    def _search_contact(self, contact_name):
        """
        Search for a contact by name
        
        Args:
            contact_name: Name or phone number to search
            
        Returns:
            bool: True if contact found and opened
        """
        try:
            logger.info(f"Searching for contact: {contact_name}")
            
            logger.info("Waiting for search box...")
            try:
                search_box = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"][@data-tab="3"] | //div[@aria-label="Search input textbox"]')
                ))
            except TimeoutException:
                 logger.warning("Standard search box not found, trying fallback...")
                 search_box = self.driver.find_elements(By.XPATH, '//div[@contenteditable="true"]')[0]

            
            search_box.click()
            time.sleep(0.5)
            
            modifier = Keys.COMMAND if self.os == 'macos' else Keys.CONTROL
            search_box.send_keys(modifier + 'a')
            search_box.send_keys(Keys.BACKSPACE)
            time.sleep(0.5)
            
            logger.debug(f"Typing in search box: {contact_name}")
            for char in contact_name:
                search_box.send_keys(char)
                time.sleep(0.05)
            
            time.sleep(2)
            
            contact_xpaths=[
                f'//span[@title="{contact_name}"]',
                f'//span[contains(@title, "{contact_name}")]',
                f'//div[@role="listitem"]//span[contains(text(), "{contact_name}")]',
            ]
            
            contact_element=None
            for xpath in contact_xpaths:
                try:
                    contact_element=self.driver.find_element(By.XPATH, xpath)
                    if contact_element:
                        logger.debug(f"Found contact using xpath: {xpath}")
                        break
                except NoSuchElementException:
                    continue
            
            if not contact_element:
                logger.warning(f"Contact '{contact_name}' not found in search results")
                logger.info("Trying to open first search result...")
                search_box.send_keys(Keys.ENTER)
                time.sleep(1.5)
                return True
            
            logger.info(f"Clicking on contact: {contact_name}")
            contact_element.click()
            time.sleep(1.5)
            
            return True
            
        except TimeoutException:
            logger.error("Search box not found - WhatsApp Web may not be loaded")
            return False
        except Exception as e:
            logger.error(f"Error searching for contact: {e}")
            return False
    
    def send_message(self, phone_number_or_name, message, browser='chrome', mode='web'):
        """
        Send a WhatsApp message to a contact
        
        Args:
            phone_number_or_name: Phone number (with country code) or contact name
            message: Message text to send
            browser: Browser to use for web mode ('chrome' or 'safari')
            mode: 'auto', 'native', or 'web'
            
        Returns:
            str: Success or error message
        """
        try:
            logger.info(f"Sending message to: {phone_number_or_name} (Mode: {mode})")
            
            if self.os == 'macos' and mode in ['auto', 'native']:
                try:
                    from .native_mac import open_whatsapp_native, send_message_simple
                    
                    logger.info("Attempting native WhatsApp automation (Simplified Mode)...")
                    if open_whatsapp_native():
                        success, result_msg = send_message_simple(phone_number_or_name, message)
                        if success:
                            logger.info(f"Native automation succeeded: {result_msg}")
                            return f"✅ Message sent via Native WhatsApp to {phone_number_or_name}"
                        else:
                            logger.warning(f"Native automation failed: {result_msg}")
                            if mode == 'native':
                                return result_msg
                    else:
                        logger.warning("WhatsApp Desktop app not responding or not installed.")
                        if mode == 'native':
                            return "❌ WhatsApp Desktop app not available"
                except Exception as ne:
                    logger.error(f"Critical error in Native WhatsApp handler: {ne}", exc_info=True)
                    if mode == 'native':
                        return f"❌ Native WhatsApp automation error: {ne}"

            if browser == 'chrome' and self.os == 'macos':
                pass
            elif self.os == 'macos' and not browser:
                 logger.info("Defaulting to Safari on macOS for better stability")
                 browser = 'safari'
            
            logger.info(f"Using Web Mode with {browser}")
            try:
                self._ensure_driver(browser=browser)
            except Exception as driver_error:
                if 'Allow remote automation' in str(driver_error):
                    return (
                        "❌ Safari automation not enabled.\n"
                        "Quick setup: Safari → Preferences → Advanced → Show Develop menu\n"
                        "Then: Safari → Develop → Allow Remote Automation"
                    )
                raise
            
            if not self._search_contact(phone_number_or_name):
                return f"❌ Failed to find contact: {phone_number_or_name}"
            
            logger.info("Waiting for message input box...")
            try:
                message_box=self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"] | //div[@aria-label="Type a message"]')
                ))
            except TimeoutException:
                logger.warning("Standard message box not found, trying fallback...")
                editables = self.driver.find_elements(By.XPATH, '//div[@contenteditable="true"]')
                if len(editables) >= 2:
                    message_box = editables[-1]
                else:
                    raise Exception("Message input box not found")
            
            message_box.click()
            time.sleep(0.3)
            
            logger.info(f"Sending message: {message[:50]}{'...' if len(message) > 50 else ''}")
            
            if len(message) > 100 or '\n' in message or any(char in message for char in ['`', '{', '}', '[', ']']):
                logger.info("Using clipboard paste for complex message")
                import pyperclip
                from selenium.webdriver.common.action_chains import ActionChains
                
                pyperclip.copy(message)
                
                actions = ActionChains(self.driver)
                actions.key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                time.sleep(0.5)
            else:
                message_box.send_keys(message)
                time.sleep(0.3)
            
            logger.info("Sending message with Enter key...")
            message_box.send_keys(Keys.ENTER)
            time.sleep(1)
            
            success_msg=f"✅ Message sent via WhatsApp Web to {phone_number_or_name}"
            logger.info(success_msg)
            return success_msg
            
        except TimeoutException as e:
            error_msg=f"❌ Timeout: Could not load WhatsApp Web"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_str=str(e)
            if "Remote Automation" in error_str:
                error_msg="❌ Safari not configured. Enable Remote Automation in Safari settings."
            else:
                error_msg=f"❌ Error: {error_str[:100]}"
            logger.error(f"WhatsApp error: {error_str}")
            return error_msg
    
    def close(self):
        """Close the WhatsApp driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WhatsApp driver closed")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
