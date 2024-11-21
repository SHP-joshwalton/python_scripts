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
parser.add_argument('method_arg', type=str, help='The method argument')
parser.add_argument('email_arg', type=str, help='A positional argument')
parser.add_argument('forward_email_arg', type=str, help='A positional argument', default=None, nargs='?',)

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
logging.basicConfig(
    filename='/var/www/scripts/forward_email.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

def get_items_from_list_containing(items, lookFor):
    newList = []
    for item in items:
        if lookFor in item:
            newList.append(item)
    return newList

def partOfTextNeeded(text, start, end):
	try:
		start_index = text.find(start) + len(start)
		end_index = text.find(end, start_index)
		if start_index - len(start) == -1 or end_index == -1:
			return ""
		return text[start_index:end_index]
	except ValueError:
		return ""
def showForwardingAddresses(user):
    gam_command = f"gam user \"{user}\" show forwardingaddress"

    output = run_GAM_Command(gam_command)
    forwardingaddress = output.split('\n')
    
    email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+')
    addresses = get_items_from_list_containing(forwardingaddress, "Forwarding Address:")
    emails = []
    for address in addresses:
        dictionary = {}
        match = email_pattern.search(address)
        if match:
            dictionary['email'] = match.group(0)
            dictionary['status'] = address.split('Verification Status:')[-1].strip().split(" ")[0]
            emails.append(dictionary)
    finalOutput(emails)
def add_forwarding_address(user, forwarding_email):
    if not is_shpbeds_email(forwarding_email):
        finalOutput("Error", ["Forwarding emails have to be shpbeds.org addresses"])
        
    gam_forwarding_command = f"gam user {user} add forwardingaddress {forwarding_email}"
    output = run_GAM_Command(gam_forwarding_command)
    if "Add 1 Forwarding Address" in output:
        output = run_GAM_Command(f"gam user {user} filter to {user} forward {forwarding_email}")
        finalOutput("success")
def delete_forwarding_address(user, forwarding_email):
    gam_command = f"gam user {user} delete forwardingaddress {forwarding_email}"
    output = run_GAM_Command(gam_command)
    if "Delete 1 Forwarding Address" in output:
        finalOutput("success")
    finalOutput("error", "no forwarding address was deleted")
    
    
def run_GAM_Command(commandToRun):
    logging.debug(f"Running command: {commandToRun}")
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
    logging.debug(f"Output Is: {output}")
    return output
def finalOutput(status, errors = None):
    output = {
        "results": status,
        "errors": errors
    }
    print(json.dumps(output))
    exit(0)
def is_shpbeds_email(email):
    pattern = r'^[\w\.-]+@shpbeds\.org$'
    return re.match(pattern, email) is not None

def main():
    methodCommand = args.method_arg
    email = args.email_arg
    if email is None:
        finalOutput("Error", f"database does not have a user with that email, {email}")
    output = ""
    match methodCommand:
        case "SHOW":
            showForwardingAddresses(email)
        case "ADD":
            forward_email = args.forward_email_arg
            if not is_shpbeds_email(forward_email):
                finalOutput("Error", ["The forwarding address must be a shpbeds email address"])
            add_forwarding_address(email, forward_email)
        case "DELETE":
            forward_email = args.forward_email_arg
            delete_forwarding_address(email, forward_email)
        case _:
            finalOutput("Error", ["expected one of the following: SHOW, ADD, DELETE", f"Got {methodCommand} and {email}"])
            pass
if __name__ == '__main__':
    main()
    

#CASantaBarbaraCoN