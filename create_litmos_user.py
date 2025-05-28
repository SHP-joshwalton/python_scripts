#!/usr/bin/env python3
import os
import requests
import SHP_config
from dotenv import load_dotenv
from litmos import Litmos
import mysql.connector
from mysql.connector import Error
import sys
import argparse
import json
import logging
import send_email
# Create the parser
parser = argparse.ArgumentParser(description="An example script.")
parser.add_argument('user_id_arg', type=str, help='A positional argument')

# Parse the arguments
args = parser.parse_args()

# Access the environment variables
SERVER_ENVIRONMENT = os.getenv('SERVER_ENVIRONMENT')
LITMOS_API_KEY = os.getenv('LITMOS_API_KEY')
LITMOS_APP_NAME = os.getenv('LITMOS_APP_NAME')
LITMOS_SERVER_URL = os.getenv('LITMOS_SERVER_URL')
litmos = Litmos(LITMOS_API_KEY, LITMOS_APP_NAME, LITMOS_SERVER_URL)

def getUserFromDatabase(user_id):

    conn = mysql.connector.connect(
        host='localhost',
        database=os.getenv('DATABASE_NAME'),
        user=os.getenv('DATABASE_USER_NAME'),
        password=os.getenv('DATABASE_USER_PASSWORD')
    )
    cursor = conn.cursor()
    # Step 3: Fetch a row and convert to dictionary
    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    row = cursor.fetchone()

    if row:
        # Get the column names
        column_names = [description[0] for description in cursor.description]
        
        # Create a dictionary from the row
        row_dict = dict(zip(column_names, row))
        return row_dict
    else:
        return None
def create_litmos_user(user):
    try:
        # Create user
        user_attributes = {
            'UserName': user['email'],
            'FirstName': user['first_name'],
            'LastName': user['last_name'],
            'Email': user['email'],
            'Chapter': user['chapter'],
            'Region': user['chapter_region'].replace('_', ' ').title()
        }

        litmos_user = litmos.User.create(user_attributes)
            
        # Confirm user by email
        confirmed_user = litmos.User.search(user['email'])
        if confirmed_user:
            finalOutput("success")

    except requests.exceptions.HTTPError as errh:
        error_message = f"HTTP Error: {errh.response.text if errh.response else str(errh)}"
        finalOutput('error', error_message)

    except requests.exceptions.ConnectionError as errc:
        finalOutput('error', f"Connection Error: {errc}")

    except requests.exceptions.Timeout as errt:
        finalOutput('error', f"Timeout Error: {errt}")

    except requests.exceptions.RequestException as err:
        finalOutput('error', f"Unexpected Request Error: {err}")

    except Exception as e:
        finalOutput('error', f"General Exception: {str(e)}")


def finalOutput(status, errors = None):
    output = {
        "result": status,
        "errors": errors
    }
    if errors != None:
        
        send_email.send_failure_alert(
            subject=f"Litmos failure",
            message=f"file: create_litmos_user.py\n{json.dumps(output, indent=2)}"
        )
    print(json.dumps(output), end="")
    exit()
def main():
    user = getUserFromDatabase(args.user_id_arg)
    if user is None:
        finalOutput("error", f"database does not have a user with that id")
    
    # Confirm user by email
    confirmed_user = litmos.User.search(user['email'])
    if confirmed_user:
        finalOutput('duplicate', "email exists")
    create_litmos_user(user)
    
if __name__ == '__main__':
    main()