# ssl_vista/config.py

import os

class Config(dict):
    def __setitem__(self, key, value):
        print(f"SSL vista configuration updated: {key} = {value}")
        super().__setitem__(key, value)

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            print(f"SSL vista configuration updated: {key} = {value}")
        super().update(*args, **kwargs)

# Initialize the configuration dictionary
CONFIG = Config({
    "DEBUG": os.getenv("SSL_VISTA_DEBUG", "False").lower() in ("true", "1", "yes"),
    "DEBUG_INFO": os.getenv("SSL_VISTA_DEBUG_INFO", "False").lower() in ("true", "1", "yes"),
    "WARNINGS": os.getenv("SSL_VISTA_WARNINGS", "True").lower() in ("true", "1", "yes"),
})
