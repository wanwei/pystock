import os
from dotenv import load_dotenv

load_dotenv()

FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY', '')

STOCKS_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stocks_config.json')
