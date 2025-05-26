import os
from utils.config import config

os.environ['OPENAI_API_KEY'] = config['api_key']
os.environ['OPENAI_API_BASE'] = config['api_base_url']
os.environ['OPENAI_BASE_URL'] = config['api_base_url']