import logging

TG_TOKEN = "1225125611:AAFskmF899-5tRCd9IZgv240Nq3XV6CgXiM"
TG_NEED_PROXY = False
TG_PROXY = "https://telegg.ru/orig/bot"

LOGGER_FORMAT = '%(asctime)s %(levelname)s\t# %(message)s'

DEFAULT_LOGGER_LEVEL = logging.WARNING
ETERNAL_LOGGER_LEVEL = logging.INFO
STDOUT_LOG = False
LOG_FILE = "eternal.log"

def stdout_log():
    return STDOUT_LOG

def get_log_file():
    return LOG_FILE

def get_logger_format():
    return LOGGER_FORMAT

def get_default_logger_level():
    return DEFAULT_LOGGER_LEVEL

def get_eternal_logger_level():
    return ETERNAL_LOGGER_LEVEL

def get_token():
    return TG_TOKEN

def need_proxy():
    return TG_NEED_PROXY

def get_proxy():
    return TG_PROXY
