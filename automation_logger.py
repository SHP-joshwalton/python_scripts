import logging
import sys
log_file = "/var/www/logs/SHP_automation.log"
# Configure logging
logging.basicConfig(
    filename=log_file,
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

# Get the log message and level from the command line arguments
if len(sys.argv) < 2:
    print("Usage: logger.py <message> [level]")
    sys.exit(1)

message = sys.argv[1]
log_level = sys.argv[2].upper() if len(sys.argv) > 2 else 'INFO'

if log_level == 'DEBUG':
    logging.debug(message)
elif log_level == 'INFO':
    logging.info(message)
elif log_level == 'WARNING':
    logging.warning(message)
elif log_level == 'ERROR':
    logging.error(message)
elif log_level == 'CRITICAL':
    logging.critical(message)
else:
    print('Invalid log level')
    sys.exit(1)
