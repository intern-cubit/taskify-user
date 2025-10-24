import uvicorn
import main as fastapi_app # Import your FastAPI app from main.py
import os
import sys
import logging
import logging.config

# Fix for PyInstaller logging issue
def fix_logging_for_pyinstaller():
    """Fix logging configuration issues when running in PyInstaller executable"""
    # Ensure stdout is available
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')

# Apply the fix
fix_logging_for_pyinstaller()

# Create a simple logging configuration that works with PyInstaller
SIMPLE_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        },
        "access": {
            "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["default"],
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
    },
}

# Define a default port and host
PORT = int(os.environ.get("FASTAPI_PORT", 8000))
HOST = os.environ.get("FASTAPI_HOST", "127.0.0.1")

# Get a logger for run_server.py
server_logger = logging.getLogger("run_server")
server_logger.setLevel(logging.INFO) # Set level for this logger
# Ensure the handler is only added once to avoid duplicate log messages
if not server_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(SIMPLE_LOG_CONFIG["formatters"]["default"]["format"])
    handler.setFormatter(formatter)
    server_logger.addHandler(handler)

# Apply the simple log config globally
try:
    logging.config.dictConfig(SIMPLE_LOG_CONFIG)
except Exception as e:
    # Fallback to basic logging if dictConfig fails
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout
    )

# Main execution wrapped for Windows multiprocessing support
if __name__ == '__main__':
    server_logger.info(f"Starting FastAPI server on http://{HOST}:{PORT}")
    
    # Check if we should enable auto-reload (disabled by default for faster startup)
    # Set ENABLE_RELOAD=true environment variable to enable auto-reload
    ENABLE_RELOAD = os.environ.get("ENABLE_RELOAD", "false").lower() == "true"
    
    if ENABLE_RELOAD:
        server_logger.info("🔄 Auto-reload is ENABLED - Server will restart when files change")
        server_logger.info("⚠️  Note: First startup with reload may take 20-30 seconds on Windows")
        server_logger.info("Running in development mode with auto-reload")
    else:
        server_logger.info("⚡ Auto-reload is DISABLED for fast startup")
        server_logger.info("💡 To enable auto-reload: set ENABLE_RELOAD=true")

    try:
        if ENABLE_RELOAD:
            # Development mode with auto-reload
            uvicorn.run(
                "main:app",  # String path to the app
                host=HOST,
                port=PORT,
                log_level="info",
                reload=True,  # Enable auto-reload
                reload_dirs=[os.path.dirname(__file__)],  # Watch the backend directory
                reload_delay=0.5  # Add a small delay to batch changes
            )
        else:
            # Production mode without reload
            config = uvicorn.Config(
                app=fastapi_app.app,
                host=HOST,
                port=PORT,
                log_level="info",
                log_config=SIMPLE_LOG_CONFIG,
                lifespan="on"
            )
            server = uvicorn.Server(config)
            server.run()

        server_logger.info("Uvicorn server has gracefully stopped.")

    except Exception as e:
        server_logger.critical(f"CRITICAL ERROR: Failed to start or run FastAPI server: {e}", exc_info=True)
        sys.exit(1)