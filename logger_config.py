import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set log level to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Define log message format
    handlers=[
        logging.FileHandler("/var/www/scripts/logs/GAM.log"),  # Log to a file
    ]
)

# Function to get the configured logger
def get_logger(name):
    return logging.getLogger(name)

# Example usage
logger = logging.getLogger(__name__)

def main():
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

if __name__ == "__main__":
    main()
