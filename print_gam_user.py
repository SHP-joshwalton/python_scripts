#!/usr/bin/env python3
import os
import sys
import logging
import pexpect
from dotenv import load_dotenv
import re
import argparse
import json
import SHP_config
# Create the parser
parser = argparse.ArgumentParser(description="An example script.")

# Add arguments
parser.add_argument('email_arg', type=str, help='A positional argument')

# Parse the arguments
args = parser.parse_args()
# Access the environment variables
GAM_USER = os.getenv('GAM_USER')
GAM_PASSWORD = os.getenv('GAM_PASSWORD')
SERVER_ENVIRONMENT = os.getenv('SERVER_ENVIRONMENT', 'production')  # Default to production if not set
# Configure logging
def log_output(message, level='INFO'):
    print(message)
     
def run_GAM_Command(commandToRun):
    # the development server does not support GAM
    if SERVER_ENVIRONMENT == "development":
        log_output(f"Development environment: Skipping actual GAM command execution for: {commandToRun}")
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
            log_output(f"Pexpect: Unexpected EOF while expecting password prompt for {user}. Output: {child.before.decode('utf-8')}")
            return "ERROR: Unexpected EOF before password prompt."
        elif i == 3: # Timeout
            log_output(f"Pexpect: Timeout while expecting password prompt for {user}. Output: {child.before.decode('utf-8')}")
            return "ERROR: Timeout before password prompt."
        
        # Expect the shell prompt after successful su. This regex handles '$', '#', '>'
        prompt_regex = r'[$#>] *$' 
        
        i = child.expect([prompt_regex, pexpect.EOF, pexpect.TIMEOUT])
        if i == 0: # Prompt found, we're logged in
            log_output(f"Pexpect: Logged in as {user}. Sending GAM command: {commandToRun}")
            child.sendline(commandToRun)
            
            # Wait for the prompt again after the command finishes executing
            i = child.expect([prompt_regex, pexpect.EOF, pexpect.TIMEOUT])
            output = child.before.decode("utf-8").strip()
            #log_output(output)
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
                #log_output(f"GAM Output Is: {clean_output}")
                
            elif i == 1: # EOF after command (command finished or errored out)
                log_output(f"Pexpect: EOF after sending command for {user}. Output: {output}")
                clean_output = output
            elif i == 2: # Timeout after command (command might be hanging)
                log_output(f"Pexpect: Timeout after sending command for {user}. Output: {output}")
                clean_output = output
            
            child.sendline("exit") # Exit the su session cleanly
            child.expect(pexpect.EOF) # Wait for the session to truly end
            return clean_output
            
        elif i == 1: # EOF after su command, before sending GAM command
            log_output(f"Pexpect: Unexpected EOF after su command for {user}. Output: {child.before.decode('utf-8')}")
            return "ERROR: Unexpected EOF after su command."
        elif i == 2: # Timeout after su command
            log_output(f"Pexpect: Timeout after su command for {user}. Output: {child.before.decode('utf-8')}")
            return "ERROR: Timeout after su command."

    except pexpect.exceptions.ExceptionPexpect as e:
        log_output(f"Pexpect error during GAM command execution for {user}: {e}")
        return f"ERROR: Pexpect exception: {e}"
    except Exception as e:
        log_output(f"Unexpected error in run_GAM_Command for {user}: {e}")
        return f"ERROR: Unexpected exception: {e}"

def finalOutput(status, errors = None):
    output = {
        "results": status,
        "errors": errors
    }
    print(json.dumps(output, indent=5), end="")
    exit()

def extract(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""

def get_user_info():
    email = args.email_arg
    if email is None:
        finalOutput("Error", f"database does not have a user with that email, {email}")
    output = run_GAM_Command(f"gam info user {email}")
    print(f"=========\nGAM Output Is: {output}\n============\n")
    return {}
    # Parsing the relevant fields using regex
    return {
        'User': extract(r'User:\s(.+)', output),
        'First Name': extract(r'First Name:\s(.+)', output),
        'Last Name': extract(r'Last Name:\s(.+)', output),
        'Full Name': extract(r'Full Name:\s(.+)', output),
        'Languages': extract(r'Languages:\s(.+)', output),
        'Is Super Admin': extract(r'Is a Super Admin:\s(.+)', output),
        'Is Delegated Admin': extract(r'Is Delegated Admin:\s(.+)', output),
        '2-step enrolled': extract(r'2-step enrolled:\s(.+)', output),
        '2-step enforced': extract(r'2-step enforced:\s(.+)', output),
        'Has Agreed to Terms': extract(r'Has Agreed to Terms:\s(.+)', output),
        'IP Whitelisted': extract(r'IP Whitelisted:\s(.+)', output),
        'Account Suspended': extract(r'Account Suspended:\s(.+)', output),
        'Is Archived': extract(r'Is Archived:\s(.+)', output),
        'Must Change Password': extract(r'Must Change Password:\s(.+)', output),
        'Google Unique ID': extract(r'Google Unique ID:\s(.+)', output),
        'Customer ID': extract(r'Customer ID:\s(.+)', output),
        'Mailbox Setup': extract(r'Mailbox is setup:\s(.+)', output),
        'Included in GAL': extract(r'Included in GAL:\s(.+)', output),
        'Creation Time': extract(r'Creation Time:\s(.+)', output),
        'Last Login Time': extract(r'Last login time:\s(.+)', output),
        'Google Org Unit Path': extract(r'Google Org Unit Path:\s(.+)', output),
        'Gender': extract(r'Gender:\s+type:\s(.+)', output),
        'Organization Description': extract(r'description:\s(.+)', output),
        'Cost Center': extract(r'costCenter:\s(.+)', output),
        'Department': extract(r'department:\s(.+)', output),
        'Phone': extract(r'Phones:\s+type:\swork\s+value:\s(.+)', output)
    }
def main():
    parsed_data = get_user_info()
    print(json.dumps(parsed_data, indent=4), end="\n")
if __name__ == '__main__':
    main()
    

#CASantaBarbaraCoN