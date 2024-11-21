#!/usr/bin/env python3
import os
import sys
import logging
import pexpect
from dotenv import load_dotenv
import re
import argparse
import json

# Create the parser
parser = argparse.ArgumentParser(description="An example script.")

# Add arguments
parser.add_argument('email_arg', type=str, help='A positional argument')

# Parse the arguments
args = parser.parse_args()
# Specify the path to the .env file
dotenv_path = os.path.join('/var/www/scripts', '.env')
# Load the .env file
load_dotenv(dotenv_path)
# Access the environment variables
gam_user = os.getenv('GAM_USER')
gam_user_pass = os.getenv('GAM_PASSWORD')

# Configure logging

def run_GAM_Command(commandToRun):
    user = gam_user
    password = gam_user_pass
    command = f"su {user}"
    
    child = pexpect.spawn(command, timeout=30)
    child.expect("Password:")
    child.sendline(password)
    child.expect("$")
    child.sendline(commandToRun)
    child.expect("$")
    child.sendline("exit")
    child.expect(pexpect.EOF)
    output = child.before.decode("utf-8")
    return output
def main():
    email = args.email_arg
    if email is None:
        finalOutput("Error", f"database does not have a user with that email, {email}")
    output = run_GAM_Command(f"gam info user {email}")
    
    # Parsing the relevant fields using regex

    parsed_data = {

        'User': re.search(r'User:\s(.+)', output).group(1).strip(),

        'First Name': re.search(r'First Name:\s(.+)', output).group(1).strip(),

        'Last Name': re.search(r'Last Name:\s(.+)', output).group(1).strip(),

        'Full Name': re.search(r'Full Name:\s(.+)', output).group(1).strip(),

        'Languages': re.search(r'Languages:\s(.+)', output).group(1).strip(),

        'Is Super Admin': re.search(r'Is a Super Admin:\s(.+)', output).group(1).strip(),

        'Is Delegated Admin': re.search(r'Is Delegated Admin:\s(.+)', output).group(1).strip(),

        '2-step enrolled': re.search(r'2-step enrolled:\s(.+)', output).group(1).strip(),

        '2-step enforced': re.search(r'2-step enforced:\s(.+)', output).group(1).strip(),

        'Has Agreed to Terms': re.search(r'Has Agreed to Terms:\s(.+)', output).group(1).strip(),

        'IP Whitelisted': re.search(r'IP Whitelisted:\s(.+)', output).group(1).strip(),

        'Account Suspended': re.search(r'Account Suspended:\s(.+)', output).group(1).strip(),

        'Is Archived': re.search(r'Is Archived:\s(.+)', output).group(1).strip(),

        'Must Change Password': re.search(r'Must Change Password:\s(.+)', output).group(1).strip(),

        'Google Unique ID': re.search(r'Google Unique ID:\s(.+)', output).group(1).strip(),

        'Customer ID': re.search(r'Customer ID:\s(.+)', output).group(1).strip(),

        'Mailbox Setup': re.search(r'Mailbox is setup:\s(.+)', output).group(1).strip(),

        'Included in GAL': re.search(r'Included in GAL:\s(.+)', output).group(1).strip(),

        'Creation Time': re.search(r'Creation Time:\s(.+)', output).group(1).strip(),

        'Last Login Time': re.search(r'Last login time:\s(.+)', output).group(1).strip(),

        'Google Org Unit Path': re.search(r'Google Org Unit Path:\s(.+)', output).group(1).strip(),

        'Gender': re.search(r'Gender:\s+type:\s(.+)', output).group(1).strip(),

        'Organization Description': re.search(r'description:\s(.+)', output).group(1).strip(),

        'Cost Center': re.search(r'costCenter:\s(.+)', output).group(1).strip(),

        'Department': re.search(r'department:\s(.+)', output).group(1).strip(),

        'Phone': re.search(r'Phones:\s+type:\swork\s+value:\s(.+)', output).group(1).strip()
    }
    print(json.dumps(parsed_data), end="\n")
if __name__ == '__main__':
    main()
    

#CASantaBarbaraCoN