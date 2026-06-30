import json
import os
import logging

logger = logging.getLogger("AutoPiano.Config")

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "playback_speed": 1.0,
    "transposition": 0,
    "humanize": False,
    "hotkeys": True,
    "mapping": "virtual_piano.json",
    "start_delay": 5
}

class ConfigManager:
    def __init__(self, config_path=CONFIG_FILE):
        self.config_path = config_path
        self.data = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Loads configuration from JSON file. Creates it with defaults if it doesn't exist."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge loaded keys into our dictionary
                    for k, v in loaded.items():
                        if k in self.data:
                            self.data[k] = v
                logger.info("Configuration loaded from %s", self.config_path)
            except Exception as e:
                logger.exception("Failed to load configuration from %s. Using default config.", self.config_path)
        else:
            logger.info("Configuration file not found. Creating a new one with defaults at %s", self.config_path)
            self.save()

    def save(self):
        """Saves current configuration parameters to JSON file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
            logger.info("Configuration successfully saved to %s", self.config_path)
        except Exception as e:
            logger.exception("Failed to save configuration to %s", self.config_path)

    def get(self, key):
        """Retrieves a configuration value."""
        return self.data.get(key)

    def set(self, key, value):
        """Sets a configuration value and persists it to disk."""
        if key in self.data:
            self.data[key] = value
            self.save()
        else:
            logger.warning("Attempted to set invalid configuration key: %s", key)
