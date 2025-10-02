#!/usr/bin/env python3
import os
import sys
import pexpect
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import argparse
import json
import logging
import SHP_config
# Configure logging
# logging.basicConfig(
#     filename='/var/www/scripts/create_user_results.log',
#     filemode='a',
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     level=logging.DEBUG
# )
# Access the environment variables
SERVER_ENVIRONMENT = os.getenv('SERVER_ENVIRONMENT')
import pexpect

def deleteFile(filename, dest):
    file_path = os.path.join(dest, filename)
    # Check if the file exists
    if os.path.exists(file_path):
        # Check if you have permission to write (delete) the file
        if os.access(file_path, os.W_OK):
            try:
                os.remove(file_path)
                finalOutput("success")
            except Exception as e:
                finalOutput("error", str(e))
        else:
            finalOutput("error", "Permission denied: You do not have permission to delete this file.")
    else:
        finalOutput("error", "File not found: The specified file does not exist.")
    

def finalOutput(status, errors = None):
    output = {
        "results": status,
        "errors": errors
    }
    print(json.dumps(output), end="")
    exit()
def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="An example script.")
    parser.add_argument('file_name', type=str, help='A positional argument')
    # Parse the arguments
    args = parser.parse_args()
    deleteFile(args.file_name, dest="/var/www/user_photos")
    
if __name__ == '__main__':
    main()