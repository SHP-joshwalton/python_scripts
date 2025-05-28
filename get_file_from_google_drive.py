#!/usr/bin/env python3
import os
import sys
import pexpect
import SHP_config
import mysql.connector
from mysql.connector import Error
import argparse
import json
import logging
# Create the parser
parser = argparse.ArgumentParser(description="An example script.")
parser.add_argument('file_name', type=str, help='A positional argument')

# Parse the arguments
args = parser.parse_args()
# Configure logging
# logging.basicConfig(
#     filename='/var/www/scripts/create_user_results.log',
#     filemode='a',
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     level=logging.DEBUG
# )
# Access the environment variables
GAM_USER = os.getenv('GAM_USER')
GAM_PASSWORD = os.getenv('GAM_PASSWORD')
import pexpect

def copyFile(filename, dest):
    command = f"su {GAM_USER}"
    
    try:
        child = pexpect.spawn(command, timeout=30)
        
        # Handle initial password prompt for `su`
        child.expect("Password:")
        child.sendline(GAM_PASSWORD)
        child.expect(r"\$")  # Matches a typical bash prompt ($)
        
        # Change directory to `dest`
        child.sendline(f"cd {dest}")
        child.expect(r"\$")
        
        # Run rclone command to copy the file
        child.sendline(f"rclone copy gamautomation:/User_Submit_Photos/{filename} ./")
        child.expect(r"\$")
        # Exit the `su` session
        child.sendline("exit")
        child.expect(pexpect.EOF)
        
        # Capture output for logging
        output = child.before.decode("utf-8")
        # logging.debug(f"GAM Output Is: {output}")
        return output
    
    except pexpect.TIMEOUT:
        print("Timeout occurred during one of the steps.")
        return None
    except pexpect.EOF:
        print("Process ended unexpectedly.")
        return None
    finally:
        child.close()

def finalOutput(status, errors = None):
    output = {
        "results": status,
        "errors": errors
    }
    print(json.dumps(output), end="")
    exit()
def main():
    copyFile(args.file_name, dest="/var/www/user_photos")
if __name__ == '__main__':
    main()