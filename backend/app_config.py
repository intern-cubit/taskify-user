# App Configuration
# This file contains configuration for different versions of the application

# Current application name - This app is always wa-bomb
import os
APP_NAME = "taskify"  # This WhatsApp automation app always uses "wa-bomb"

# App-specific configurations for all apps in the system
APP_CONFIGS = {
    "wa-bomb": {
        "display_name": "WA Bomb - WhatsApp Marketing",
        "description": "WhatsApp Marketing and Automation Tool",
        "port": 8000,
        "frontend_port": 5173
    },
    "mail-storm": {
        "display_name": "MailStorm - Email Marketing", 
        "description": "Email Marketing and Campaign Management Tool",
        "port": 8000,
        "frontend_port": 5173
    },
    "taskify": {
        "display_name": "Taskify - Making Tasks Simpler",
        "description": "Automate Vehicle Registration Form Filling",
        "port": 8000,
        "frontend_port": 5173
    }
}

def get_port():
    """Get port for current app"""
    return get_current_config()["port"]

def get_current_config():
    """Get configuration for current app"""
    return APP_CONFIGS.get(APP_NAME, APP_CONFIGS["taskify"])