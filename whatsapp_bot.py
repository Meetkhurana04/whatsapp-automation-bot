import os
import time
import logging
import json
import base64
import uuid
import tempfile
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
import pickle
import shutil

logger = logging.getLogger(__name__)

class WhatsAppBot:
    def __init__(self, device_id='default', headless=True, profile_dir=None):
        self.device_id = device_id
        self.headless = headless
        self.driver = None
        self.session_dir = f"sessions/{device_id}"
        self.qr_code_path = f"qr_codes/{device_id}_qr.png"
        self.is_authenticated = False
        self.whatsapp_url = "https://web.whatsapp.com/"
        self.profile_dir = str(profile_dir) if profile_dir else f"{self.session_dir}/user_data"
        
        os.makedirs(self.session_dir, exist_ok=True)
        os.makedirs("qr_codes", exist_ok=True)
        os.makedirs(self.profile_dir, exist_ok=True)
        
        logger.info(f"WhatsApp bot initialized for device: {device_id}")
        self.last_activity = time.time()
    
    def __del__(self):
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
            if hasattr(self, 'device_id'):
                logger.info(f"WhatsApp bot destroyed for device: {self.device_id}")
        except Exception as e:
            logger.error(f"Error destroying WhatsApp bot: {str(e)}")
    
    def _find_chrome_executable(self):
        possible_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/opt/google/chrome/chrome'
        ]
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found Chrome at: {path}")
                return path
        chrome_path = shutil.which('google-chrome') or shutil.which('google-chrome-stable') or shutil.which('chromium')
        if chrome_path:
            logger.info(f"Found Chrome using which: {chrome_path}")
            return chrome_path
        logger.error("Chrome executable not found")
        return None
    
    def _find_chromedriver_executable(self):
        possible_paths = [
            '/usr/local/bin/chromedriver',
            '/usr/bin/chromedriver',
            '/opt/chromedriver',
            '/app/chromedriver'
        ]
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found ChromeDriver at: {path}")
                return path
        chromedriver_path = shutil.which('chromedriver')
        if chromedriver_path:
            logger.info(f"Found ChromeDriver using which: {chromedriver_path}")
            return chromedriver_path
        logger.error("ChromeDriver executable not found")
        return None
    
    def _setup_driver(self):
        try:
            chrome_path = self._find_chrome_executable()
            chromedriver_path = self._find_chromedriver_executable()
            
            if not chrome_path:
                logger.error("Chrome executable not found")
                return False
            if not chromedriver_path:
                logger.error("ChromeDriver executable not found")
                return False
            
            chrome_options = Options()
            chrome_options.binary_location = chrome_path
            
            user_data_dir = os.path.join(self.session_dir, "user_data")
            os.makedirs(user_data_dir, exist_ok=True)
            os.chmod(self.session_dir, 0o700)  # Secure permissions
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-features=TranslateUI")
            chrome_options.add_argument("--disable-ipc-flooding-protection")
            chrome_options.add_argument("--disable-background-networking")
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--disable-sync")
            chrome_options.add_argument("--disable-translate")
            chrome_options.add_argument("--hide-scrollbars")
            chrome_options.add_argument("--metrics-recording-only")
            chrome_options.add_argument("--mute-audio")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--safebrowsing-disable-auto-update")
            chrome_options.add_argument("--ignore-certificate-errors")
            chrome_options.add_argument("--ignore-ssl-errors")
            chrome_options.add_argument("--ignore-certificate-errors-spki-list")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-session-crashed-bubble")
            chrome_options.add_argument("--disable-password-generation")
            chrome_options.add_argument("--disable-password-manager-reauthentication")
            chrome_options.add_argument("--single-process")
            chrome_options.add_argument("--no-zygote")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            chrome_options.add_argument(f"--profile-directory=Default")
            chrome_options.add_argument(f"--remote-debugging-port={9222 + hash(self.device_id) % 1000}")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
            
            if self.headless:
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--disable-gpu")
                logger.info(f"Running in headless mode for device: {self.device_id}")
            
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0,
                "profile.managed_default_content_settings.images": 2,
                "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,
                "profile.default_content_setting_values.media_stream_mic": 2,
                "profile.default_content_setting_values.media_stream_camera": 2,
                "profile.default_content_setting_values.geolocation": 2,
                "profile.default_content_setting_values.desktop_notification": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(5)
            
            logger.info(f"Chrome WebDriver initialized successfully for device: {self.device_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to setup WebDriver for device {self.device_id}: {str(e)}")
            return False
    
    def initialize_session(self):
        try:
            if not self._setup_driver():
                return {'success': False, 'error': 'Failed to setup WebDriver'}
            
            logger.info(f"Loading WhatsApp Web for device: {self.device_id}")
            self.driver.get(self.whatsapp_url)
            time.sleep(3)
            
            if self._check_authentication():
                logger.info(f"Device {self.device_id} already authenticated")
                return {'success': True, 'qr_required': False}
            
            qr_code_present = self._wait_for_qr_code()
            if qr_code_present:
                logger.info(f"QR code detected for device: {self.device_id}")
                self._save_qr_code()
                auth_success = self._wait_for_authentication(timeout=300)
                if auth_success:
                    logger.info(f"Authentication successful for device: {self.device_id}")
                    return {'success': True, 'qr_required': True}
                else:
                    logger.warning(f"Authentication timeout for device: {self.device_id}")
                    return {'success': False, 'error': 'Authentication timeout'}
            else:
                if self._check_authentication():
                    logger.info(f"Device {self.device_id} authenticated without QR scan")
                    return {'success': True, 'qr_required': False}
                return {'success': False, 'error': 'Unable to load WhatsApp Web'}
        except Exception as e:
            logger.error(f"Error initializing session for device {self.device_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _wait_for_qr_code(self, timeout=30):
        try:
            qr_selectors = [
                'canvas[aria-label="Scan me!"]',
                'div[data-ref] canvas',
                'canvas[aria-label*="QR"]'
            ]
            WebDriverWait(self.driver, timeout).until(any_element_present(*qr_selectors))
            logger.info(f"QR code found")
            return True
        except TimeoutException:
            return False
    
    def _save_qr_code(self):
        try:
            qr_selectors = [
                'canvas[aria-label="Scan me!"]',
                'div[data-ref] canvas',
                'canvas[aria-label*="QR"]'
            ]
            for selector in qr_selectors:
                try:
                    qr_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    canvas_base64 = self.driver.execute_script(
                        "return arguments[0].toDataURL('image/png').substring(21);",
                        qr_element
                    )
                    with open(self.qr_code_path, 'wb') as f:
                        f.write(base64.b64decode(canvas_base64))
                    logger.info(f"QR code saved for device: {self.device_id}")
                    return True
                except NoSuchElementException:
                    continue
            logger.warning(f"Could not save QR code for device: {self.device_id}")
            return False
        except Exception as e:
            logger.error(f"Error in _save_qr_code: {str(e)}")
            return False
    
    def _wait_for_authentication(self, timeout=300):
        try:
            end_time = time.time() + timeout
            while time.time() < end_time:
                if self._check_authentication():
                    self.is_authenticated = True
                    return True
                time.sleep(2)
            return False
        except Exception as e:
            logger.error(f"Error waiting for authentication: {str(e)}")
            return False
    
    def _check_authentication(self):
        try:
            authenticated_selectors = [
                'div[data-testid="chat-list"]',
                'div[aria-label="Chat list"]',
                'div[data-testid="side"]',
                'header[data-testid="chatlist-header"]'
            ]
            WebDriverWait(self.driver, 5).until(any_element_present(*authenticated_selectors))
            self.is_authenticated = True
            return True
        except TimeoutException:
            return False
    
    def send_message(self, phone_number, message=None, media_path=None):
        try:
            if not self.driver:
                init_result = self.initialize_session()
                if not init_result['success']:
                    return init_result
            
            if not self.is_authenticated and not self._check_authentication():
                init_result = self.initialize_session()
                if not init_result['success']:
                    return init_result
            
            clean_phone = ''.join(filter(str.isdigit, phone_number))
            if not clean_phone.startswith('91') and len(clean_phone) == 10:
                clean_phone = '91' + clean_phone
            
            chat_url = f"https://web.whatsapp.com/send?phone={clean_phone}"
            logger.info(f"Navigating to chat for number: {phone_number[:5]}*****")
            self.driver.get(chat_url)
            
            if not self._wait_for_chat_to_load():
                return {'success': False, 'error': 'Failed to load chat interface'}
            
            if media_path and os.path.exists(media_path):
                if not self._send_media(media_path):
                    logger.warning(f"Failed to send media, continuing with text message")
            
            if message:
                if not self._send_text_message(message):
                    return {'success': False, 'error': 'Failed to send text message'}
            
            logger.info(f"Message sent successfully to {phone_number[:5]}*****")
            return {'success': True}
        except Exception as e:
            logger.error(f"Error sending message to {phone_number[:5]}*****: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _wait_for_chat_to_load(self, timeout=30):
        try:
            chat_selectors = [
                'div[data-testid="conversation-compose-box-input"]',
                'div[contenteditable="true"][data-tab="10"]',
                'div[role="textbox"]'
            ]
            WebDriverWait(self.driver, timeout).until(any_element_present(*chat_selectors))
            time.sleep(1)
            return True
        except TimeoutException:
            return False
    
    def _send_text_message(self, message):
        try:
            input_selectors = [
                'div[data-testid="conversation-compose-box-input"]',
                'div[contenteditable="true"][data-tab="10"]',
                'div[role="textbox"]'
            ]
            message_box = None
            for selector in input_selectors:
                try:
                    message_box = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not message_box:
                logger.error("Could not find message input box")
                return False
            
            message_box.click()
            time.sleep(0.5)
            lines = message.split('\n')
            for i, line in enumerate(lines):
                message_box.send_keys(line)
                if i < len(lines) - 1:
                    message_box.send_keys(Keys.SHIFT + Keys.ENTER)
            time.sleep(0.5)
            message_box.send_keys(Keys.ENTER)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error sending text message: {str(e)}")
            return False
    
    def _send_media(self, media_path):
        try:
            attachment_selectors = [
                'div[data-testid="clip"]',
                'span[data-testid="clip"]',
                'div[title="Attach"]'
            ]
            attachment_btn = None
            for selector in attachment_selectors:
                try:
                    attachment_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not attachment_btn:
                logger.error("Could not find attachment button")
                return False
            
            attachment_btn.click()
            time.sleep(1)
            file_input_selectors = [
                'input[accept*="image"]',
                'input[type="file"]'
            ]
            file_input = None
            for selector in file_input_selectors:
                try:
                    file_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not file_input:
                logger.error("Could not find file input")
                return False
            
            absolute_path = os.path.abspath(media_path)
            file_input.send_keys(absolute_path)
            time.sleep(2)
            send_selectors = [
                'span[data-testid="send"]',
                'div[data-testid="send"]',
                'button[data-testid="send"]'
            ]
            send_btn = None
            for selector in send_selectors:
                try:
                    send_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if send_btn:
                send_btn.click()
                time.sleep(2)
                return True
            else:
                logger.error("Could not find send button for media")
                return False
        except Exception as e:
            logger.error(f"Error sending media: {str(e)}")
            return False
    
    def get_session_status(self):
        try:
            if not self.driver:
                return 'not_initialized'
            if self._check_authentication():
                return 'authenticated'
            elif self._wait_for_qr_code(timeout=5):
                return 'qr_required'
            else:
                return 'unknown'
        except Exception as e:
            logger.error(f"Error getting session status: {str(e)}")
            return 'error'
    
    def get_qr_code_path(self):
        return self.qr_code_path if os.path.exists(self.qr_code_path) else None
    
    def close(self):
        try:
            if self.driver:
                logger.info(f"Closing WhatsApp bot session for device: {self.device_id}")
                self.driver.quit()
                self.driver = None
                self.is_authenticated = False
                if os.path.exists(self.qr_code_path):
                    os.remove(self.qr_code_path)
        except Exception as e:
            logger.error(f"Error closing session for device {self.device_id}: {str(e)}")
    
    def __del__(self):
        try:
            if hasattr(self, 'device_id'):
                logger.info(f"Cleaning up WhatsApp bot for device: {self.device_id}")
            self.close()
        except Exception as e:
            if hasattr(self, 'device_id'):
                logger.error(f"Error in __del__ for device {self.device_id}: {str(e)}")
            else:
                logger.error(f"Error in __del__: {str(e)}")

def any_element_present(*selectors):
    def condition(driver):
        for selector in selectors:
            try:
                if driver.find_element(By.CSS_SELECTOR, selector):
                    return True
            except NoSuchElementException:
                pass
        return False
    return condition