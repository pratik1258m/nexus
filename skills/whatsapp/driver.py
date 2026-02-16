from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from core.logger import get_logger
import os

logger=get_logger(__name__)

class WhatsAppDriver:
    _instance=None
    _driver=None

    @classmethod
    def get_driver(cls, browser='chrome'):
        if cls._driver is not None:
            try:
                _ = cls._driver.current_url
                current_browser = cls._driver.name.lower()
                if (browser == 'safari' and 'safari' not in current_browser) or \
                   (browser == 'chrome' and 'chrome' not in current_browser):
                    logger.info(f"Switching browser from {current_browser} to {browser}")
                    cls._driver.quit()
                    cls._driver = None
            except Exception:
                logger.debug('Driver found but unresponsive, cleaning up...')
                try:
                    cls._driver.quit()
                except Exception:
                    pass
                cls._driver=None
        
        if cls._driver is None:
            cls._driver=cls._init_driver(browser)
        return cls._driver

    @staticmethod
    def _init_driver(browser):
        logger.info(f'Initializing {browser.capitalize()} Driver for WhatsApp...')
        try:
            if browser == 'safari':
                driver = webdriver.Safari()
                driver.maximize_window()
                logger.info('Safari driver initialized successfully')
                return driver
            else:
                options=Options()
                
                nexus_profile_dir = os.path.expanduser('~/.nexus/chrome_profile')
                os.makedirs(nexus_profile_dir, exist_ok=True)
                
                options.add_argument(f'--user-data-dir={nexus_profile_dir}')
                options.add_argument('--profile-directory=Default')
                
                options.add_argument('--start-maximized')
                options.add_argument('--disable-blink-features=AutomationControlled')
                
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--remote-debugging-port=9222')
                
                options.add_experimental_option('excludeSwitches', ['enable-automation'])
                options.add_experimental_option('useAutomationExtension', False)
                
                logger.info(f'Using dedicated Nexus Chrome profile: {nexus_profile_dir}')
                
                service=Service(ChromeDriverManager().install())
                driver=webdriver.Chrome(service=service, options=options)
                logger.info('Chrome driver initialized successfully with persistent profile')
                return driver
        except Exception as e:
            logger.error(f'Failed to initialize {browser}: {e}')
            if browser == 'safari':
                logger.error("Please enable 'Allow Remote Automation' in Safari -> Develop menu")
            else:
                logger.error("Please install Chrome browser or run: pip install webdriver-manager")
            raise Exception(f"{browser.capitalize()} driver failed: {e}")
