import json
import os
from core.logger import logger

SETTINGS_FILE = "settings.json"

class Config:
    _instance = None

    def __new__(cls):
        """
        Create or return the singleton Config instance.
        
        On first construction, initializes the single Config object and loads settings from the settings file.
        
        Returns:
            Config: The singleton Config instance.
        """
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_settings()
        return cls._instance

    def _load_settings(self):
        """
        Load configuration from SETTINGS_FILE into self.settings.
        
        If the file is present and contains valid JSON, parse it and assign the resulting mapping to self.settings. If the file is missing, contains invalid JSON, or any other error occurs, set self.settings to an empty dict and log an error describing the problem.
        """
        if not os.path.exists(SETTINGS_FILE):
            logger.error(f"Settings file not found: {SETTINGS_FILE}. Please create it.")
            self.settings = {}
            return

        try:
            with open(SETTINGS_FILE, 'r') as f:
                self.settings = json.load(f)
            logger.info("Settings loaded successfully.")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding settings.json: {e}. Please check your JSON syntax.")
            self.settings = {}
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading settings: {e}")
            self.settings = {}

    def get(self, key, default=None):
        """
        Retrieve a configuration value by key with a fallback.
        
        Parameters:
            key (str): The settings key to look up.
            default: Value returned if the key is not present in the settings (defaults to None).
        
        Returns:
            The value associated with `key` from the loaded settings, or `default` if the key is absent.
        """
        return self.settings.get(key, default)

    def __getattr__(self, name):
        """
        Provide attribute-style access to configuration keys.
        
        Parameters:
            name (str): The configuration key to retrieve.
        
        Returns:
            The value associated with `name` from the loaded settings.
        
        Raises:
            AttributeError: If `name` is not present in the settings.
        """
        if name in self.settings:
            return self.settings[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

# Initialize and expose a single instance of the Config
config = Config()

if __name__ == "__main__":
    # Example usage
    print(f"Delay Range: {config.delay_range}")
    print(f"Enabled Scrapers: {config.enabled_scrapers}")
    print(f"Use Proxies: {config.use_proxies}")
    print(f"Retry Attempts: {config.retry_attempts}")
    print(f"HTTP Timeout: {config.http_timeout}")
    print(f"User Agents (first one): {config.user_agents[0] if config.user_agents else 'N/A'}")

    # Test with a non-existent key
    print(f"Non-existent key: {config.get('non_existent_key', 'default_value')}")