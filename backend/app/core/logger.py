import logging

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# create and add a local console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)

logger.info("Logger Setup Complete!")