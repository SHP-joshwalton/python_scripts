#!/usr/bin/env python3
import os
import sys
import pexpect # type: ignore
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import argparse
import json
import logging
import shlex # NEW: For quoting shell arguments
import re    # NEW: For robust prompt matching in pexpect
import SHP_config
# Create the parser
parser = argparse.ArgumentParser(description="An example script.")
parser.add_argument('user_id_arg', type=str, help='A positional argument')

# Parse the arguments
args = parser.parse_args()
# Configure logging
logging.basicConfig(
    filename='/var/www/logs/create_user_results.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
# Access the environment variables
SERVER_ENVIRONMENT = os.getenv('SERVER_ENVIRONMENT')
GAM_USER = os.getenv('GAM_USER')
GAM_PASSWORD = os.getenv('GAM_PASSWORD')
shp_from_email = os.getenv('EMAIL_SENDER')
    
    
def email_alread_exist(email):
    # add logic to check if the email already exists in GAM
    # but for now, just return False
    return False
def getUserFromDatabase(user_id):
    conn = None # Initialize conn to None
    try:
        conn = mysql.connector.connect(
            host='localhost',
            database=os.getenv('DATABASE_NAME'),
            user=os.getenv('DATABASE_USER_NAME'),
            password=os.getenv('DATABASE_USER_PASSWORD')
        )
        # Use dictionary=True to get rows as dictionaries, making access easier
        cursor = conn.cursor(dictionary=True)
        
        # Use a parameterized query to prevent SQL injection
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        return row # row is already a dictionary if dictionary=True was used
    except Error as e:
        logging.error(f"Database error in getUserFromDatabase for user_id {user_id}: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
      
def run_GAM_Command(commandToRun):
    # the development server does not support GAM
    if SERVER_ENVIRONMENT == "development":
        logging.info(f"Development environment: Skipping actual GAM command execution for: {commandToRun}")
        return "This is development - GAM command skipped."

    user = GAM_USER
    password = GAM_PASSWORD
    
    # Use 'su -l' for a login shell to ensure GAM's environment variables are loaded
    su_command = f"su -l {user}"
    
    try:
        child = pexpect.spawn(su_command, timeout=60) # Increased timeout
        
        # Expect password prompt, handling common variations
        i = child.expect(['Password:', r'\[sudo\] password for .*:', pexpect.EOF, pexpect.TIMEOUT])
        if i in [0, 1]: # Password prompt found
            child.sendline(password)
        elif i == 2: # EOF means no prompt, perhaps already logged in or error
            logging.error(f"Pexpect: Unexpected EOF while expecting password prompt for {user}. Output: {child.before.decode('utf-8')}")
            return "ERROR: Unexpected EOF before password prompt."
        elif i == 3: # Timeout
            logging.error(f"Pexpect: Timeout while expecting password prompt for {user}. Output: {child.before.decode('utf-8')}")
            return "ERROR: Timeout before password prompt."
        
        # Expect the shell prompt after successful su. This regex handles '$', '#', '>'
        prompt_regex = r'[$#>] *$' 
        
        i = child.expect([prompt_regex, pexpect.EOF, pexpect.TIMEOUT])
        if i == 0: # Prompt found, we're logged in
            logging.debug(f"Pexpect: Logged in as {user}. Sending GAM command: {commandToRun}")
            child.sendline(commandToRun)
            
            # Wait for the prompt again after the command finishes executing
            i = child.expect([prompt_regex, pexpect.EOF, pexpect.TIMEOUT])
            output = child.before.decode("utf-8").strip()
            
            if i == 0: # Prompt found, command executed
                # Remove the command itself and the final prompt from the output
                output_lines = output.splitlines()
                clean_output_lines = []
                command_found = False
                for line in output_lines:
                    if commandToRun in line and not command_found:
                        command_found = True
                        continue # Skip the line containing the command
                    if command_found and not re.match(prompt_regex, line.strip()):
                        clean_output_lines.append(line)
                
                clean_output = '\n'.join(clean_output_lines).strip()
                logging.debug(f"GAM Output Is: {clean_output}")
                
            elif i == 1: # EOF after command (command finished or errored out)
                logging.warning(f"Pexpect: EOF after sending command for {user}. Output: {output}")
                clean_output = output
            elif i == 2: # Timeout after command (command might be hanging)
                logging.error(f"Pexpect: Timeout after sending command for {user}. Output: {output}")
                clean_output = output
            
            child.sendline("exit") # Exit the su session cleanly
            child.expect(pexpect.EOF) # Wait for the session to truly end
            return clean_output
            
        elif i == 1: # EOF after su command, before sending GAM command
            logging.error(f"Pexpect: Unexpected EOF after su command for {user}. Output: {child.before.decode('utf-8')}")
            return "ERROR: Unexpected EOF after su command."
        elif i == 2: # Timeout after su command
            logging.error(f"Pexpect: Timeout after su command for {user}. Output: {child.before.decode('utf-8')}")
            return "ERROR: Timeout after su command."

    except pexpect.exceptions.ExceptionPexpect as e:
        logging.error(f"Pexpect error during GAM command execution for {user}: {e}")
        return f"ERROR: Pexpect exception: {e}"
    except Exception as e:
        logging.error(f"Unexpected error in run_GAM_Command for {user}: {e}")
        return f"ERROR: Unexpected exception: {e}"
      

def updateGAMUser(user: dict, run=True):
    first_name = user.get('first_name', '').strip()
    last_name = user.get('last_name', '').strip()
    shp_email = user.get("email", '').strip()
    personal_email = user.get('personal_email', '').strip()
    phone_number = user.get('phone', '').strip()
    recovery_phone_number = f"1{phone_number}" if phone_number else ''
    region = user.get('chapter_region', '').strip()
    chapter = user.get('chapter', '').strip()

    gam_commands = []

    if phone_number:
        gam_commands.append(
            f"gam update user {shlex.quote(shp_email)} phones type mobile value {shlex.quote(phone_number)} primary"
        )


    if recovery_phone_number:
        gam_commands.append(
            f"gam update user {shlex.quote(shp_email)} recoveryphone {shlex.quote(recovery_phone_number)}"
        )

    if personal_email:
        gam_commands.append(
            f"gam update user {shlex.quote(shp_email)} otheremail home {shlex.quote(personal_email)}"
        )
        gam_commands.append(
            f"gam update user {shlex.quote(shp_email)} recoveryemail {shlex.quote(personal_email)}"
        )
    if region or chapter:
        org_cmd = f"gam update user {shlex.quote(shp_email)} organization"
        if region:
            org_cmd += f" costcenter {shlex.quote(region)}"
        if chapter:
            org_cmd += f" department {shlex.quote(chapter)}"
        org_cmd += f" description {shlex.quote('User')}"
        gam_commands.append(org_cmd)

    final_errors = []
    final_status = "success"

    for cmd in gam_commands:
        print(f"Executing: {cmd}")
        if run:
            logging.info(f"Running: {cmd}")
            output = run_GAM_Command(cmd)
            logging.debug(f"Output: {output}")
            if "ERROR:" in output:
                final_status = "error"
                print(f"GAM Error: {output.split('ERROR:', 1)[1].strip()}")
                final_errors.append(f"GAM Error: {output.split('ERROR:', 1)[1].strip()}")
            elif "Authentication failure" in output:
                final_status = "error"
                final_errors.append("GAM Authentication failure during update.")

    finalOutput(status=final_status, errors=final_errors if final_errors else None)
    return None
def finalOutput(status, errors = None):
    # Ensure errors is a list for consistency
    if errors is not None and not isinstance(errors, list):
        errors = [errors]

    output = {
        "results": status,
        "errors": errors
    }
    print(json.dumps(output, indent=4), end="")
    sys.exit() # Use sys.exit() instead of bare exit() for clarity in scripts
def main():
    user = getUserFromDatabase(args.user_id_arg)
    if user is None:
        finalOutput("error", f"Database does not have a user with ID: {args.user_id_arg}")
    
    updateGAMUser(user=user, run=True)
    
if __name__ == '__main__':
    main()