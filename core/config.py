import json
import os
from dotenv import load_dotenv
from core.logger import logger
from typing import Any, Dict # Import for type hinting

SETTINGS_FILE = "settings.json"

class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors."""
    pass

class Config:
    _instance = None
    _data: dict = {} # Internal storage for settings

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
            cls._instance._load_env_overrides() # Load environment variables after settings
            cls._instance.validate() # Validate configuration on startup
        return cls._instance

    def _load_settings(self):
        """
        Load configuration from SETTINGS_FILE into self._data.
        
        If the file is present and contains valid JSON, parse it and assign the resulting mapping to self._data. If the file is missing, contains invalid JSON, or any other error occurs, set self._data to an empty dict and log an error describing the problem.
        """
        if not os.path.exists(SETTINGS_FILE):
            logger.error(f"Settings file not found: {SETTINGS_FILE}. Please create it.")
            self._data = {}
            return

        try:
            with open(SETTINGS_FILE, 'r') as f:
                self._data = json.load(f)
            logger.info("Settings loaded successfully.")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding settings.json: {e}. Please check your JSON syntax.")
            self._data = {}
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading settings: {e}")
            self._data = {}
    
    def _load_env_overrides(self):
        """
        Load environment variables from .env file and override sensitive settings.
        """
        load_dotenv() # Load environment variables from .env file

        # Override notification settings with environment variables
        notification_settings = self._data.get('notification_settings', {})
        notification_settings['smtp_password'] = os.getenv('SMTP_PASSWORD', notification_settings.get('smtp_password'))
        notification_settings['smtp_username'] = os.getenv('SMTP_USERNAME', notification_settings.get('smtp_username'))
        notification_settings['telegram_bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN', notification_settings.get('telegram_bot_token'))
        notification_settings['telegram_chat_id'] = os.getenv('TELEGRAM_CHAT_ID', notification_settings.get('telegram_chat_id'))
        
        # Override Telegram API credentials if present (used by telethon)
        # These are often separate from the bot token
        notification_settings['telegram_api_id'] = os.getenv('TELEGRAM_API_ID', notification_settings.get('telegram_api_id'))
        notification_settings['telegram_api_hash'] = os.getenv('TELEGRAM_API_HASH', notification_settings.get('telegram_api_hash'))

        self._data['notification_settings'] = notification_settings

    def validate(self):
        """
        Validate the loaded configuration for critical settings.
        
        Raises:
            ConfigValidationError: If any critical configuration setting is missing or invalid.
        """
        errors = []

        # Validate enabled scrapers
        if not self.get('enabled_scrapers'):
            errors.append("`enabled_scrapers` cannot be empty.")
        elif not isinstance(self.enabled_scrapers, list):
            errors.append("`enabled_scrapers` must be a list.")

        # Validate notification settings
        notification_settings = self.get('notification_settings', {})
        if notification_settings.get('enable_email_notifications'):
            required_email_fields = ['smtp_server', 'smtp_port', 'smtp_username', 'smtp_password', 'email_recipients']
            for field in required_email_fields:
                value = notification_settings.get(field)
                if not value or (isinstance(value, str) and value.startswith('REPLACE_ME')):
                    errors.append(f"Email notifications enabled but `{field}` is not configured or uses a placeholder.")
            if not isinstance(notification_settings.get('email_recipients'), list) or not notification_settings.get('email_recipients'):
                errors.append("Email notifications enabled but `email_recipients` must be a non-empty list.")

        if notification_settings.get('enable_telegram_notifications'):
            required_telegram_fields = ['telegram_bot_token', 'telegram_chat_id', 'telegram_api_id', 'telegram_api_hash']
            for field in required_telegram_fields:
                value = notification_settings.get(field)
                if not value or (isinstance(value, str) and value.startswith('REPLACE_ME')):
                    errors.append(f"Telegram notifications enabled but `{field}` is not configured or uses a placeholder.")
            
        # Validate delay_range
        delay_range = self.get('delay_range')
        if not isinstance(delay_range, list) or len(delay_range) != 2 or not all(isinstance(x, (int, float)) for x in delay_range):
            errors.append("`delay_range` must be a list of two numbers (min, max).")
        elif delay_range[0] < 0 or delay_range[1] < delay_range[0]:
            errors.append("`delay_range` min must be >= 0 and max must be >= min.")

        if errors:
            raise ConfigValidationError("\n".join(errors))

    def get(self, key, default=None):
        """
        Retrieve a configuration value by key with a fallback.
        
        Parameters:
            key (str): The settings key to look up.
            default: Value returned if the key is not present in the settings (defaults to None).
        
        Returns:
            The value associated with `key` from the loaded settings, or `default` if the key is absent.
        """
        return self._data.get(key, default)

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
        if name in self._data:
            return self._data[name]
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
    # Test with environment variables (create a .env file first)
    # echo "SMTP_PASSWORD=env_password" > .env
    # python core/config.py
    print(f"SMTP Password (from env or settings): {config.notification_settings.get('smtp_password')}")
    print(f"Telegram Bot Token (from env or settings): {config.notification_settings.get('telegram_bot_token')}")
    
    # Test validation (this will raise an error if settings are not configured)
    try:
        config.validate()
        print("Config validation successful!")
    except ConfigValidationError as e:
        print(f"Config validation failed: {e}")