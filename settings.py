import os
from dotenv import load_dotenv

load_dotenv()

# SMS Activate API
SMS_ACTIVATE_API_KEY = os.getenv("SMS_ACTIVATE_API_KEY")

# Appium settings
DEVICE_NAME = os.getenv("DEVICE_NAME")
APPIUM_SERVER_URL = os.getenv('APPIUM_SERVER_URL')

# Telegram API
APP_API_ID = os.getenv('APP_API_ID')
APP_API_HASH = os.getenv('APP_API_HASH')
APP_PACKAGE = "org.telegram.messenger.web"

# Proxy settings (опционально)
USE_PROXY = os.getenv('USE_PROXY', 'false').lower() == 'true'
PROXY_HOST = os.getenv('PROXY_HOST')
PROXY_PORT = os.getenv('PROXY_PORT')
PROXY_USERNAME = os.getenv('PROXY_USERNAME')  # опционально
PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')  # опционально

# Формирование URL прокси
if USE_PROXY and PROXY_HOST and PROXY_PORT:
    if PROXY_USERNAME and PROXY_PASSWORD:
        PROXY_HTTP = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}"
        PROXY_HTTPS = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}"
    else:
        PROXY_HTTP = f"http://{PROXY_HOST}:{PROXY_PORT}"
        PROXY_HTTPS = f"http://{PROXY_HOST}:{PROXY_PORT}"
else:
    PROXY_HTTP = None
    PROXY_HTTPS = None
