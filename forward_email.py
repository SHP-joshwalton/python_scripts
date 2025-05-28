#!/usr/bin/env python3
import SHP_config
from GAM_user_exist import check_user_exists
import os
import logging
import pexpect # type: ignore
import re
import argparse
import json

SERVER_ENVIRONMENT = os.getenv('SERVER_ENVIRONMENT')
GAM_USER = os.getenv('GAM_USER')
GAM_PASSWORD = os.getenv('GAM_PASSWORD')
def setup_logging():
    logging.basicConfig(
        filename='/var/www/logs/forward_email.log',
        filemode='a',
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.DEBUG
    )



def parse_arguments():
    parser = argparse.ArgumentParser(description="Manage forwarding email addresses.")
    parser.add_argument('method', choices=['SHOW', 'ADD', 'DELETE'], help='Method: SHOW, ADD, DELETE')
    parser.add_argument('email', help='Target email address')
    parser.add_argument('forward_email', nargs='?', default=None, help='Forwarding email (optional)')
    return parser.parse_args()


def extract_emails(text):
    pattern = r'([\w\.-]+@[\w\.-]+)'
    return re.findall(pattern, text)


def is_shpbeds_email(email):
    return True if email.endswith("@shpbeds.org") else False


def is_real_email(email):
    if is_shpbeds_email(email) == False:
        return False
    output = run_GAM_Command(f"gam info user {email}")
    return "User:" in output and "Primary Email:" in output


def run_GAM_Command(command):
    if SERVER_ENVIRONMENT == "development":
        return 'development can\'t be used with GAM.'

    logging.debug(f"Running command: {command}")
    child = pexpect.spawn(f"su {GAM_USER}", timeout=30)
    child.expect("Password:")
    child.sendline(GAM_PASSWORD)
    child.expect("$")
    child.sendline(command)
    child.expect("$")
    child.sendline("exit")
    child.expect(pexpect.EOF)
    output = child.before.decode("utf-8")
    logging.debug(f"Output: {output}")
    return output


def final_output(status, errors=[]):
    print(json.dumps({"results": status, "errors": errors}))
    exit(0)


def show_forwarding_addresses(user, return_list=False):
    if SERVER_ENVIRONMENT == "development":
        addresses = [
            {'email': 'josh.walton@shpbeds.org', 'status': 'accepted'},
            {'email': 'zander.krauch@shpbeds.org', 'status': 'accepted'}
        ]
        final_output(addresses)

    email_exists = check_user_exists(user)
    if not email_exists["exists"]:
        final_output("error", [f"The email {user}@shpbeds.org does not exist in Google Workspace"])
        #final_output("error", [f"The email {user} does not exist in Google Workspace"])
        pass
    output = run_GAM_Command(f"gam user \"{user}\" show forwardingaddress")
    addresses = [
        {'email': email, 'status': 'accepted'}
        for line in output.splitlines()
        for email in extract_emails(line) if "Forwarding Address:" in line
    ]
    if return_list:
        return addresses    
    print(json.dumps({"results": 'success', "forwarding_addresses":addresses, "errors": None}))
    exit(0)

def add_forwarding_address(user, forwarding_email):
    if SERVER_ENVIRONMENT == "development":
        final_output("success")
    forwarding_email_exists = check_user_exists(forwarding_email)
    email_exists = check_user_exists(user)
    errors = []
    if not email_exists["exists"]:
        errors.append(f"The email {user}@shpbeds.org does not exist in Google Workspace")
    if not forwarding_email_exists["exists"]:
        errors.append(f"The forwarding email {forwarding_email} does not exist in Google Workspace")
    existing_addresses = show_forwarding_addresses(user, return_list=True)
    if forwarding_email in existing_addresses:
        errors.append(f"The forwarding address {forwarding_email} already exists.")
    if len(errors) > 0:
        final_output("error", errors)

    output = run_GAM_Command(f"gam user {user} add forwardingaddress {forwarding_email}")

    if "Add 1 Forwarding Address" in output:
        run_GAM_Command(f"gam user {user} filter to {user} forward {forwarding_email}")
        final_output("success")

    final_output("error", ["Failed to add forwarding address."])


def delete_forwarding_address(user, forwarding_email):
    output = run_GAM_Command(f"gam user {user} delete forwardingaddress {forwarding_email}")
    if "Delete 1 Forwarding Address" in output:
        final_output("success")
    final_output("error", ["No forwarding address was deleted."])

def main():
    setup_logging()
    args = parse_arguments()
    actions = {
        "SHOW": lambda: show_forwarding_addresses(args.email),
        "ADD": lambda: add_forwarding_address(args.email, args.forward_email),
        "DELETE": lambda: delete_forwarding_address(args.email, args.forward_email)
    }

    action = actions.get(args.method)
    if action:
        action()
    else:
        final_output("Error", [f"Invalid method: {args.method}. Expected: SHOW, ADD, DELETE"])


if __name__ == '__main__':
    main()
