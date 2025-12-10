import json
import os
from core.logger import logger

SETTINGS_FILE = "settings.json"

class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_settings()
        return cls._instance

    def _load_settings(self):
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
        return self.settings.get(key, default)

    def __getattr__(self, name):
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
