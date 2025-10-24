import os
import sys
import time
import logging
import subprocess
import json
import socket
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

VAHAN_URL = "https://vahan.parivahan.gov.in/vahan/vahan/ui/login/login.xhtml"
CHROME_DEBUG_PORT = 9222  # Port for Chrome debugging

# Global driver instance
driver_instance = None
is_logged_in = False  # Track login status

# File to persist session info across backend restarts
SESSION_FILE = os.path.join(os.path.dirname(__file__), '.vahan_session.json')

def save_session_info():
    """Save session info to file"""
    try:
        session_data = {
            'has_driver': driver_instance is not None,
            'is_logged_in': is_logged_in,
            'timestamp': time.time()
        }
        with open(SESSION_FILE, 'w') as f:
            json.dump(session_data, f)
        safe_print(f"[SESSION] Saved session info")
    except Exception as e:
        safe_print(f"[SESSION] Error saving session: {e}")

def load_session_info():
    """Load session info from file"""
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                session_data = json.load(f)
            
            # Check if session is recent (within 1 hour)
            if time.time() - session_data.get('timestamp', 0) < 3600:
                safe_print(f"[SESSION] Loaded session info: {session_data}")
                return session_data
        return None
    except Exception as e:
        safe_print(f"[SESSION] Error loading session: {e}")
        return None

def clear_session_info():
    """Clear session info file"""
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
            safe_print("[SESSION] Cleared session info")
    except Exception as e:
        safe_print(f"[SESSION] Error clearing session: {e}")

def safe_print(message):
    """Print messages safely handling unicode"""
    try:
        logger.info(message)
    except UnicodeEncodeError:
        cleaned_message = message.encode('ascii', errors='ignore').decode('ascii')
        logger.info(f"[UNICODE_ERROR] {cleaned_message}")
    except Exception as e:
        logger.info(f"[LOGGING_ERROR] Message could not be logged: {str(e)}")

def is_chrome_debugging_available():
    """
    Check if Chrome is running with debugging port 9222.
    Returns True if available, False otherwise.
    Does NOT create any browser instance.
    """
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', CHROME_DEBUG_PORT))
        sock.close()
        return result == 0
    except Exception:
        return False

def try_connect_to_existing_chrome():
    """
    Try to connect to an existing Chrome instance with debugging enabled.
    Returns driver if successful, None otherwise.
    ONLY connects to Chrome with debugging port, does NOT open new browser.
    """
    try:
        # First check if debugging port is available
        if not is_chrome_debugging_available():
            safe_print("[CONNECT] No Chrome with debugging port detected on port 9222")
            return None
        
        safe_print("[CONNECT] Debugging port 9222 is active, attempting to connect...")
        
        options = uc.ChromeOptions()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{CHROME_DEBUG_PORT}")
        
        # Create driver that connects to existing Chrome
        # This should ONLY connect, not create new browser
        driver = uc.Chrome(options=options, use_subprocess=False, version_main=None)
        
        # Verify connection by getting current URL
        try:
            _ = driver.current_url
            safe_print("[CONNECT] ✅ Successfully connected to existing Chrome instance!")
            return driver
        except Exception as e:
            safe_print(f"[CONNECT] Connected but cannot communicate: {str(e)[:100]}")
            try:
                driver.quit()
            except:
                pass
            return None
        
    except Exception as e:
        safe_print(f"[CONNECT] Connection failed: {str(e)[:100]}")
        return None

def create_vahan_driver():
    """
    Create a Chrome driver with fallback mechanisms for version compatibility.
    Specifically configured for Vahan website automation.
    Uses remote debugging port to survive backend restarts.
    """
    # First try to connect to existing Chrome instance
    existing_driver = try_connect_to_existing_chrome()
    if existing_driver:
        return existing_driver
    
    attempt_number = 1
    
    # Base options for all attempts
    def get_base_options():
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--ignore-certificate-errors")
        
        # Additional stability options
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--dns-prefetch-disable")
        options.add_argument("--disable-features=VizDisplayCompositor")
        
        # Enable remote debugging (allows reconnection after backend restart)
        options.add_argument(f"--remote-debugging-port={CHROME_DEBUG_PORT}")
        
        # Set user agent
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.210 Safari/537.36")
        
        # Set preferences to help with network issues
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
        }
        options.add_experimental_option("prefs", prefs)
        
        return options
    
    # Strategy 1: Auto-detect Chrome version
    try:
        safe_print(f"[DRIVER] Attempt {attempt_number}: Auto-detecting Chrome version...")
        options = get_base_options()
        return uc.Chrome(options=options, version_main=None)
    except Exception as e:
        safe_print(f"[DRIVER] Attempt {attempt_number} failed: {str(e)[:200]}...")
        attempt_number += 1
    
    # Strategy 2: Try with Chrome version 140
    try:
        safe_print(f"[DRIVER] Attempt {attempt_number}: Using Chrome version 140...")
        options = get_base_options()
        return uc.Chrome(options=options, version_main=140)
    except Exception as e:
        safe_print(f"[DRIVER] Attempt {attempt_number} failed: {str(e)[:200]}...")
        attempt_number += 1
    
    # Strategy 3: Use webdriver_manager
    try:
        safe_print(f"[DRIVER] Attempt {attempt_number}: Using webdriver_manager...")
        chromedriver_path = ChromeDriverManager().install()
        safe_print(f"[DRIVER] Downloaded ChromeDriver to: {chromedriver_path}")
        
        options = get_base_options()
        return uc.Chrome(options=options, driver_executable_path=chromedriver_path)
    except Exception as e:
        safe_print(f"[DRIVER] Attempt {attempt_number} failed: {str(e)[:200]}...")
        attempt_number += 1
    
    # Strategy 4: Try other common Chrome versions
    for version in [139, 138, 137, 136]:
        try:
            safe_print(f"[DRIVER] Attempt {attempt_number}: Trying Chrome version {version}...")
            options = get_base_options()
            return uc.Chrome(options=options, version_main=version)
        except Exception as e:
            safe_print(f"[DRIVER] Chrome version {version} failed: {str(e)[:100]}...")
            attempt_number += 1
    
    # All strategies failed
    error_msg = (
        "❌ Chrome Driver Initialization Failed!\n\n"
        "🔍 This is typically caused by a version mismatch between Chrome browser and ChromeDriver.\n\n"
        "🛠️  SOLUTIONS (try in order):\n"
        "1. UPDATE CHROME: Update your Chrome browser to the latest version\n"
        "2. RESTART: Close all Chrome instances and restart your computer\n"
        "3. UPDATE PACKAGES: Run 'pip install --upgrade undetected-chromedriver selenium webdriver-manager'\n"
    )
    raise Exception(error_msg)

def check_browser_status():
    """
    Check if browser is already open and if user is logged in.
    Only checks existing driver instance, does NOT open new browser.
    Attempts to reconnect to existing Chrome ONLY if one is running with debugging port.
    Returns dict with browser_open, logged_in status.
    """
    global driver_instance, is_logged_in
    
    # If no driver, try to connect to existing Chrome instance (but don't create new one)
    if not driver_instance:
        safe_print("[CHECK] No driver instance, checking for existing Chrome with debugging port...")
        
        # Quick check if debugging port is available (fast, no browser creation)
        if not is_chrome_debugging_available():
            safe_print("[CHECK] ℹ️  No Chrome with debugging port found (normal if you haven't clicked 'Start' yet)")
            return {
                "browser_open": False,
                "logged_in": False,
                "message": "No browser instance found. Click 'Start' to open browser."
            }
        
        # Debugging port is available, try to connect
        try:
            existing_driver = try_connect_to_existing_chrome()
            if existing_driver:
                driver_instance = existing_driver
                safe_print("[CHECK] ✅ Reconnected to existing Chrome instance!")
                # Continue to check status below
            else:
                safe_print("[CHECK] ⚠️  Debugging port active but cannot connect")
                return {
                    "browser_open": False,
                    "logged_in": False,
                    "message": "Cannot connect to browser"
                }
        except Exception as e:
            safe_print(f"[CHECK] Connection error: {str(e)[:100]}")
            return {
                "browser_open": False,
                "logged_in": False,
                "message": "No browser instance found"
            }
    
    # We have a driver instance, check its status
    try:
        # Check if driver is still alive
        current_url = driver_instance.current_url
        safe_print(f"[CHECK] Browser is open. Current URL: {current_url}")
        
        # Check if logged in (not on login page and on Vahan site)
        if "vahan.parivahan.gov.in" in current_url and "login" not in current_url.lower():
            is_logged_in = True
            save_session_info()  # Save successful session
            safe_print("[CHECK] ✅ User appears to be logged in")
            return {
                "browser_open": True,
                "logged_in": True,
                "message": "Browser is open and user is logged in",
                "current_url": current_url
            }
        else:
            is_logged_in = False
            save_session_info()  # Save session even if not logged in
            safe_print("[CHECK] ⚠️ Browser open but user not logged in")
            return {
                "browser_open": True,
                "logged_in": False,
                "message": "Browser is open but user is not logged in",
                "current_url": current_url
            }
            
    except Exception as e:
        # Driver is dead or not responding
        safe_print(f"[CHECK] ❌ Browser check failed: {str(e)[:50]}")
        driver_instance = None
        is_logged_in = False
        clear_session_info()  # Clear session file
        return {
            "browser_open": False,
            "logged_in": False,
            "message": "Browser instance is not responding"
        }

def wait_for_login(driver, timeout=300):
    """
    Wait for user to login to Vahan website.
    Detects successful login by monitoring URL changes.
    """
    safe_print("[WAIT] Waiting for user to login...")
    safe_print("[INFO] Please login manually in the browser window")
    
    start_time = time.time()
    
    try:
        login_url = driver.current_url
    except Exception as e:
        safe_print(f"[ERROR] ❌ Cannot get current URL: {str(e)[:100]}")
        return False
    
    try:
        while time.time() - start_time < timeout:
            try:
                current_url = driver.current_url
                
                # Check if URL has changed from login page
                if current_url != login_url and "login" not in current_url.lower():
                    safe_print("[SUCCESS] ✅ Login acknowledged - URL changed!")
                    safe_print(f"[INFO] Current URL: {current_url}")
                    return True
                
                # Also check for common post-login elements (optional additional check)
                try:
                    # Look for elements that typically appear after login
                    post_login_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'logout')] | //button[contains(text(), 'Logout')] | //div[contains(@class, 'user')]")
                    if post_login_elements:
                        safe_print("[SUCCESS] ✅ Login acknowledged - user elements found!")
                        return True
                except:
                    pass
                
            except Exception as e:
                # Browser might have been closed
                error_str = str(e)
                if "connection" in error_str.lower() or "target" in error_str.lower():
                    safe_print(f"[ERROR] ❌ Lost connection to browser (was it closed?)")
                    return False
                safe_print(f"[ERROR] ❌ Error checking login status: {error_str[:100]}")
                return False
            
            time.sleep(2)  # Check every 2 seconds
        
        # Timeout reached
        safe_print(f"[TIMEOUT] ⏰ Login timeout after {timeout} seconds.")
        return False
        
    except Exception as e:
        safe_print(f"[ERROR] ❌ Error during login wait: {str(e)[:100]}")
        return False

def start_vahan_browser():
    """
    Main function to start browser and navigate to Vahan website.
    Returns dict with success status and message.
    """
    global driver_instance, is_logged_in
    
    # First check if browser is already open
    status = check_browser_status()
    
    if status["browser_open"] and status["logged_in"]:
        safe_print("[INFO] ✅ Browser already open and logged in! Reusing session.")
        return {
            "success": True,
            "message": "Browser already open and logged in. Ready for automation!",
            "status": "already_logged_in",
            "reused_session": True
        }
    
    if status["browser_open"] and not status["logged_in"]:
        safe_print("[INFO] ⚠️ Browser open but not logged in. Please login.")
        # Browser is open but on login page, wait for login
        try:
            login_success = wait_for_login(driver_instance, timeout=300)
            if login_success:
                is_logged_in = True
                safe_print("[SUCCESS] ✅✅✅ LOGIN ACKNOWLEDGED ✅✅✅")
                return {
                    "success": True,
                    "message": "Login acknowledged successfully!",
                    "status": "login_success"
                }
            else:
                safe_print("[WARNING] ⚠️ Login timeout - user did not complete login")
                return {
                    "success": False,
                    "message": "Login timeout - please try again and login within 5 minutes",
                    "status": "login_timeout"
                }
        except Exception as e:
            safe_print(f"[ERROR] Error waiting for login: {str(e)}")
            return {
                "success": False,
                "message": f"Error waiting for login: {str(e)}",
                "status": "error"
            }
    
    # No browser open, start fresh
    try:
        safe_print("[START] Starting Vahan automation...")
        
        # Create driver
        safe_print("[DRIVER] Creating Chrome driver...")
        driver = create_vahan_driver()
        driver_instance = driver
        safe_print("[SUCCESS] ✅ Chrome driver created successfully!")
        
        # Navigate to Vahan website with retry logic
        max_retries = 3
        retry_count = 0
        page_loaded = False
        
        while retry_count < max_retries and not page_loaded:
            try:
                safe_print(f"[NAVIGATE] Opening Vahan website (attempt {retry_count + 1}/{max_retries}): {VAHAN_URL}")
                
                # Set page load timeout
                driver.set_page_load_timeout(60)
                
                # Navigate to URL
                driver.get(VAHAN_URL)
                
                # Wait a moment for initial page load
                time.sleep(2)
                
                # Wait for page to load completely
                safe_print("[WAIT] Waiting for page to load completely...")
                WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # Additional check - verify we're on the right page
                current_url = driver.current_url
                safe_print(f"[INFO] Current URL: {current_url}")
                
                if "vahan.parivahan.gov.in" in current_url or "login" in current_url.lower():
                    safe_print("[SUCCESS] ✅ Vahan website loaded successfully!")
                    page_loaded = True
                else:
                    safe_print(f"[WARNING] ⚠️ Unexpected URL: {current_url}")
                    retry_count += 1
                    if retry_count < max_retries:
                        safe_print(f"[RETRY] Retrying in 3 seconds...")
                        time.sleep(3)
                
            except TimeoutException:
                safe_print(f"[TIMEOUT] ⏰ Page load timeout on attempt {retry_count + 1}")
                retry_count += 1
                if retry_count < max_retries:
                    safe_print(f"[RETRY] Retrying in 3 seconds...")
                    time.sleep(3)
                    
            except WebDriverException as e:
                if "ERR_CONNECTION_RESET" in str(e) or "net::" in str(e):
                    safe_print(f"[CONNECTION_ERROR] ⚠️ Network error on attempt {retry_count + 1}: Connection reset")
                    retry_count += 1
                    if retry_count < max_retries:
                        safe_print(f"[RETRY] Retrying in 5 seconds...")
                        time.sleep(5)
                else:
                    raise  # Re-raise if it's not a connection error
        
        if not page_loaded:
            error_msg = (
                "⚠️ Unable to connect to Vahan website.\n\n"
                "Possible causes:\n"
                "• Internet connection issues\n"
                "• Firewall/antivirus blocking connection\n"
                "• Website temporarily unavailable\n\n"
                "Solutions:\n"
                "1. Check your internet connection\n"
                "2. Try opening https://vahan.parivahan.gov.in manually in Chrome\n"
                "3. Temporarily disable firewall/antivirus and retry\n"
                "4. Check TROUBLESHOOTING.md for detailed help"
            )
            safe_print(f"[ERROR] ❌ {error_msg}")
            
            # Close driver
            if driver_instance:
                try:
                    driver_instance.quit()
                    driver_instance = None
                except:
                    pass
            
            return {
                "success": False,
                "message": "Failed to connect to Vahan website. Please check your internet connection and try again. See logs for details.",
                "status": "connection_error"
            }
        
        # Wait for user to login
        login_success = wait_for_login(driver, timeout=300)
        
        if login_success:
            is_logged_in = True
            save_session_info()  # Save session after successful login
            safe_print("[SUCCESS] ✅✅✅ LOGIN ACKNOWLEDGED ✅✅✅")
            return {
                "success": True,
                "message": "Browser started and login acknowledged successfully!",
                "status": "login_success"
            }
        else:
            safe_print("[WARNING] ⚠️ Login timeout - user did not complete login")
            return {
                "success": False,
                "message": "Login timeout - please try again and login within 5 minutes",
                "status": "login_timeout"
            }
        
    except Exception as e:
        error_msg = f"Error starting Vahan browser: {str(e)}"
        safe_print(f"[ERROR] ❌ {error_msg}")
        
        # Close driver if it was created
        if driver_instance:
            try:
                driver_instance.quit()
                driver_instance = None
                clear_session_info()  # Clear session on error
            except:
                pass
        
        return {
            "success": False,
            "message": error_msg,
            "status": "error"
        }

def check_for_error_page(driver):
    """
    Check if an error page is displayed (like "Sorry, Something Went Wrong").
    Returns True if error detected, False otherwise.
    """
    try:
        # Check for common error messages
        error_elements = driver.find_elements(
            By.XPATH,
            "//*[contains(text(), 'Sorry') or contains(text(), 'Went Wrong') or contains(text(), 'Error')]"
        )
        
        if error_elements:
            safe_print("[WARNING] ⚠️ Error message detected on page!")
            return True
        
        # Check for the specific "Back to Home-Page" button (error indicator)
        try:
            back_button = driver.find_element(By.ID, "j_idt45")
            if back_button:
                safe_print("[WARNING] ⚠️ 'Back to Home-Page' button detected - error page!")
                return True
        except:
            pass
        
        return False
    except Exception as e:
        safe_print(f"[WARNING] Error checking for error page: {str(e)[:50]}")
        return False

def check_for_back_to_home_page(driver):
    """
    Check if there's a 'back to home page' button/link and click it if found.
    Returns True if found and clicked, False otherwise.
    """
    try:
        # Approach 1: Look for the specific button ID (j_idt45)
        try:
            back_button_by_id = driver.find_element(By.ID, "j_idt45")
            if back_button_by_id and "back to home" in back_button_by_id.text.lower():
                safe_print("[AUTOMATION] Found 'Back to Home-Page' button by ID!")
                back_button_by_id.click()
                safe_print("[SUCCESS] ✅ Clicked 'Back to Home-Page' button!")
                time.sleep(3)  # Wait for page to load
                return True
        except:
            pass
        
        # Approach 2: Look for "back to home page" text or button
        back_to_home_elements = driver.find_elements(
            By.XPATH,
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'back to home page') or contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'back to home page') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'back to home-page')]"
        )
        
        if back_to_home_elements:
            safe_print("[AUTOMATION] Found 'Back to Home Page' element!")
            
            # Try to find a clickable button/link
            for element in back_to_home_elements:
                try:
                    if element.tag_name in ['button', 'a', 'input']:
                        safe_print("[AUTOMATION] Clicking 'Back to Home Page' button...")
                        element.click()
                        safe_print("[SUCCESS] ✅ Clicked 'Back to Home Page' button!")
                        time.sleep(3)  # Wait for page to load
                        return True
                except:
                    continue
            
            # If no direct clickable element, look for button near the text
            try:
                back_button = driver.find_element(
                    By.XPATH,
                    "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'back to home')]//ancestor::button | //*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'back to home')]//ancestor::a"
                )
                safe_print("[AUTOMATION] Clicking 'Back to Home Page' button (ancestor)...")
                back_button.click()
                safe_print("[SUCCESS] ✅ Clicked 'Back to Home Page' button!")
                time.sleep(3)  # Wait for page to load
                return True
            except:
                pass
        
        return False
    except Exception as e:
        safe_print(f"[WARNING] Error checking for back to home page: {str(e)[:50]}")
        return False

def run_automation_internal(retry_count=0, max_retries=2):
    """
    Internal automation function that can be retried.
    Returns result dict with success status.
    """
    global driver_instance
    
    driver = driver_instance
    
    # Check for "back to home page" before starting
    if check_for_back_to_home_page(driver):
        safe_print("[AUTOMATION] Returned to home page, continuing automation...")
    
    # Step 1: Click Dashboard Pendency button
    safe_print("[AUTOMATION] Looking for Dashboard Pendency button...")
    try:
        # Try to find by title attribute first (more reliable)
        dashboard_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@title='Dashboard Pendency']"))
        )
        safe_print("[AUTOMATION] Found Dashboard Pendency button (by title)!")
        dashboard_button.click()
        safe_print("[SUCCESS] ✅ Clicked Dashboard Pendency button!")
        
        # Wait for page transition
        time.sleep(3)
        safe_print("[AUTOMATION] Waiting for page to load...")
        
    except TimeoutException:
        safe_print("[ERROR] Dashboard Pendency button not found within timeout")
        
        # Check if we need to go back to home page and retry
        if retry_count < max_retries:
            safe_print(f"[AUTOMATION] Checking for 'Back to Home Page' button... (Retry {retry_count + 1}/{max_retries})")
            if check_for_back_to_home_page(driver):
                safe_print("[AUTOMATION] Retrying automation after returning to home page...")
                return run_automation_internal(retry_count + 1, max_retries)
        
        # If still can't find it, ask user to login
        return {
            "success": False,
            "message": "⚠️ Dashboard Pendency button not found. Please ensure you are logged in correctly. If you see a login page, please login and try again.",
            "status": "button_not_found",
            "action_required": "login"
        }
    
    # Continue with remaining automation steps
    return execute_remaining_steps(driver, retry_count, max_retries)

def execute_remaining_steps(driver, retry_count=0, max_retries=2):
    """Execute automation steps 2-17"""
    
    # Step 1.5: Handle optional alert popup after Dashboard Pendency click
    safe_print("[AUTOMATION] Checking for optional alert popup...")
    try:
        # Give a short wait to see if the popup appears
        time.sleep(2)
        
        # Try to find the alert dialog
        alert_dialog = driver.find_elements(
            By.XPATH,
            "//div[@id='primefacesmessagedlg' and contains(@class, 'ui-message-dialog')]"
        )
        
        if alert_dialog and alert_dialog[0].is_displayed():
            safe_print("[AUTOMATION] Found alert popup! Attempting to close it...")
            
            # First, remove any overlays that might be blocking
            driver.execute_script("""
                var overlays = document.querySelectorAll('.ui-widget-overlay, .ui-dialog-mask');
                overlays.forEach(function(overlay) {
                    overlay.style.display = 'none';
                });
            """)
            safe_print("[AUTOMATION] Removed overlay elements")
            time.sleep(1)
            
            # Try multiple strategies to close the dialog
            close_clicked = False
            
            # Strategy 1: Click the close button (X icon)
            try:
                close_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//div[@id='primefacesmessagedlg']//a[contains(@class, 'ui-dialog-titlebar-close')]"
                    ))
                )
                close_button.click()
                safe_print("[SUCCESS] ✅ Closed alert popup using close button!")
                close_clicked = True
            except:
                safe_print("[INFO] Could not click close button, trying alternatives...")
            
            # Strategy 2: Click using JavaScript if regular click didn't work
            if not close_clicked:
                try:
                    close_button = driver.find_element(
                        By.XPATH,
                        "//div[@id='primefacesmessagedlg']//a[contains(@class, 'ui-dialog-titlebar-close')]"
                    )
                    driver.execute_script("arguments[0].click();", close_button)
                    safe_print("[SUCCESS] ✅ Closed alert popup using JavaScript!")
                    close_clicked = True
                except:
                    safe_print("[WARNING] Could not close alert popup with JavaScript")
            
            # Wait for dialog to disappear
            if close_clicked:
                time.sleep(2)
                safe_print("[INFO] Alert popup closed successfully")
        else:
            safe_print("[INFO] ℹ️ No alert popup found, continuing to next step")
            
    except Exception as e:
        safe_print(f"[INFO] No alert popup detected or error checking: {e}")
        # Not a critical error, continue with automation
    
    # Step 2: Click Dealer Registration span (if not already expanded)
    safe_print("[AUTOMATION] Looking for Dealer Registration element...")
    try:
        # Wait for the page to load completely
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Check if Dealer Registration is already expanded (look for the down arrow icon)
        try:
            # If this element exists, it's already expanded (ui-icon-triangle-1-s means down arrow)
            already_expanded = driver.find_elements(
                By.XPATH, 
                "//td[.//label[contains(., 'Dealer Registration')]]//span[contains(@class, 'ui-icon-triangle-1-s')]"
            )
            
            if already_expanded:
                safe_print("[INFO] ℹ️ Dealer Registration is already expanded, skipping click")
            else:
                # Find and click the toggle (right arrow icon - ui-icon-triangle-1-e)
                dealer_registration_span = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((
                        By.XPATH, 
                        "//td[.//label[contains(., 'Dealer Registration')]]//span[@class='ui-treetable-toggler ui-icon ui-icon-triangle-1-e ui-c']"
                    ))
                )
                safe_print("[AUTOMATION] Found Dealer Registration toggle!")
                dealer_registration_span.click()
                safe_print("[SUCCESS] ✅ Clicked Dealer Registration toggle!")
                time.sleep(3)  # Wait for sub-items to load
                
        except Exception as e:
            safe_print(f"[WARNING] Could not determine Dealer Registration state: {e}")
            # Try to click anyway
            dealer_registration_span = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH, 
                    "//td[.//label[contains(., 'Dealer Registration')]]//span[@class='ui-treetable-toggler ui-icon ui-icon-triangle-1-e ui-c']"
                ))
            )
            dealer_registration_span.click()
            safe_print("[SUCCESS] ✅ Clicked Dealer Registration toggle!")
            time.sleep(3)
        
        # Step 3: Click "New Registration (Dealer Side)" toggle (if not already expanded)
        safe_print("[AUTOMATION] Looking for New Registration (Dealer Side) toggle...")
        
        # Check if New Registration is already expanded
        try:
            already_expanded_new_reg = driver.find_elements(
                By.XPATH,
                "//label[contains(., 'New Registration (Dealer Side)')]/preceding-sibling::span[contains(@class, 'ui-icon-triangle-1-s')]"
            )
            
            if already_expanded_new_reg:
                safe_print("[INFO] ℹ️ New Registration (Dealer Side) is already expanded, skipping click")
            else:
                # Find and click the toggle (right arrow)
                new_registration_span = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//label[contains(., 'New Registration (Dealer Side)')]/preceding-sibling::span[@class='ui-treetable-toggler ui-icon ui-icon-triangle-1-e ui-c']"
                    ))
                )
                safe_print("[AUTOMATION] Found New Registration (Dealer Side) toggle!")
                new_registration_span.click()
                safe_print("[SUCCESS] ✅ Clicked New Registration (Dealer Side) toggle!")
                time.sleep(2)  # Wait for expansion to complete
                
        except Exception as e:
            safe_print(f"[WARNING] Could not determine New Registration state: {e}")
            # Try to click anyway
            new_registration_span = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//label[contains(., 'New Registration (Dealer Side)')]/preceding-sibling::span[@class='ui-treetable-toggler ui-icon ui-icon-triangle-1-e ui-c']"
                ))
            )
            new_registration_span.click()
            safe_print("[SUCCESS] ✅ Clicked New Registration (Dealer Side) toggle!")
            time.sleep(2)
        
        # Step 4: Click the magnifying glass (View Detail link) beside "NEW-RC-APPROVAL"
        safe_print("[AUTOMATION] Looking for View Detail link beside NEW-RC-APPROVAL...")
        # Find the <a> tag in the same row as the label containing "NEW-RC-APPROVAL"
        # Using XPath similar to Dealer Registration pattern - finds the <a> in the <td> that contains the label
        view_detail_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//tr[.//label[contains(., 'NEW-RC-APPROVAL')]]//td[@role='gridcell']//a[contains(@class, 'ui-commandlink')]"
            ))
        )
        safe_print("[AUTOMATION] Found View Detail link beside NEW-RC-APPROVAL!")
        view_detail_link.click()
        safe_print("[SUCCESS] ✅ Clicked View Detail magnifying glass beside NEW-RC-APPROVAL!")
        
        time.sleep(3)  # Wait for the table page to load
        
        # Step 5: Wait for the table to appear and click the first Approve button
        safe_print("[AUTOMATION] Waiting for the Pending Applications table to load...")
        try:
            # Wait for the table with id="workDetails" to be visible
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "workDetails"))
            )
            safe_print("[AUTOMATION] Table loaded successfully!")
            
            # Find the first Approve button in the table (in the first row with data-ri="0")
            # The button is inside workDetails table with pattern workDetails:0:j_idt270
            safe_print("[AUTOMATION] Looking for the first Approve button...")
            
            # Check if any approve buttons exist in the table
            approve_buttons = driver.find_elements(
                By.XPATH,
                "//tbody[@id='workDetails_data']//tr[@data-ri='0']//button[contains(@id, 'workDetails:0:')]"
            )
            
            if not approve_buttons:
                # No approve buttons found - this means all items are processed!
                safe_print("[INFO] ℹ️ No approve buttons found in the table!")
                safe_print("[SUCCESS] 🎉 All pending applications have been processed!")
                return {
                    "success": False,  # False to stop the loop
                    "message": "No more pending applications to process.",
                    "status": "no_approve_button"
                }
            
            # Wait for the button to be clickable
            first_approve_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//tbody[@id='workDetails_data']//tr[@data-ri='0']//button[contains(@id, 'workDetails:0:')]"
                ))
            )
            safe_print("[AUTOMATION] Found first Approve button!")
            first_approve_button.click()
            safe_print("[SUCCESS] ✅ Clicked first Approve button!")
            
            time.sleep(3)  # Wait for the new page/dialog to open
            
        except TimeoutException:
            safe_print("[ERROR] Table or Approve button not found within timeout")
            
            # Double-check if it's because there are no more items to process
            try:
                table = driver.find_element(By.ID, "workDetails")
                rows = driver.find_elements(By.XPATH, "//tbody[@id='workDetails_data']//tr[@data-ri='0']")
                
                if not rows or len(rows) == 0:
                    safe_print("[INFO] ℹ️ Table is empty - no more items to process!")
                    return {
                        "success": False,  # False to stop the loop
                        "message": "No more pending applications to process.",
                        "status": "no_approve_button"
                    }
            except:
                pass
            
            return {
                "success": False,
                "message": "Pending Applications table or Approve button not found. The page may not have loaded correctly.",
                "status": "table_not_found"
            }
        
        # Step 6: Click the verification checkbox (only if unchecked)
        safe_print("[AUTOMATION] Looking for the verification checkbox...")
        try:
            # Wait for the checkbox to be visible
            # The checkbox is identified by id="workbench_tabview:verifyCheckValue"
            checkbox_container = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((
                    By.ID,
                    "workbench_tabview:verifyCheckValue"
                ))
            )
            safe_print("[AUTOMATION] Found verification checkbox container!")
            
            # Check if the checkbox is already checked
            # If checked, the checkbox box will have class "ui-state-active"
            checkbox_box = checkbox_container.find_element(By.CLASS_NAME, "ui-chkbox-box")
            checkbox_classes = checkbox_box.get_attribute("class")
            
            if "ui-state-active" in checkbox_classes:
                safe_print("[INFO] ℹ️ Verification checkbox is already checked, skipping click")
            else:
                safe_print("[AUTOMATION] Checkbox is unchecked, clicking it...")
                checkbox_box.click()
                safe_print("[SUCCESS] ✅ Clicked verification checkbox!")
                time.sleep(2)  # Wait for checkbox action to complete
            
        except TimeoutException:
            safe_print("[ERROR] Verification checkbox not found within timeout")
            return {
                "success": False,
                "message": "Verification checkbox not found. The approval page may not have loaded correctly.",
                "status": "checkbox_not_found"
            }
        
        # Step 7: Click on the "Documents Uploaded" tab
        safe_print("[AUTOMATION] Looking for the Documents Uploaded tab...")
        try:
            # Wait for the tab to be clickable
            # The tab is the 6th tab (data-index="5")
            documents_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//ul[contains(@class, 'ui-tabs-nav')]//li[@data-index='5']//a[contains(text(), 'Documents Uploaded')]"
                ))
            )
            safe_print("[AUTOMATION] Found Documents Uploaded tab!")
            documents_tab.click()
            safe_print("[SUCCESS] ✅ Clicked Documents Uploaded tab!")
            
            time.sleep(3)  # Wait for tab content to load
            
        except TimeoutException:
            safe_print("[ERROR] Documents Uploaded tab not found within timeout")
            return {
                "success": False,
                "message": "Documents Uploaded tab not found. The page may not have loaded correctly.",
                "status": "tab_not_found"
            }
        
        # Step 8: Click the "Modify/View Documents" button
        safe_print("[AUTOMATION] Looking for the Modify/View Documents button...")
        try:
            # Wait for the button to be clickable
            # The button has id="workbench_tabview:idViewDoc" and contains text "Modify/View Documents for Application No"
            modify_view_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((
                    By.ID,
                    "workbench_tabview:idViewDoc"
                ))
            )
            safe_print("[AUTOMATION] Found Modify/View Documents button!")
            
            # Get the button text to log the application number
            button_text = modify_view_button.text
            safe_print(f"[AUTOMATION] Button text: {button_text}")
            
            modify_view_button.click()
            safe_print("[SUCCESS] ✅ Clicked Modify/View Documents button!")
            
            time.sleep(3)  # Wait for the modal to open
            
        except TimeoutException:
            safe_print("[ERROR] Modify/View Documents button not found within timeout")
            return {
                "success": False,
                "message": "Modify/View Documents button not found. The Documents Uploaded tab content may not have loaded correctly.",
                "status": "modify_button_not_found"
            }
        
        # Step 9: Close the DMS modal
        safe_print("[AUTOMATION] Looking for the modal close button...")
        try:
            # Make sure we're in default content (not in any iframe)
            driver.switch_to.default_content()
            
            # Wait for the modal dialog to appear first
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.ID,
                    "workbench_tabview:viewUploadedDms_title"
                ))
            )
            safe_print("[AUTOMATION] Modal dialog appeared!")
            time.sleep(1)  # Wait for modal animation to complete
            
            # Find the close button - target the one inside the DMS modal specifically
            close_modal_button = None
            try:
                # More specific selector - find close button within the viewUploadedDms dialog
                close_modal_button = driver.find_element(
                    By.XPATH,
                    "//div[@id='workbench_tabview:viewUploadedDms']//a[contains(@class, 'ui-dialog-titlebar-close')]"
                )
                safe_print("[AUTOMATION] Found modal close button using specific XPath!")
            except:
                # Fallback: By CSS selector
                try:
                    close_modal_button = driver.find_element(
                        By.CSS_SELECTOR,
                        "a.ui-dialog-titlebar-close"
                    )
                    safe_print("[AUTOMATION] Found modal close button using CSS selector!")
                except:
                    # Last resort: By aria-label
                    close_modal_button = driver.find_element(
                        By.XPATH,
                        "//a[@aria-label='Close' and contains(@class, 'ui-dialog-titlebar-close')]"
                    )
                    safe_print("[AUTOMATION] Found modal close button using aria-label!")
            
            # Try regular click first (more reliable for UI interactions)
            try:
                safe_print("[AUTOMATION] Attempting regular click on close button...")
                # Scroll into view first
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", close_modal_button)
                time.sleep(0.5)
                
                # Wait for element to be clickable
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(close_modal_button)
                )
                
                # Regular click
                close_modal_button.click()
                safe_print("[SUCCESS] ✅ Clicked modal close button with regular click!")
            except Exception as e:
                safe_print(f"[WARNING] Regular click failed: {str(e)[:80]}, trying JavaScript click...")
                # Fallback to JavaScript click
                driver.execute_script("arguments[0].click();", close_modal_button)
                safe_print("[SUCCESS] ✅ Clicked modal close button with JavaScript!")
            
            time.sleep(2)  # Wait for modal to close
            
        except TimeoutException:
            safe_print("[ERROR] Modal close button not found within timeout")
            return {
                "success": False,
                "message": "Modal close button not found.",
                "status": "modal_close_not_found"
            }
        
        # Step 10: Close the success message popup using close icon
        safe_print("[AUTOMATION] Looking for success message popup close button...")
        try:
            # Wait for popup to appear (increased wait time)
            safe_print("[AUTOMATION] Waiting for confirmation popup to appear...")
            time.sleep(3)
            
            # Find the close icon (X) in the success dialog using "Confirmation" title as anchor
            close_popup_button = None
            try:
                close_popup_button = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//div[contains(@class, 'ui-dialog-titlebar')]//span[contains(text(), 'Confirmation')]/following-sibling::a[contains(@class, 'ui-dialog-titlebar-close')]"
                    ))
                )
                safe_print("[AUTOMATION] Found success popup close icon!")
            except:
                # Fallback: try to find any visible dialog close button
                close_popup_button = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//div[contains(@class, 'ui-dialog') and contains(@style, 'display: block')]//a[contains(@class, 'ui-dialog-titlebar-close')]"
                    ))
                )
                safe_print("[AUTOMATION] Found success popup close icon (fallback)!")
            
            # Element found but may be blocked by overlay - use JavaScript to click directly
            # This bypasses overlay blocking issues
            safe_print("[AUTOMATION] Clicking popup close button (bypassing overlays)...")
            try:
                # First, try to remove any blocking overlays
                driver.execute_script("""
                    // Hide all overlay elements that might block the click
                    var overlays = document.querySelectorAll('.ui-widget-overlay, .ui-dialog-mask');
                    overlays.forEach(function(overlay) {
                        overlay.style.display = 'none';
                    });
                """)
                time.sleep(0.3)
                
                # Now try regular click
                close_popup_button.click()
                safe_print("[SUCCESS] ✅ Clicked success popup close icon!")
            except Exception as e:
                safe_print(f"[WARNING] Regular click failed even after removing overlays: {str(e)[:50]}")
                # Use JavaScript click that bypasses all interactability checks
                safe_print("[AUTOMATION] Using direct JavaScript click...")
                driver.execute_script("arguments[0].click();", close_popup_button)
                safe_print("[SUCCESS] ✅ Clicked popup close with JavaScript!")
            
            time.sleep(2)  # Wait for popup to close and overlay to disappear
            
        except Exception as e:
            safe_print(f"[ERROR] Could not find or click success popup close icon: {str(e)[:100]}")
            return {
                "success": False,
                "message": "Could not close success message popup.",
                "status": "popup_close_not_found"
            }
        
        # Step 11: Click the Modify/View Documents button again
        safe_print("[AUTOMATION] Clicking Modify/View Documents button again...")
        try:
            modify_view_button_2 = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((
                    By.ID,
                    "workbench_tabview:idViewDoc"
                ))
            )
            safe_print("[AUTOMATION] Found Modify/View Documents button again!")
            
            # Use JavaScript click to avoid interception issues
            safe_print("[AUTOMATION] Using JavaScript click to avoid iframe interception...")
            driver.execute_script("arguments[0].click();", modify_view_button_2)
            
            safe_print("[SUCCESS] ✅ Clicked Modify/View Documents button again!")
            
            time.sleep(3)  # Wait for the modal to open
            
        except TimeoutException:
            safe_print("[ERROR] Modify/View Documents button not found on second attempt")
            return {
                "success": False,
                "message": "Modify/View Documents button not found on second attempt.",
                "status": "modify_button_2_not_found"
            }
        except WebDriverException as e:
            safe_print(f"[ERROR] WebDriver error clicking Modify/View Documents button: {str(e)[:200]}")
            return {
                "success": False,
                "message": f"Could not click Modify/View Documents button - it may be blocked by another element. Error: {str(e)[:100]}",
                "status": "modify_button_2_click_error"
            }
        
        # Step 12: Check all unchecked "approvedStatus" checkboxes in the document list
        safe_print("[AUTOMATION] Looking for approvedStatus checkboxes...")
        try:
            # Wait for the modal and iframe to load
            time.sleep(2)
            
            # The checkboxes are inside an iframe in the DMS modal
            # First, find and switch to the iframe
            safe_print("[AUTOMATION] Looking for DMS iframe...")
            try:
                # Wait for the iframe to be present
                iframe = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//iframe[contains(@src, 'dms-app/dealer-search-within-dms')]"
                    ))
                )
                safe_print("[AUTOMATION] Found DMS iframe, switching to it...")
                driver.switch_to.frame(iframe)
                safe_print("[SUCCESS] ✅ Switched to iframe!")
                time.sleep(1)  # Give iframe content time to load
            except TimeoutException:
                safe_print("[ERROR] Could not find DMS iframe")
                raise
            
            # Now we're inside the iframe, wait for checkboxes
            # Wait for Angular to initialize and checkboxes to appear
            time.sleep(2)  # Give Angular time to render inside iframe
            
            # Wait for at least one checkbox with name starting with 'approvedStatus'
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//input[@type='checkbox' and starts-with(@name, 'approvedStatus')]"
                ))
            )
            
            # Additional wait for Angular to be ready
            try:
                driver.execute_script("return window.angular !== undefined;")
            except:
                pass
            time.sleep(1)
            
            # Find all approvedStatus checkboxes (approvedStatus, approvedStatus2, approvedStatus3, etc.)
            approved_checkboxes = driver.find_elements(
                By.XPATH,
                "//input[@type='checkbox' and starts-with(@name, 'approvedStatus')]"
            )
            
            safe_print(f"[AUTOMATION] Found {len(approved_checkboxes)} total approvedStatus checkboxes")
            
            checked_count = 0
            skipped_count = 0
            
            for i, checkbox in enumerate(approved_checkboxes):
                try:
                    # Get checkbox name for logging
                    checkbox_name = checkbox.get_attribute("name") or f"checkbox_{i+1}"
                    
                    # Check if checkbox is disabled
                    is_disabled = checkbox.get_attribute("disabled")
                    
                    # Check if checkbox is already checked (multiple ways for Angular)
                    is_checked = checkbox.is_selected()  # Selenium's native method
                    checked_attr = checkbox.get_attribute("checked")  # HTML attribute
                    
                    safe_print(f"[DEBUG] {checkbox_name}: disabled={is_disabled}, is_selected={is_checked}, checked_attr={checked_attr}")
                    
                    # Skip if disabled
                    if is_disabled:
                        safe_print(f"[INFO] {checkbox_name} is disabled, skipping")
                        skipped_count += 1
                        continue
                    
                    # Skip if already checked
                    if is_checked or checked_attr:
                        safe_print(f"[INFO] {checkbox_name} is already checked, skipping")
                        skipped_count += 1
                        continue
                    
                    # Checkbox is enabled and unchecked - click it!
                    safe_print(f"[AUTOMATION] Clicking {checkbox_name}...")
                    
                    # Scroll checkbox into view
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                    time.sleep(0.5)
                    
                    # Try clicking with JavaScript for Angular checkboxes
                    try:
                        # Use JavaScript click which works better with Angular
                        driver.execute_script("arguments[0].click();", checkbox)
                        checked_count += 1
                        safe_print(f"[AUTOMATION] ✓ Checked {checkbox_name} ({checked_count} total)")
                    except Exception as click_err:
                        safe_print(f"[WARNING] JS click failed, trying regular click: {str(click_err)[:50]}")
                        checkbox.click()
                        checked_count += 1
                        safe_print(f"[AUTOMATION] ✓ Checked {checkbox_name} ({checked_count} total)")
                    
                    time.sleep(0.7)  # Small delay for Angular to process
                        
                except Exception as e:
                    safe_print(f"[WARNING] Could not process checkbox {i+1}: {str(e)[:100]}")
            
            safe_print(f"[SUCCESS] ✅ Checked {checked_count} checkboxes, skipped {skipped_count} (disabled or already checked)")
            
            # IMPORTANT: Switch back to default content (exit iframe)
            driver.switch_to.default_content()
            safe_print("[AUTOMATION] Switched back to default content from iframe")
            
            time.sleep(2)  # Wait after checking all
            
        except TimeoutException:
            safe_print("[ERROR] ApprovedStatus checkboxes not found within timeout")
            
            # Make sure we're back to default content even if there's an error
            try:
                driver.switch_to.default_content()
                safe_print("[AUTOMATION] Switched back to default content after error")
            except:
                pass
            
            # Try to get more diagnostic information
            try:
                page_source = driver.page_source
                if 'approvedStatus' in page_source:
                    safe_print("[DEBUG] Found 'approvedStatus' in page source, but elements not accessible")
                else:
                    safe_print("[DEBUG] 'approvedStatus' not found in page source at all")
            except:
                pass
            
            # Check if error page appeared with "Back to Home-Page" button
            if check_for_back_to_home_page(driver):
                safe_print("[AUTOMATION] Error page detected, returned to home page. Retrying...")
                if retry_count < max_retries:
                    return run_automation_internal(retry_count + 1, max_retries)
            
            return {
                "success": False,
                "message": "ApprovedStatus checkboxes not found. The page may not have loaded completely, or Angular is still initializing.",
                "status": "checkboxes_not_found"
            }
        except Exception as e:
            safe_print(f"[ERROR] Unexpected error while processing checkboxes: {str(e)[:200]}")
            
            # Make sure we're back to default content even if there's an error
            try:
                driver.switch_to.default_content()
                safe_print("[AUTOMATION] Switched back to default content after exception")
            except:
                pass
            
            return {
                "success": False,
                "message": f"Error processing approvedStatus checkboxes: {str(e)[:100]}",
                "status": "checkbox_processing_error"
            }
        
        # Step 13: Close the DMS modal again
        safe_print("[AUTOMATION] Closing the modal again...")
        try:
            # Make sure we're in default content (not in iframe)
            driver.switch_to.default_content()
            
            # Wait for the modal to be present
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.ID,
                    "workbench_tabview:viewUploadedDms_title"
                ))
            )
            time.sleep(1)  # Wait for modal animation to complete
            
            # Find the close button - target the one inside the DMS modal specifically
            close_modal_button_2 = None
            try:
                # More specific selector - find close button within the viewUploadedDms dialog
                close_modal_button_2 = driver.find_element(
                    By.XPATH,
                    "//div[@id='workbench_tabview:viewUploadedDms']//a[contains(@class, 'ui-dialog-titlebar-close')]"
                )
                safe_print("[AUTOMATION] Found modal close button using specific XPath!")
            except:
                # Fallback: By CSS selector
                try:
                    close_modal_button_2 = driver.find_element(
                        By.CSS_SELECTOR,
                        "a.ui-dialog-titlebar-close"
                    )
                    safe_print("[AUTOMATION] Found modal close button using CSS selector!")
                except:
                    # Last resort: By aria-label
                    close_modal_button_2 = driver.find_element(
                        By.XPATH,
                        "//a[@aria-label='Close' and contains(@class, 'ui-dialog-titlebar-close')]"
                    )
                    safe_print("[AUTOMATION] Found modal close button using aria-label!")
            
            # Try regular click first (more reliable for UI interactions)
            try:
                safe_print("[AUTOMATION] Attempting regular click on close button...")
                # Scroll into view first
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", close_modal_button_2)
                time.sleep(0.5)
                
                # Wait for element to be clickable
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(close_modal_button_2)
                )
                
                # Regular click
                close_modal_button_2.click()
                safe_print("[SUCCESS] ✅ Clicked modal close button with regular click!")
            except Exception as e:
                safe_print(f"[WARNING] Regular click failed: {str(e)[:80]}, trying JavaScript click...")
                # Fallback to JavaScript click
                driver.execute_script("arguments[0].click();", close_modal_button_2)
                safe_print("[SUCCESS] ✅ Clicked modal close button with JavaScript!")
            
            time.sleep(2)  # Wait for modal to close
            
        except TimeoutException:
            safe_print("[ERROR] Modal close button not found on second attempt")
            return {
                "success": False,
                "message": "Modal close button not found on second attempt.",
                "status": "modal_close_2_not_found"
            }
        
        # Step 14: Close the success message popup using close icon (again)
        safe_print("[AUTOMATION] Looking for success message popup close button again...")
        try:
            # Wait for popup to appear (increased wait time)
            safe_print("[AUTOMATION] Waiting for confirmation popup to appear...")
            time.sleep(3)
            
            # Find the close icon (X) in the success dialog using "Confirmation" title as anchor
            close_popup_button_2 = None
            try:
                close_popup_button_2 = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//div[contains(@class, 'ui-dialog-titlebar')]//span[contains(text(), 'Confirmation')]/following-sibling::a[contains(@class, 'ui-dialog-titlebar-close')]"
                    ))
                )
                safe_print("[AUTOMATION] Found success popup close icon!")
            except:
                # Fallback: try to find any visible dialog close button
                close_popup_button_2 = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//div[contains(@class, 'ui-dialog') and contains(@style, 'display: block')]//a[contains(@class, 'ui-dialog-titlebar-close')]"
                    ))
                )
                safe_print("[AUTOMATION] Found success popup close icon (fallback)!")
            
            # Element found but may be blocked by overlay - use JavaScript to click directly
            # This bypasses overlay blocking issues
            safe_print("[AUTOMATION] Clicking popup close button (bypassing overlays)...")
            try:
                # First, try to remove any blocking overlays
                driver.execute_script("""
                    // Hide all overlay elements that might block the click
                    var overlays = document.querySelectorAll('.ui-widget-overlay, .ui-dialog-mask');
                    overlays.forEach(function(overlay) {
                        overlay.style.display = 'none';
                    });
                """)
                time.sleep(0.3)
                
                # Now try regular click
                close_popup_button_2.click()
                safe_print("[SUCCESS] ✅ Clicked success popup close icon!")
            except Exception as e:
                safe_print(f"[WARNING] Regular click failed even after removing overlays: {str(e)[:50]}")
                # Use JavaScript click that bypasses all interactability checks
                safe_print("[AUTOMATION] Using direct JavaScript click...")
                driver.execute_script("arguments[0].click();", close_popup_button_2)
                safe_print("[SUCCESS] ✅ Clicked popup close with JavaScript!")
            
            time.sleep(2)  # Wait for popup to close and overlay to disappear
            
        except Exception as e:
            safe_print(f"[ERROR] Could not find or click success popup close icon: {str(e)[:100]}")
            return {
                "success": False,
                "message": "Could not close success message popup on second attempt.",
                "status": "popup_close_not_found"
            }
        
        # Step 15: Click the "Save-Options" dropdown button
        safe_print("[AUTOMATION] Looking for the Save-Options dropdown button...")
        try:
            # Find by button text "Save-Options" instead of dynamic ID
            save_options_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[.//span[contains(text(), 'Save-Options')]]"
                ))
            )
            safe_print("[AUTOMATION] Found Save-Options button!")
            save_options_button.click()
            safe_print("[SUCCESS] ✅ Clicked Save-Options button!")
            
            time.sleep(2)  # Wait for dropdown to open
            
        except TimeoutException:
            safe_print("[ERROR] Save-Options button not found within timeout")
            return {
                "success": False,
                "message": "Save-Options button not found.",
                "status": "save_options_not_found"
            }
        
        # Step 16: Click "File Movement" from the dropdown menu
        safe_print("[AUTOMATION] Looking for File Movement option in dropdown...")
        try:
            # Find by text "File Movement" instead of dynamic ID
            file_movement_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//a[.//span[contains(text(), 'File Movement')]]"
                ))
            )
            safe_print("[AUTOMATION] Found File Movement option!")
            file_movement_link.click()
            safe_print("[SUCCESS] ✅ Clicked File Movement option!")
            
            time.sleep(3)  # Wait for modal to open
            
        except TimeoutException:
            safe_print("[ERROR] File Movement option not found within timeout")
            return {
                "success": False,
                "message": "File Movement option not found in dropdown.",
                "status": "file_movement_not_found"
            }
        
        # Step 17: Wait for the File Movement modal to open successfully
        safe_print("[AUTOMATION] Waiting for File Movement modal to open...")
        try:
            # Wait for the modal dialog to appear
            # Try to find a modal dialog or panel that appears after clicking File Movement
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//div[contains(@class, 'ui-dialog') and contains(@style, 'display: block')] | //div[@id='panelAppDisapp' and contains(@style, 'display: block')]"
                ))
            )
            safe_print("[SUCCESS] ✅ File Movement modal opened successfully!")
            
            time.sleep(1)  # Small wait to ensure modal is fully loaded
            
        except TimeoutException:
            safe_print("[WARNING] Could not detect File Movement modal, but proceeding...")
            # Don't fail here, just warn - the modal might have a different structure
        
        # Step 18: Select the "Proceed to Next Seat" radio button
        safe_print("[AUTOMATION] Looking for 'Proceed to Next Seat' radio button...")
        try:
            # Wait for modal content to be fully loaded
            time.sleep(1)
            
            # Find the radio button by its associated label "Proceed to Next Seat"
            # The actual input is hidden, so we need to click the visible UI element
            proceed_label = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//label[contains(text(), 'Proceed to Next Seat')]"
                ))
            )
            safe_print("[AUTOMATION] Found 'Proceed to Next Seat' label")
            
            # Get the radio button ID from the label's 'for' attribute
            radio_button_id = proceed_label.get_attribute('for')
            safe_print(f"[AUTOMATION] Radio button ID: {radio_button_id}")
            
            # The actual input element is hidden inside ui-helper-hidden-accessible
            # We need to click the visible ui-radiobutton-box div instead
            # Find the radio button box that corresponds to this input
            radio_button_box = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    f"//input[@id='{radio_button_id}']/ancestor::div[contains(@class, 'ui-radiobutton')]//div[contains(@class, 'ui-radiobutton-box')]"
                ))
            )
            
            # Check if already selected (will have ui-state-active class)
            box_classes = radio_button_box.get_attribute('class')
            if 'ui-state-active' not in box_classes:
                safe_print("[AUTOMATION] Radio button not selected, clicking the UI box...")
                radio_button_box.click()
                safe_print("[SUCCESS] ✅ Selected 'Proceed to Next Seat' radio button!")
                time.sleep(1)  # Wait for any AJAX updates
            else:
                safe_print("[INFO] ℹ️ 'Proceed to Next Seat' radio button already selected")
            
        except TimeoutException:
            safe_print("[ERROR] 'Proceed to Next Seat' radio button not found")
            return {
                "success": False,
                "message": "Could not find 'Proceed to Next Seat' radio button in File Movement modal",
                "status": "element_not_found"
            }
        except Exception as e:
            safe_print(f"[ERROR] Error selecting radio button: {str(e)[:100]}")
            return {
                "success": False,
                "message": f"Error selecting radio button: {str(e)}",
                "status": "error"
            }
        
        # Step 19: Click the Save button in the File Movement modal
        safe_print("[AUTOMATION] Looking for Save button in File Movement modal...")
        try:
            # Multiple strategies to find and click the Save button
            save_clicked = False
            
            # Strategy 1: Try to find by text content within the modal
            try:
                save_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//div[contains(@class, 'ui-dialog') and contains(@style, 'display: block')]//a[contains(@class, 'ui-commandlink') and contains(text(), 'Save')]"
                    ))
                )
                safe_print("[AUTOMATION] Found Save button (Strategy 1: text in visible modal)")
                save_button.click()
                save_clicked = True
                safe_print("[SUCCESS] ✅ Clicked Save button!")
            except:
                safe_print("[AUTOMATION] Strategy 1 failed, trying Strategy 2...")
            
            # Strategy 2: Try to find by ID (from the HTML: app_disapp_form:j_idt1949)
            if not save_clicked:
                try:
                    save_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "app_disapp_form:j_idt1949"))
                    )
                    safe_print("[AUTOMATION] Found Save button (Strategy 2: by ID)")
                    save_button.click()
                    save_clicked = True
                    safe_print("[SUCCESS] ✅ Clicked Save button!")
                except:
                    safe_print("[AUTOMATION] Strategy 2 failed, trying Strategy 3...")
            
            # Strategy 3: Try JavaScript click if normal click fails
            if not save_clicked:
                try:
                    save_button = driver.find_element(
                        By.XPATH,
                        "//a[contains(@class, 'ui-commandlink') and contains(text(), 'Save')]"
                    )
                    safe_print("[AUTOMATION] Found Save button, trying JavaScript click (Strategy 3)")
                    driver.execute_script("arguments[0].click();", save_button)
                    save_clicked = True
                    safe_print("[SUCCESS] ✅ Clicked Save button using JavaScript!")
                except:
                    safe_print("[AUTOMATION] Strategy 3 failed, trying Strategy 4...")
            
            # Strategy 4: Find by class and data attributes
            if not save_clicked:
                try:
                    save_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            "//a[contains(@class, 'ui-commandlink') and contains(@data-pfconfirmcommand, 'PF')]"
                        ))
                    )
                    safe_print("[AUTOMATION] Found Save button (Strategy 4: by data attributes)")
                    driver.execute_script("arguments[0].click();", save_button)
                    save_clicked = True
                    safe_print("[SUCCESS] ✅ Clicked Save button using JavaScript!")
                except:
                    pass
            
            if not save_clicked:
                raise Exception("All strategies to click Save button failed")
            
            time.sleep(2)  # Wait for save action to process
            
        except TimeoutException:
            safe_print("[ERROR] Save button not found in File Movement modal")
            return {
                "success": False,
                "message": "Could not find Save button in File Movement modal",
                "status": "element_not_found"
            }
        except Exception as e:
            safe_print(f"[ERROR] Error clicking Save button: {str(e)[:100]}")
            return {
                "success": False,
                "message": f"Error clicking Save button: {str(e)}",
                "status": "error"
            }
        
        # Step 20: Click "Yes" in the confirmation dialog
        safe_print("[AUTOMATION] Looking for 'Yes' button in confirmation dialog...")
        try:
            # Wait for the confirmation dialog to appear
            time.sleep(1)
            
            # Multiple strategies to find and click the Yes button
            yes_clicked = False
            
            # Strategy 1: Find by the class "ui-confirmdialog-yes"
            try:
                yes_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(@class, 'ui-confirmdialog-yes')]"
                    ))
                )
                safe_print("[AUTOMATION] Found Yes button (Strategy 1: by class)")
                
                # First, try to remove any blocking overlays
                driver.execute_script("""
                    // Hide all overlay elements that might block the click
                    var overlays = document.querySelectorAll('.ui-widget-overlay, .ui-dialog-mask');
                    overlays.forEach(function(overlay) {
                        overlay.style.display = 'none';
                    });
                """)
                time.sleep(0.3)
                
                yes_button.click()
                yes_clicked = True
                safe_print("[SUCCESS] ✅ Clicked Yes button!")
            except Exception as e:
                safe_print(f"[AUTOMATION] Strategy 1 failed: {str(e)[:50]}, trying Strategy 2...")
            
            # Strategy 2: Find by button text "Yes"
            if not yes_clicked:
                try:
                    yes_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            "//button[contains(@class, 'ui-button')]//span[contains(text(), 'Yes')]"
                        ))
                    )
                    safe_print("[AUTOMATION] Found Yes button (Strategy 2: by text)")
                    yes_button.click()
                    yes_clicked = True
                    safe_print("[SUCCESS] ✅ Clicked Yes button!")
                except:
                    safe_print("[AUTOMATION] Strategy 2 failed, trying Strategy 3...")
            
            # Strategy 3: Find by ID pattern (from HTML: app_disapp_form:j_idt1965)
            if not yes_clicked:
                try:
                    yes_button = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((
                            By.XPATH,
                            "//button[contains(@id, 'app_disapp_form:j_idt') and contains(@class, 'ui-confirmdialog-yes')]"
                        ))
                    )
                    safe_print("[AUTOMATION] Found Yes button (Strategy 3: by ID pattern)")
                    driver.execute_script("arguments[0].click();", yes_button)
                    yes_clicked = True
                    safe_print("[SUCCESS] ✅ Clicked Yes button using JavaScript!")
                except:
                    pass
            
            if not yes_clicked:
                raise Exception("All strategies to click Yes button failed")
            
            time.sleep(2)  # Wait for confirmation action to process
            
        except TimeoutException:
            safe_print("[ERROR] Yes button not found in confirmation dialog")
            return {
                "success": False,
                "message": "Could not find Yes button in confirmation dialog",
                "status": "element_not_found"
            }
        except Exception as e:
            safe_print(f"[ERROR] Error clicking Yes button: {str(e)[:100]}")
            return {
                "success": False,
                "message": f"Error clicking Yes button: {str(e)}",
                "status": "error"
            }
        
        return {
            "success": True,
            "message": "Automation completed successfully! All steps executed: Dashboard Pendency → Dealer Registration → New Registration (Dealer Side) → NEW-RC-APPROVAL View Detail → First Approve Button → Verification Checkbox → Documents Uploaded Tab → Modify/View Documents → Close Modal → OK → Modify/View Documents Again → Check All Approved Checkboxes → Close Modal → OK → Save-Options → File Movement → Modal Opened → Proceed to Next Seat Selected → Save Clicked → Yes Confirmed.",
            "status": "completed"
        }
    
    except TimeoutException:
        safe_print("[ERROR] Dealer Registration element not found within timeout")
        return {
            "success": False,
            "message": "Dealer Registration element not found. The page may not have loaded correctly.",
            "status": "element_not_found"
        }
        
    except Exception as e:
        error_msg = f"Error during automation: {str(e)}"
        safe_print(f"[ERROR] ❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg,
            "status": "error"
        }

def run_automation():
    """
    Main automation function that checks browser status and runs the automation in a loop.
    Continues processing until no more approve buttons are found.
    Includes retry logic for 'back to home page' scenarios.
    """
    # First check if browser is open and logged in
    status = check_browser_status()
    
    if not status["browser_open"]:
        return {
            "success": False,
            "message": "⚠️ Browser is not open. Please click 'Start' to open the browser and login first.",
            "status": "browser_not_open"
        }
    
    if not status["logged_in"]:
        return {
            "success": False,
            "message": "⚠️ You are not logged in. Please login to Vahan website first.",
            "status": "not_logged_in"
        }
    
    # Browser is open and user is logged in, run automation in a loop
    safe_print("[AUTOMATION] 🔄 Starting infinite automation loop...")
    safe_print("[AUTOMATION] Will continue processing until no more approve buttons are found...")
    
    processed_count = 0
    error_count = 0
    max_consecutive_errors = 3  # Stop after 3 consecutive errors
    
    while True:
        safe_print(f"\n{'='*60}")
        safe_print(f"[AUTOMATION] 🔄 LOOP ITERATION {processed_count + 1}")
        safe_print(f"{'='*60}\n")
        
        # Run one iteration of automation
        result = run_automation_internal(retry_count=0, max_retries=2)
        
        # Check the result
        if result.get("success"):
            processed_count += 1
            error_count = 0  # Reset error count on success
            safe_print(f"[SUCCESS] ✅ Successfully processed item {processed_count}")
            safe_print("[AUTOMATION] 🔄 Continuing to next item...")
            time.sleep(2)  # Brief pause before next iteration
            
        elif result.get("status") == "no_approve_button":
            # No more approve buttons found - this is the SUCCESS exit condition
            safe_print(f"\n{'='*60}")
            safe_print(f"[AUTOMATION] 🎉 ALL ITEMS PROCESSED!")
            safe_print(f"[AUTOMATION] Total items processed: {processed_count}")
            safe_print(f"{'='*60}\n")
            
            return {
                "success": True,
                "message": f"✅ Automation completed successfully! Processed {processed_count} item(s). No more pending approvals found.",
                "status": "completed",
                "processed_count": processed_count
            }
            
        else:
            # An error occurred
            error_count += 1
            safe_print(f"[ERROR] ❌ Error in iteration {processed_count + 1}: {result.get('message')}")
            safe_print(f"[ERROR] Consecutive errors: {error_count}/{max_consecutive_errors}")
            
            if error_count >= max_consecutive_errors:
                # Too many consecutive errors, stop the loop
                safe_print(f"\n{'='*60}")
                safe_print(f"[AUTOMATION] ⚠️ STOPPING - Too many consecutive errors")
                safe_print(f"[AUTOMATION] Total items processed: {processed_count}")
                safe_print(f"{'='*60}\n")
                
                return {
                    "success": False,
                    "message": f"⚠️ Automation stopped after {max_consecutive_errors} consecutive errors. Processed {processed_count} item(s) successfully before errors. Last error: {result.get('message')}",
                    "status": result.get("status", "error"),
                    "processed_count": processed_count,
                    "error": result.get("message")
                }
            
            # Wait a bit longer before retrying after an error
            safe_print("[AUTOMATION] ⏳ Waiting 5 seconds before retry...")
            time.sleep(5)
    
def close_vahan_browser():
    """Close the browser instance if it exists"""
    global driver_instance, is_logged_in
    
    if driver_instance:      
        try:
            safe_print("[CLOSE] Closing browser...")
            driver_instance.quit()
            driver_instance = None
            is_logged_in = False
            clear_session_info()  # Clear session file
            safe_print("[SUCCESS] ✅ Browser closed successfully!")
            return True
        except Exception as e:
            safe_print(f"[ERROR] Error closing browser: {str(e)}")
            driver_instance = None
            is_logged_in = False
            clear_session_info()  # Clear session file
            return False
    else:
        safe_print("[INFO] No browser instance to close")
        clear_session_info()  # Clear session file anyway
        return True
        
if __name__ == "__main__":
    # For testing
    result = start_vahan_browser()
    print(f"\nResult: {result}")
    
    # Keep browser open for testing
    input("\nPress Enter to close browser...")
    close_vahan_browser()
