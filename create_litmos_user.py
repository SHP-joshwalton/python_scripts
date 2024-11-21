#!/usr/bin/env python3#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from litmos import Litmos
import mysql.connector
from mysql.connector import Error
import sys
import argparse
import json
import logging
# Create the parser
parser = argparse.ArgumentParser(description="An example script.")
parser.add_argument('user_id_arg', type=str, help='A positional argument')

# Parse the arguments
args = parser.parse_args()
# Specify the path to the .env file
dotenv_path = os.path.join('/var/www/scripts', '.env')

# Load the .env file
load_dotenv(dotenv_path)

# Specify the path to the .env file
dotenv_path = os.path.join('/var/www/scripts', '.env')
# Load the .env file
load_dotenv(dotenv_path)
# Access the environment variables
API_KEY = os.getenv('LITMOS_API_KEY')
LITMOS_APP_NAME = 'shpuniversity.shpbeds.org'
LITMOS_SERVER_URL = 'https://api.litmos.com/v1.svc'  # https://support.litmos.com/hc/en-us/articles/227734667-Overview-Developer-API
litmos = Litmos(API_KEY, LITMOS_APP_NAME, LITMOS_SERVER_URL)

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
def create_litmos_user(user):
    # create user
    LitmosUser = litmos.User.create({
            'UserName': user['email'],
            'FirstName': user['first_name'],
            'LastName': user['last_name'],
            'Email': user['email'],
            'Chapter': user['chapter'],
            'Region': user['chapter_region'].replace('_', ' ').title()
        })
    
    # Confirm user by email
    confirmed_user = litmos.User.search(user['email'])
    if confirmed_user:
        finalOutput('success')
    else:
        finalOutput('error', "User creation failed or not found.")



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
    
    # Confirm user by email
    confirmed_user = litmos.User.search(user['email'])
    if confirmed_user:
        finalOutput('duplicate', "email exists")
    create_litmos_user(user)
    
if __name__ == '__main__':
    main()