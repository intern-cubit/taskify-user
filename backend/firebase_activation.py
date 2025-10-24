import firebase_admin
from firebase_admin import credentials, firestore
import os
import sys
import logging

logger = logging.getLogger(__name__)

def initialize_firebase():
    """Initialize Firebase Admin SDK with service account key"""
    try:
        # Path to your Firebase service account key JSON file
        # Handle both development and PyInstaller bundled scenarios
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle
            service_account_path = os.path.join(sys._MEIPASS, "firebase-service-account.json")
        else:
            # Running in development
            service_account_path = os.path.join(os.path.dirname(__file__), "firebase-service-account.json")
        
        if not os.path.exists(service_account_path):
            logger.warning(f"Firebase service account file not found at: {service_account_path}")
            return None
            
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
        
        # Get Firestore client
        db = firestore.client()
        logger.info("Firebase initialized successfully")
        return db
    except Exception as e:
        logger.error(f"Error initializing Firebase: {e}")
        return None

# Initialize Firestore client
db = initialize_firebase()

class FirebaseActivationManager:
    def __init__(self):
        self.collection_name = "activation_keys"
        self.db = db
    
    def verify_activation(self, system_id: str, activation_key: str, app_name: str = "taskify") -> dict:
        """
        Verify if the system_id and activation_key pair exists and is valid in Firebase
        """
        try:
            if not self.db:
                return {
                    "deviceActivation": False,
                    "activationStatus": "error",
                    "message": "Firebase connection not available",
                    "success": False
                }
            
            # Get document by activation key
            doc_ref = self.db.collection(self.collection_name).document(activation_key)
            doc = doc_ref.get()
            
            if not doc.exists:
                return {
                    "deviceActivation": False,
                    "activationStatus": "invalid_key",
                    "message": "Invalid activation key",
                    "success": False
                }
            
            data = doc.to_dict()
            
            # Check if system_id matches
            if data.get("system_id") != system_id:
                return {
                    "deviceActivation": False,
                    "activationStatus": "key_mismatch",
                    "message": "Activation key does not match this system",
                    "success": False
                }
            
            # Check if app_name matches
            if data.get("app_name") != app_name:
                return {
                    "deviceActivation": False,
                    "activationStatus": "wrong_app",
                    "message": f"Activation key is for {data.get('app_name', 'Unknown')} app, not {app_name}",
                    "success": False
                }
            
            # Check if still active
            if not data.get("is_active", False):
                return {
                    "deviceActivation": False,
                    "activationStatus": "inactive",
                    "message": "Activation key has been deactivated",
                    "success": False
                }
            
            # Check expiry
            expires_at = data.get("expires_at")
            if expires_at and expires_at.timestamp() < __import__('time').time():
                return {
                    "deviceActivation": False,
                    "activationStatus": "expired",
                    "message": "Activation key has expired",
                    "success": False
                }
            
            return {
                "deviceActivation": True,
                "activationStatus": "active",
                "message": "Device is activated and ready to use",
                "success": True,
                "customer_name": data.get("customer_name", ""),
                "expires_at": expires_at.isoformat() if expires_at else None
            }
            
        except Exception as e:
            logger.error(f"Error verifying activation in Firebase: {e}")
            return {
                "deviceActivation": False,
                "activationStatus": "error",
                "message": f"Verification error: {str(e)}",
                "success": False
            }

# Create global instance
firebase_activation_manager = FirebaseActivationManager()