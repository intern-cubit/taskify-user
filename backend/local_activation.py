import os
import json
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class LocalActivationStorage:
    def __init__(self, app_data_path: str):
        self.app_data_path = app_data_path
        self.activation_file = os.path.join(app_data_path, "activation_data.json")
    
    def save_activation(self, system_id: str, activation_key: str, app_name: str = "taskify") -> bool:
        """
        Save activation key locally after successful verification
        """
        try:
            activation_data = {
                "system_id": system_id,
                "activation_key": activation_key,
                "app_name": app_name,
                "saved_at": __import__('datetime').datetime.now().isoformat()
            }
            
            with open(self.activation_file, 'w') as f:
                json.dump(activation_data, f, indent=2)
            
            logger.info("Activation data saved locally")
            return True
            
        except Exception as e:
            logger.error(f"Error saving activation data: {e}")
            return False
    
    def get_stored_activation(self) -> Optional[Dict[str, str]]:
        """
        Get stored activation data
        """
        try:
            if not os.path.exists(self.activation_file):
                return None
            
            with open(self.activation_file, 'r') as f:
                data = json.load(f)
            
            return {
                "system_id": data.get("system_id"),
                "activation_key": data.get("activation_key"),
                "app_name": data.get("app_name", "taskify")  # Default for backward compatibility
            }
            
        except Exception as e:
            logger.error(f"Error reading stored activation: {e}")
            return None
    
    def clear_activation(self) -> bool:
        """
        Clear stored activation data
        """
        try:
            if os.path.exists(self.activation_file):
                os.remove(self.activation_file)
                logger.info("Stored activation data cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing activation data: {e}")
            return False
    
    def has_stored_activation(self) -> bool:
        """
        Check if activation is stored locally
        """
        return os.path.exists(self.activation_file)