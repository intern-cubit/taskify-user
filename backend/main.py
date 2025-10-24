import os
import subprocess
import hashlib
import asyncio
import sys 
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Optional 
from firebase_activation import firebase_activation_manager
from local_activation import LocalActivationStorage
from app_config import get_current_config, get_port
from vahan_automation import start_vahan_browser, close_vahan_browser, run_automation, check_browser_status

APP_AUTHOR = "YourCompany"
APP_NAME = "taskify"  # This should match the name in app_config.py

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO) # Already set by basicConfig, but can override for this specific logger if needed

shutdown_event = asyncio.Event()
SHUTDOWN_GRACE_PERIOD = 5

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and shutdown events.
    """
    logger.info("FastAPI app starting up...")
    yield
    logger.info("FastAPI app received shutdown signal. Waiting for graceful termination...")

    try:
        await asyncio.wait_for(shutdown_event.wait(), timeout=SHUTDOWN_GRACE_PERIOD)
        logger.info("FastAPI app received shutdown signal and completed graceful wait.")
    except asyncio.TimeoutError:
        logger.warning(f"FastAPI app did not complete graceful shutdown within {SHUTDOWN_GRACE_PERIOD} seconds.")
    except Exception as e:
        logger.error(f"Error during graceful shutdown wait: {e}", exc_info=True)

    logger.info("FastAPI app completed graceful shutdown.")

# Determine application data directory
if os.name == 'nt':
    app_data_dir = os.getenv('LOCALAPPDATA')
    if app_data_dir is None:
        app_data_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local')
else:
    app_data_dir = os.getenv('XDG_DATA_HOME', os.path.join(os.path.expanduser('~'), '.local', 'share'))

current_config = get_current_config()
APP_NAME_DIR = APP_NAME.lower().replace(" ", "-")
APP_DATA_PATH = os.path.join(app_data_dir, APP_NAME_DIR)
          
try:
    os.makedirs(APP_DATA_PATH, exist_ok=True)
    logger.info(f"Ensured application data directory exists: {APP_DATA_PATH}")
except OSError as e:
    logger.critical(f"CRITICAL ERROR: Could not create application data directory {APP_DATA_PATH}: {e}")
    sys.exit(1) 

local_activation = LocalActivationStorage(APP_DATA_PATH)

# Create FastAPI app (only once!)
app = FastAPI(
    lifespan=lifespan,
    title=current_config["display_name"],
    description=current_config["description"],
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ActivationRequest(BaseModel):
    systemId: str
    activationKey: str
    appName: Optional[str] = APP_NAME

def get_motherboard_serial():
    try:
        try:
            result = subprocess.check_output(
                ["powershell.exe", "-Command", "(Get-WmiObject Win32_BaseBoard).SerialNumber"],
                text=True,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            serial = result.strip()
            if serial:
                return serial
            else:
                logger.warning("Powershell returned empty motherboard serial. Falling back to wmic.")
        except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
            logger.warning(f"Powershell WMI query for motherboard serial failed ({e}). Falling back to wmic.")

        result = subprocess.check_output("wmic baseboard get serialnumber", shell=True, text=True)
        serial = result.split('\n')[1].strip()
        return serial
    except Exception as e:
        logger.error(f"Failed to get motherboard serial: {e}")
        return f"Error getting motherboard serial: {e}"

def get_processor_id():
    try:
        try:
            result = subprocess.check_output(
                ["powershell.exe", "-Command", "(Get-WmiObject Win32_Processor).ProcessorId"],
                text=True,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            processor_id = result.strip()
            if processor_id:
                return processor_id
            else:
                logger.warning("Powershell returned empty processor ID. Falling back to wmic.")
        except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
            logger.warning(f"Powershell WMI query for processor ID failed ({e}). Falling back to wmic.")

    except Exception as e:
        logger.warning(f"Initial attempt for processor ID failed. Falling back to wmic. Error: {e}")
    try:
        result = subprocess.check_output("wmic cpu get processorId", shell=True, text=True)
        processor_id = result.split('\n')[1].strip()
        return processor_id
    except Exception as e:
        logger.error(f"Failed to get processor ID: {e}")
        return f"Error getting processor ID: {e}"

def generate_systemId(processorId: str, motherboardSerial: str) -> str:
    input_string = f"{processorId}:{motherboardSerial}".upper()

    hash_object = hashlib.blake2b(digest_size=32)
    hash_object.update(input_string.encode('utf-8'))
    hex_hash = hash_object.hexdigest().upper()

    big_int_value = int(hex_hash, 16)

    base36_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    base36_result = ""
    while big_int_value > 0:
        big_int_value, remainder = divmod(big_int_value, 36)
        base36_result = base36_chars[remainder] + base36_result

    if not base36_result:
        base36_result = "0"

    base36 = base36_result.upper()

    raw_key = base36.zfill(16)[:16]

    formatted_key = "-".join([raw_key[i:i+4] for i in range(0, len(raw_key), 4)])

    return formatted_key

@app.get("/")
async def root():
    return {
        "message": f"{current_config['display_name']} Backend API", 
        "app_name": APP_NAME,
        "status": "running", 
        "endpoints": ["/system-info", "/check-activation", "/activate-device", "/start-browser", "/check-browser-status", "/run-automation", "/close-browser", "/health"]
    }

@app.get("/system-info")
async def get_system_info_endpoint():
    motherboard_serial = get_motherboard_serial()
    processor_id = get_processor_id()

    if "Error" in motherboard_serial or "Error" in processor_id:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve complete system information. Motherboard: {motherboard_serial}, Processor: {processor_id}"
        )

    systemId = generate_systemId(processor_id, motherboard_serial)
    
    return {"systemId" : systemId} 

@app.get("/check-activation")
async def check_activation_endpoint():
    motherboard_serial = get_motherboard_serial()
    processor_id = get_processor_id()

    if "Error" in motherboard_serial or "Error" in processor_id:
        return {
            "deviceActivation": False,
            "activationStatus": "error",
            "message": "Failed to retrieve complete system information.",
            "success": False,
            "systemId": None,
            "requiresActivationKey": True
        }

    systemId = generate_systemId(processor_id, motherboard_serial)
    
    # Check if we have stored activation data
    stored_activation = local_activation.get_stored_activation()
    
    if stored_activation and stored_activation.get("system_id") == systemId:
        # We have stored activation, verify with Firebase
        activation_key = stored_activation.get("activation_key")
        
        if activation_key:
            logger.info(f"Found stored activation key, verifying with Firebase")
            stored_app_name = stored_activation.get("app_name")
            app_name = APP_NAME  # Always use current app name instead of stored one
            logger.info(f"Stored app name: {stored_app_name}, Using app name: {app_name}")
            result = firebase_activation_manager.verify_activation(systemId, activation_key, app_name)
            
            if result.get("success"):
                return {
                    "deviceActivation": True,
                    "activationStatus": "active",
                    "message": "Device is activated and ready to use",
                    "success": True,
                    "systemId": systemId,
                    "requiresActivationKey": False
                }
            else:
                # Stored key is invalid, clear it
                local_activation.clear_activation()
                return {
                    "deviceActivation": False,
                    "activationStatus": result.get("activationStatus", "invalid"),
                    "message": result.get("message", "Stored activation is no longer valid. Please enter your activation key."),
                    "success": False,
                    "systemId": systemId,
                    "requiresActivationKey": True
                }
    
    # No stored activation or verification failed
    return {
        "deviceActivation": False,
        "activationStatus": "not_activated",
        "message": f"Please enter your activation key for {APP_NAME}.",
        "success": False,
        "systemId": systemId,
        "requiresActivationKey": True
    }

@app.post("/activate-device")
async def activate_device_endpoint(request: ActivationRequest):
    """
    Activate device with provided activation key using Firebase
    """
    try:
        # Verify activation with Firebase
        result = firebase_activation_manager.verify_activation(
            request.systemId, 
            request.activationKey,
            request.appName
        )
        
        if result.get("success"):
            # Save activation locally for future use (always use current APP_NAME)
            local_activation.save_activation(request.systemId, request.activationKey, APP_NAME)
            
            return {
                "deviceActivation": True,
                "activationStatus": "active",
                "message": "Device activated successfully!",
                "success": True,
                "systemId": request.systemId
            }
        else:
            return {
                "deviceActivation": False,
                "activationStatus": result.get("activationStatus", "invalid"),
                "message": result.get("message", "Invalid activation key"),
                "success": False,
                "systemId": request.systemId
            }
            
    except Exception as e:
        logger.error(f"Error during device activation: {e}")
        return {
            "deviceActivation": False,
            "activationStatus": "error",
            "message": f"Activation error: {str(e)}",
            "success": False,
            "systemId": request.systemId
        }
        
@app.post("/logout")
async def logout_endpoint():
    """Clear local activation data on logout"""
    try:
        local_activation.clear_activation()
        logger.info("Cleared local activation data on logout")
        return JSONResponse(content={"success": True, "message": "Logged out successfully. Activation data cleared."})
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail=f"Error during logout: {str(e)}")

@app.get("/health")
async def health_check():
    logger.info("Health check requested.")
    return {"status": "healthy", "message": "Taskify API is running"}

@app.post("/start-browser")
async def start_browser_endpoint():
    """
    Start the browser and navigate to Vahan website.
    Wait for user login and acknowledge when successful.
    Also reuses existing browser session if already logged in.
    """
    logger.info("Received request to start browser for Vahan automation")
    
    try:
        # Run browser automation in background
        result = start_vahan_browser()
        
        if result.get("success"):
            logger.info("Browser started and login acknowledged successfully")
            return {
                "success": True,
                "message": result.get("message", "Browser started and login acknowledged!"),
                "status": result.get("status", "login_success"),
                "reused_session": result.get("reused_session", False)
            }
        else:
            logger.warning(f"Browser start failed: {result.get('message')}")
            return {
                "success": False,
                "message": result.get("message", "Failed to start browser"),
                "status": result.get("status", "error")
            }
            
    except Exception as e:
        logger.error(f"Error in start-browser endpoint: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error starting browser: {str(e)}",
            "status": "error"
        }

@app.get("/check-browser-status")
async def check_browser_status_endpoint():
    """
    Check if browser is open and if user is logged in.
    """
    logger.info("Received request to check browser status")
    
    try:
        result = check_browser_status()
        return {
            "success": True,
            "browser_open": result.get("browser_open", False),
            "logged_in": result.get("logged_in", False),
            "message": result.get("message", "Status checked"),
            "current_url": result.get("current_url", None)
        }
    except Exception as e:
        logger.error(f"Error checking browser status: {e}", exc_info=True)
        return {
            "success": False,
            "browser_open": False,
            "logged_in": False,
            "message": f"Error checking status: {str(e)}"
        }

@app.post("/close-browser")
async def close_browser_endpoint():
    """
    Close the browser instance if it exists.
    """
    logger.info("Received request to close browser")
    
    try:
        result = close_vahan_browser()
        
        if result:
            return {
                "success": True,
                "message": "Browser closed successfully"
            }
        else:
            return {
                "success": False,
                "message": "Failed to close browser"
            }
            
    except Exception as e:
        logger.error(f"Error closing browser: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error closing browser: {str(e)}"
        }

@app.post("/run-automation")
async def run_automation_endpoint():
    """
    Run the automation process after login.
    Runs in a loop until all pending applications are processed.
    """
    logger.info("Received request to run automation")
    
    try:
        result = run_automation()
        
        if result.get("success"):
            logger.info(f"Automation completed successfully. Processed {result.get('processed_count', 0)} items.")
            return {
                "success": True,
                "message": result.get("message", "Automation completed successfully!"),
                "status": result.get("status", "completed"),
                "processed_count": result.get("processed_count", 0)
            }
        else:
            logger.warning(f"Automation failed: {result.get('message')}")
            return {
                "success": False,
                "message": result.get("message", "Automation failed"),
                "status": result.get("status", "error"),
                "processed_count": result.get("processed_count", 0),
                "error": result.get("error", result.get("message"))
            }
            
    except Exception as e:
        logger.error(f"Error in run-automation endpoint: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error running automation: {str(e)}",
            "status": "error",
            "processed_count": 0,
            "error": str(e)
        }

@app.post("/shutdown")
async def shutdown_backend_endpoint():
    logger.info("Received shutdown request for backend. Signaling graceful exit...")
    
    # Close browser before shutdown
    try:
        close_vahan_browser()
    except Exception as e:
        logger.error(f"Error closing browser during shutdown: {e}")
    
    shutdown_event.set() # Set the event to unblock the lifespan shutdown
    return {"message": "Backend shutdown initiated successfully."}