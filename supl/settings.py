"""
    Simple module for dynamically accessing the settings from yaml file
"""
import os
import time
import yaml

class Settings:
    """
        Class to access the yaml config file in supl module, allows as to pass
        just the instance arround and not carrying about the paths and file
        searching.
    """
    def __init__(self, config_path="config.yaml", cache_ttl=5):
        """
        Initializes the config loader.

        :param config_path: Path to the YAML config file.
        :param cache_ttl: Time in seconds before reloading the config (default: 5s).
        """
        self.config_path = config_path
        self.cache_ttl = cache_ttl
        self.config = {}
        self.last_loaded = 0  # Timestamp of last load

    def load_config(self):
        """Reads the YAML file only if CACHE_TTL has passed or if it has changed."""
        current_time = time.time()

        # Reload only if TTL has passed or the file does not exist in memory
        if current_time - self.last_loaded > self.cache_ttl:
            if not os.path.exists(self.config_path):
                print(f"Warning: Config file '{self.config_path}' not found.")
                self.config = {}
            else:
                try:
                    with open(self.config_path, "r", encoding="utf-8") as file:
                        self.config = yaml.safe_load(file) or {}
                        self.last_loaded = current_time
                except (yaml.YAMLError, OSError) as e:
                    print(f"Error reading config file '{self.config_path}': {e}")
                    self.config = {}

    def get(self, key, default=None):
        """Fetches a value from the config file, auto-reloading if necessary."""
        self.load_config()
        return self.config["settings"].get(key, default)
