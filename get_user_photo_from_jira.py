#!/usr/bin/env python3
# This script shows how to use the client in anonymous mode
# against jira.atlassian.com.
from __future__ import annotations
from PIL import Image, ImageOps
import os
import io
from dotenv import load_dotenv

import mysql.connector
from mysql.connector import Error # type: ignore
from jira import JIRA

import argparse
import json
import logging

# Create the parser
parser = argparse.ArgumentParser(description="An example script.")

# Add arguments
parser.add_argument('ticket_arg', type=str, help='The Jira ticket number to search for')

# Parse the arguments
args = parser.parse_args()

# Parse the arguments
args = parser.parse_args()
# Specify the path to the .env file
dotenv_path = os.path.join('/var/www', '.env')
# Load the .env file
load_dotenv(dotenv_path)
JIRA_URL = os.getenv('JIRA_URL')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_PHOTOS_DIRECTORY = os.getenv('JIRA_PHOTOS_DIRECTORY')

def get_db_connection():
    """Establish and return a database connection."""
    try:
        return mysql.connector.connect(
            host='localhost',
            database=os.getenv('DATABASE_NAME'),
            user=os.getenv('DATABASE_USER_NAME'),
            password=os.getenv('DATABASE_USER_PASSWORD')
        )
    except Error as e:
        logging.error(f"Database connection error: {e}")
        return None

def save_as_jpeg(image_bytes, output_path):
    """
    Converts image bytes to JPEG and saves to output_path.

    Args:
        image_bytes (bytes): The raw image data (e.g., from attachment.get()).
        output_path (str): Full path to save the converted JPEG (should end with .jpg).

    Raises:
        ValueError: If the image format is not supported or not convertible.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = ImageOps.exif_transpose(img)  # Apply orientation from EXIF
            rgb_img = img.convert('RGB')  # JPEG doesn't support alpha
            rgb_img.save(output_path, format='JPEG')
            return True
    except Exception as e:
        #raise ValueError(f"Could not convert image to JPEG: {e}")
        return False

def getUserPhotoFromDatabase(jira_ticket):

    conn = get_db_connection()
    cursor = conn.cursor()
    # Step 3: Fetch a row and convert to dictionary
    cursor.execute("SELECT * FROM users_photos WHERE jira_ticket=%s", (jira_ticket,))
    row = cursor.fetchone()

    if row:
        # Get the column names
        column_names = [description[0] for description in cursor.description]
        
        # Create a dictionary from the row
        row_dict = dict(zip(column_names, row))
        return row_dict
    else:
        return None
import re

def update_file_name(photo_id, file_name):
    """
    Updates the file_name in the users_photos table for the given photo ID.

    Args:
        photo_id (int): The ID of the photo to update.
        file_name (str): The new sanitized file name to store.
        db_config (dict): A dictionary containing MySQL connection config keys:
                          host, user, password, database

    Returns:
        int: Number of rows updated (0 if not found).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "UPDATE users_photos SET file_name = %s WHERE id = %s"
        cursor.execute(query, (file_name, photo_id))
        conn.commit()

        return cursor.rowcount  # number of rows affected
    except mysql.connector.Error as err:
        finalOutput("error", [f"Error: {err}"])
        return 0
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def finalOutput(status, errors = None):
    output = {
        "results": status,
        "errors": errors
    }
    print(json.dumps(output))
    exit(0)
def main():
    jira_ticket = args.ticket_arg
    # Get the photo filename from the database
    photo_data = getUserPhotoFromDatabase(jira_ticket)
    if not photo_data:
        finalOutput("error", [f"Photo with ID '{jira_ticket}' not found in the database."])
    photo_id = photo_data['id']
    photo_filename = photo_data['file_name']

    jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))
    issue1 = jira.issue(id=jira_ticket)

    if len(issue1.fields.attachment) > 0:
        for attachment in issue1.fields.attachment:
            attachment_path = os.path.join(JIRA_PHOTOS_DIRECTORY, photo_filename)

            try:
                save_as_jpeg(attachment.get(), attachment_path)
                finalOutput("success", None)
            except ValueError as err:
                finalOutput("error", str(err))
    else:
        finalOutput("error", [f"Photo '{photo_filename}' not found in Jira ticket '{jira_ticket}'."])

if __name__ == "__main__":
    main()