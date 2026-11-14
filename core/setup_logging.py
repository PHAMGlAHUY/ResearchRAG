import logging.config
import yaml

def setup_logging():
    with open("config/logging.yaml", encoding='utf-8') as file:
        logging.config.dictConfig(yaml.safe_load(file)) # doc file yaml va chuyen sang python dict