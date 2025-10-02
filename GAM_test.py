import subprocess
import json
import sys
import SHP_config
import os
import logging
import pexpect # type: ignore

import shlex

SERVER_ENVIRONMENT = os.getenv('SERVER_ENVIRONMENT')
GAM_USER = os.getenv('GAM_USER')
GAM_PASSWORD = os.getenv('GAM_PASSWORD')
GAM_PATH = os.getenv('GAM_PATH', '/home/gamadmin/bin/gamadv-xtd3/gam')  # Default path if not set
def run_GAM_Command(commandToRun):
    if SERVER_ENVIRONMENT == "development":
        return "This is development"

    user = GAM_USER
    password = GAM_PASSWORD

    # Properly quote the command for shell safety
    safe_command = shlex.quote(commandToRun)

    # Full command to run GAM as the user with `su`
    su_command = f"su {user} -c {safe_command}"
    print(f"Running command: {su_command}")
    try:
        child = pexpect.spawn(su_command, timeout=30)
        child.expect("Password:")
        child.sendline(password)
        child.expect(pexpect.EOF)
        output = child.before.decode("utf-8")
        print(f"GAM Output Is: {output}")
        return output
    except pexpect.ExceptionPexpect as e:
        logging.error(f"GAM command failed: {str(e)}")
        return f"Error: {str(e)}"
def check_user_exists(email):
    command = f"{GAM_PATH} info user {email}"
    result = run_GAM_Command(command)
    if "Does not exist" in result:
        return {
            "email": email,
            "exists": False,
            "message": f"User {email} does not exist."
        }
    elif "User:" in result:
        return {
            "email": email,
            "exists": True,
            "message": f"User {email} exists."
        }
    else:
        return {
            "email": email,
            "exists": False,
            "message": f"Unexpected result for {email}: {result}"
        }
if __name__ == "__main__":
    emails = ['josh.walton@shpbeds.org', 'matt.grant@shpbeds.org', 'zander.krauch@shpbeds.org', 'xander.krauch@shpbeds.org']
    for email in emails:
        results = check_user_exists(email)
        print(json.dumps(results, indent=4))