import logging

LOG_FORMAT = "%(levelname)s:     %(asctime)s\t%(name)s:\t%(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
console_handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO) 
logger.addHandler(console_handler)

logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("pymongo").setLevel(logging.WARNING)

logger.info("✅ Logging is configured successfully!")
