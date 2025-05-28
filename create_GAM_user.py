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
import SHP_config
# Create the parser
parser = argparse.ArgumentParser(description="An example script.")
parser.add_argument('user_id_arg', type=str, help='A positional argument')

# Parse the arguments
args = parser.parse_args()
# Configure logging
logging.basicConfig(
    filename='/var/www/scripts/create_user_results.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
# Access the environment variables
SERVER_ENVIRONMENT = os.getenv('SERVER_ENVIRONMENT')
GAM_USER = os.getenv('GAM_USER')
GAM_PASSWORD = os.getenv('GAM_PASSWORD')
shp_from_email = os.getenv('EMAIL_SENDER')
def getUserFromDatabase(user_id):

    conn = mysql.connector.connect(
        host='localhost',
        database=os.getenv('DATABASE_NAME'),
        user=os.getenv('DATABASE_USER_NAME'),
        password=os.getenv('DATABASE_USER_PASSWORD')
    )
    cursor = conn.cursor()
    # Step 3: Fetch a row and convert to dictionary
    cursor.execute(f"SELECT * FROM users WHERE id=\"{user_id}\"")
    row = cursor.fetchone()

    if row:
        # Get the column names
        column_names = [description[0] for description in cursor.description]
        
        # Create a dictionary from the row
        row_dict = dict(zip(column_names, row))
        return row_dict
    else:
        return None
def email_alread_exist(email):
    gam_command = f"gam info user {email}"
    output = run_GAM_Command(gam_command)

    # Check if output contains valid user details
    if "User:" in output and "Primary Email:" in output:
        return True
    return False
def createGAMUser(user:dict, run=True):
    
    result = ""
    error = ""
    first_name = user.get('first_name').strip()
    last_name = user.get('last_name').strip()
    shp_email = user.get("email").strip()
    personal_email = user.get('personal_email').strip()
    phone_number = user.get('phone').strip()
    recovery_phone_number = f"1{phone_number}"
    region = user.get('chapter_region')
    chapter = user.get('chapter')
    #check if user already exists
    if email_alread_exist(shp_email):
        finalOutput(status='error', errors=['User already exists'])
    createGAMUserCommand = f"gam create user \"{shp_email}\" firstname \"{first_name}\" lastname \"{last_name}\" notify \"{personal_email}\" subject \"Here is your new account\" from \"{shp_from_email}\" password random 10 changepasswordatnextlogin"

    updateGAMUserCommand = f"gam update user \"{shp_email}\" phone type mobile value \"{phone_number}\" primary recoveryphone \"{recovery_phone_number}\" otheremail home \"{personal_email}\" recoveryemail \"{personal_email}\" organization description \"User\" costcenter \"{region}\" department \"{chapter}\" title \"\" primary"
    if run is True:
        output = run_GAM_Command(createGAMUserCommand)
        result  = "success"
        error = ''
        if "Create Failed: Duplicate" in output:
            result = "error"
            error = "Duplicate"
        elif "ERROR:" in output:
            result = "error"
            error = "GAM Error"
        elif "Authentication failure" in output:
            result = "error"
            error = "GAM Authentication failure"
        else:
            output = run_GAM_Command(updateGAMUserCommand)
        finalOutput(status=result, errors=error)
        return None
        
    finalOutput(status=[createGAMUserCommand, updateGAMUserCommand])
    return None
def run_GAM_Command(commandToRun):
    # the development server does not support GAM
    if SERVER_ENVIRONMENT == "development":
        return "This is development"
    user = GAM_USER
    password = GAM_PASSWORD
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
    logging.debug(f"GAM Output Is: {output}")
    return output
def finalOutput(status, errors = None):
    output = {
        "results": status,
        "errors": errors
    }
    print(json.dumps(output), end="")
    exit()
def main():
    user = getUserFromDatabase(args.user_id_arg)
    if user is None:
        finalOutput("Error", f"database does not have a user with that id")
    createGAMUser(user=user, run=True)
    
if __name__ == '__main__':
    main()