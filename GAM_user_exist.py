import subprocess
import json
import sys
import SHP_config
import os
import logging
import pexpect # type: ignore

SERVER_ENVIRONMENT = os.getenv('SERVER_ENVIRONMENT')
GAM_USER = os.getenv('GAM_USER')
GAM_PASSWORD = os.getenv('GAM_PASSWORD')

def run_GAM_Command(command):
    if SERVER_ENVIRONMENT == "development":
        return 'development can’t be used with GAM.'

    child = pexpect.spawn(f"su {GAM_USER}", timeout=30)
    child.expect("Password:")
    child.sendline(GAM_PASSWORD)
    child.expect("$")
    child.sendline(command)
    child.expect("$")
    child.sendline("exit")
    child.expect(pexpect.EOF)
    output = child.before.decode("utf-8")
    return output
def check_user_exists(email):
    command = f"gam info user {email}"
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