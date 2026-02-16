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
        
        # Navigate to WhatsApp Web if not already there
        if 'web.whatsapp.com' not in self.driver.current_url:
            logger.info("Navigating to WhatsApp Web...")
            self.driver.get('https://web.whatsapp.com')
            
            # Wait for QR code scan or main interface
            logger.info("Waiting for WhatsApp Web to load (scan QR if needed)...")
            try:
                # Wait for either search box (logged in) or QR code (not logged in)
                self.wait.until(
                    lambda d: d.find_elements(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]') or
                             d.find_elements(By.XPATH, '//canvas[@aria-label]')
                )
                
                # If QR code is present, wait longer for scan
                if self.driver.find_elements(By.XPATH, '//canvas[@aria-label]'):
                    logger.info("QR Code detected - Please scan with your phone")
                    print("\n📱 SCAN QR CODE: Open WhatsApp on your phone and scan the QR code in Safari\n")
                    
                    # Wait up to 90 seconds for QR scan
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
            
            # Reset wait to normal timeout
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
            
            # Find and click search box
            search_box=self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
            ))
            
            # Clear any existing search
            search_box.click()
            time.sleep(0.5)
            search_box.send_keys(Keys.CONTROL + 'a')
            search_box.send_keys(Keys.BACKSPACE)
            time.sleep(0.5)
            
            # Type contact name
            logger.debug(f"Typing in search box: {contact_name}")
            for char in contact_name:
                search_box.send_keys(char)
                time.sleep(0.05)
            
            time.sleep(2)
            
            # Look for the contact in search results
            # Try multiple XPath strategies
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
                # Try pressing Enter as fallback (opens first result)
                logger.info("Trying to open first search result...")
                search_box.send_keys(Keys.ENTER)
                time.sleep(1.5)
                return True
            
            # Click on the contact
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
            
            # Try Native first if on macOS and mode is auto/native
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
                            # Fall through to web mode
                    else:
                        logger.warning("WhatsApp Desktop app not responding or not installed.")
                        if mode == 'native':
                            return "❌ WhatsApp Desktop app not available"
                        # Fall through to web mode
                except Exception as ne:
                    logger.error(f"Critical error in Native WhatsApp handler: {ne}", exc_info=True)
                    if mode == 'native':
                        return f"❌ Native WhatsApp automation error: {ne}"
                    # Fall through to web mode

            # Fallback to Web Mode
            logger.info(f"Using Web Mode with {browser}")
            self._ensure_driver(browser=browser)
            
            # Search for and open the contact
            if not self._search_contact(phone_number_or_name):
                return f"❌ Failed to find contact: {phone_number_or_name}"
            
            # Wait for message input box to be available
            logger.info("Waiting for message input box...")
            message_box=self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
            ))
            
            message_box.click()
            time.sleep(0.3)
            
            logger.info(f"Sending message: {message[:50]}{'...' if len(message) > 50 else ''}")
            
            # For long messages, code blocks, or special formatting, use clipboard paste
            # This is more reliable than send_keys for complex content
            if len(message) > 100 or '\n' in message or any(char in message for char in ['`', '{', '}', '[', ']']):
                logger.info("Using clipboard paste for complex message")
                import pyperclip
                from selenium.webdriver.common.action_chains import ActionChains
                
                # Copy message to clipboard
                pyperclip.copy(message)
                
                # Paste using keyboard shortcut (Cmd+V on macOS)
                actions = ActionChains(self.driver)
                actions.key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                time.sleep(0.5)
            else:
                # For short simple messages, send_keys is fine
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
