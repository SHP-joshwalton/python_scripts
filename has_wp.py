#!/usr/bin/env python3#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from litmos import Litmos
import mysql.connector
from mysql.connector import Error
import sys
import argparse
import json
import requests

from requests.auth import HTTPBasicAuth
# Specify the path to the .env file
dotenv_path = os.path.join('/var/www/scripts', '.env')

# Load the .env file
load_dotenv(dotenv_path)

# Specify the path to the .env file
dotenv_path = os.path.join('/var/www/scripts', '.env')
# Load the .env file
load_dotenv(dotenv_path)

conn = mysql.connector.connect(
        host='localhost',
        database=os.getenv('DATABASE_NAME'),
        user=os.getenv('DATABASE_USER_NAME'),
        password=os.getenv('DATABASE_USER_PASSWORD')
    )
cursor = conn.cursor()
# Access the environment variables
wp_username = os.getenv('WORDPRESS_USER')
wp_password = os.getenv('WORDPRESS_PASSWORD')
API_KEY = os.getenv('LITMOS_API_KEY')
LITMOS_APP_NAME = 'shpuniversity.shpbeds.org'
LITMOS_SERVER_URL = 'https://api.litmos.com/v1.svc'  # https://support.litmos.com/hc/en-us/articles/227734667-Overview-Developer-API
#litmos = Litmos(API_KEY, LITMOS_APP_NAME, LITMOS_SERVER_URL)


# Example API query for WordPress users
def check_wordpress_user(email):
    wp_api_url = f"https://shpbeds.org/wp-json/wp/v2/users?search={email}"
    try:
        # Basic authentication
        response = requests.get(wp_api_url, auth=HTTPBasicAuth(wp_username, wp_password))
        response.raise_for_status()  # Raise an error if the response code is not 200
        users = response.json()

        # Log response for debugging
        print(f"API Response for {email}: {users}")

        if len(users) > 0:
            return True
        else:
            print(f"No WordPress user found for {email}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Error querying WordPress API for {email}: {e}")
        return False


def getUserFromDatabase():
    # Select users who don't have WordPress
    cursor.execute("SELECT email FROM users WHERE wordpress = FALSE")
    users_without_wp = cursor.fetchall()
    return users_without_wp

# Function to update 'wordpress' boolean in MySQL
def update_wordpress_status(email):
    cursor.execute("UPDATE users SET wordpress = TRUE WHERE email = %s", (email,))
    db.commit()

def main():
    print("Checking WordPress users ")
    needWordpress = getUserFromDatabase()
    for user in needWordpress:
        email = user[0]
        print(f"Checking {email} for WordPress user")
        if check_wordpress_user(email):
            print(f"Setting WordPress to true for user {email}")
            update_wordpress_status(email)
if __name__ == '__main__':
    main()