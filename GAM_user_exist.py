import pexpect
import os
import logging
import json
import SHP_config
SERVER_ENVIRONMENT = os.getenv('SERVER_ENVIRONMENT')
GAM_USER = os.getenv('GAM_USER')
GAM_PASSWORD = os.getenv('GAM_PASSWORD')


def run_GAM_Command(command):
    if SERVER_ENVIRONMENT == "development":
        return "development can’t be used with GAM."

    logging.debug(f"Running command: {command}")
    try:
        # Use a login shell (-l) and run the command (-c)
        gam_command = f'su -l -c "{command}" {GAM_USER}'
        print(f"Running command: {gam_command}")
        child = pexpect.spawn(gam_command, timeout=60)
        child.expect("Password:")
        child.sendline(GAM_PASSWORD)
        child.expect(pexpect.EOF)
        output = child.before.decode("utf-8", errors="ignore").strip()
        logging.debug(f"Output: {output}")
        print(f"Output: {output}")
        return output
    except pexpect.TIMEOUT:
        logging.error(f"GAM command timed out: {command}")
        return "Timeout"
    except Exception as e:
        logging.error(f"Error running GAM command: {e}")
        return f"Error: {e}"


def check_user_exists(email):
    command = f'gam info user {email}'
    result = run_GAM_Command(command)
    if "Does not exist" in result:
        return {"email": email, "exists": False, "message": f"User {email} does not exist."}
    elif "User:" in result:
        return {"email": email, "exists": True, "message": f"User {email} exists."}
    else:
        return {"email": email, "exists": False, "message": f"Unexpected result for {email}: {result}"}


if __name__ == "__main__":
    emails = ['josh.walton@shpbeds.org', 'matt.grant@shpbeds.org', 'zander.krauch@shpbeds.org', 'xander.krauch@shpbeds.org']
    for email in emails:
        results = check_user_exists(email)
        print(json.dumps(results, indent=4))
