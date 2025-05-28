from __future__ import annotations
import os
import re
import json
import logging
import requests
import argparse
import mysql.connector
from mysql.connector import Error # type: ignore
from jira import JIRA
import SHP_config
import send_email
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# get all the jira information environment variables
JIRA_URL = os.getenv('JIRA_URL')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_PHOTOS_DIRECTORY = os.getenv('JIRA_PHOTOS_DIRECTORY')
# Regex patterns
PHONE_PATTERN = re.compile(r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b')
EMAIL_PATTERN = re.compile(r'[\w.-]+@[\w.-]+')
CHAPTER_PATTERN = re.compile(r'\b[A-Z]{2}-[A-Za-z\s]+\b')

wp_chapters = None

with open('/var/www/chapters.json', 'r') as f:
    wp_chapters = json.load(f)

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
def search_and_get_string_after(data_list, search_string):
    for item in data_list:
        if search_string in item:
            return item.split(search_string)[-1].replace("|", "").strip()
    return ""

def combine_selected_values_with_dashes(data, keys_to_include, delimiter="-"):
    """
        combines the selected values from the list of keys into a string separated by delimiter
        Args:
            data (dict): the dictionary of the keys and values that you want combined 
            keys_to_include (list): list of keys in order that you want the values in 
            delimiter (str, optional): an optional value for the separater
        Returns:
            str: the combined values separated by delimiter as a string
    """
    return delimiter.join(str(data[key]).strip().replace(" ", "-") for key in keys_to_include if key in data)

def execute_query(query, data):
    """Executes a query and commits changes to the database."""
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cursor:
            cursor.execute(query, data)
            conn.commit()
            return cursor.rowcount > 0
    return False

def sanitize_filename(name):
    """
    Removes or replaces characters that are invalid in file names.

    Args:
        name (str): The raw file name string.

    Returns:
        str: A sanitized, safe file name.
    """
    # Remove any character that is not a letter, number, dash, underscore, or dot
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', name)  # Remove reserved and control chars
    name = re.sub(r'[\s]+', '-', name)  # Replace spaces with underscores
    return name.strip('-')


# Function to format phone numbers to (123) 456-7890
def format_phone_number(phone):
	# Extract digits from the phone number
	digits = re.sub(r'\D', '', phone)

	formatted_phone = ""

	# Format the phone number
	if len(digits) == 10:
		formatted_phone = f'({digits[0:3]}) {digits[3:6]}-{digits[6:10]}'
	elif len(digits) == 11:
		formatted_phone = f'({digits[1:4]}) {digits[4:7]}-{digits[7:11]}'
	elif len(digits) == 7:
		formatted_phone = f'{digits[0:3]}-{digits[3:7]}'
	return formatted_phone

def find_chapter_by_title(chapters, title):
    """Find a chapter by title in the provided JSON list."""
    
    if not chapters:  # If chapters is None or empty
        return {"id": 0, "title": title, "region": ""}
    return next((obj for obj in chapters if obj.get('title') == title), {"id": 0, "title": title, "region": ""})


def get_email_from_list(info_list, isSHP):
    email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+')
    for item in info_list:
        if isSHP and "shpbeds.org" in item:
            match = email_pattern.search(item)
            if match:
                return match.group(0)
        elif not isSHP and "shpbeds.org" not in item:
            match = email_pattern.search(item)
            if match:
                return match.group(0)
    return ""
def extract_email(info_list, is_shp):
    """Extracts an email from a list based on whether it's an SHP email or not."""
    for item in info_list:
        match = EMAIL_PATTERN.search(item)
        if match and ((is_shp and "shpbeds.org" in item) or (not is_shp and "shpbeds.org" not in item)):
            return match.group(0)
    return ""
def extract_email_from_text(text):
    # Regular expression to match email addresses
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)

    if match:
        email = match.group()
        # Remove any trailing "mailto" part (if captured)
        email = email.split("mailto")[0]  
        return email
    else:
        return ""
def extract_first_email(text):
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else ""


def format_phone(phone):
    """Formats a phone number to (123) 456-7890."""
    digits = re.sub(r'\D', '', phone)
    return f"({digits[-10:-7]}) {digits[-7:-4]}-{digits[-4:]}" if len(digits) >= 10 else phone


def parse_info_list(info_list, search_key):
    """Extracts value from a key-value structured list."""
    for item in info_list:
        if search_key in item:
            return item.split(search_key)[-1].replace("|", "").strip()
    return ""

def handle_email_request(issue):
    """Processes an email request Jira ticket."""
    global wp_chapters
    info_list = issue.fields.description.split("\n")
    jira_ticket = issue.key
    return extract_user_account_info_from_list(info_list, jira_ticket)
    
def extract_user_account_info_from_list(info_list, jira_ticket):
    # Extracting the chapter name from the info_list
    chapter_name = (search_and_get_string_after(info_list, "Chapter:") or "").strip()
    chapter = find_chapter_by_title(wp_chapters, chapter_name)
    chapter_id = chapter.get("id")
    region = chapter.get("region")

    data = {
        "first_name": (search_and_get_string_after(info_list, "First Name:") or "").strip(),
        "last_name": (search_and_get_string_after(info_list, "Last Name:") or "").strip(),
        "requestor_name": (search_and_get_string_after(info_list, "Requester:") or "").strip(),
        "requestor_email": (search_and_get_string_after(info_list, "Requester Email:") or "").strip(),
        "personal_email": (search_and_get_string_after(info_list, "Personal Email:") or "").strip(),
        "email": (search_and_get_string_after(info_list, "SHP Email Formatted:") or "").strip(),
        "phone": format_phone_number((search_and_get_string_after(info_list, "Phone Number:") or "").strip()),
        "chapter_role": "chapter_staff",
        "chapter": chapter_name,
        "chapter_id": chapter_id,
        "chapter_region": region,
        "chapter_title": (search_and_get_string_after(info_list, "Team Member Role:") or "").strip(),
        "chapter_visibility": (search_and_get_string_after(info_list, "Name on your Chapter Page?:") or "").strip().lower() == "yes",
        "chapter_portal_account": (search_and_get_string_after(info_list, "Portal Access?:") or "").strip().lower() == "yes",
        "jira_ticket": jira_ticket,
        "state": "JIRA"
    }
    query = """
    INSERT INTO users (
        first_name, last_name, requestor_name, requestor_email, personal_email,
        email, phone, chapter, chapter_id, chapter_region, chapter_title,
        chapter_role, jira_ticket, state, chapter_visibility, chapter_portal_account
    ) VALUES (
        %(first_name)s, %(last_name)s, %(requestor_name)s, %(requestor_email)s,
        %(personal_email)s, %(email)s, %(phone)s, %(chapter)s, %(chapter_id)s,
        %(chapter_region)s, %(chapter_title)s, %(chapter_role)s, %(jira_ticket)s,
        %(state)s, %(chapter_visibility)s, %(chapter_portal_account)s
    )
    """


    return execute_query(query, data)
def save_user_photo_to_database(data):
    query = """
    INSERT INTO users_photos (first_name, last_name, email, requester_email, phone, chapter, file_name, jira_ticket, state, source) 
    VALUES (%(first_name)s, %(last_name)s, %(email)s, %(requester_email)s, %(phone)s, %(chapter)s, %(file_name)s, %(jira_ticket)s, %(state)s, %(source)s)"""
    return execute_query(query, data)
def handle_photo_request_jira(issue):
    info_list = issue.fields.description.split("\n")
    jira_ticket = issue.key
    return extract_photo_request_info_jira(info_list, jira_ticket)
def extract_photo_request_info_jira(info_list, jira_ticket):
    first_name = parse_info_list(info_list, "First Name:").strip()
    last_name = parse_info_list(info_list, "Last Name:").strip()
    chapter = parse_info_list(info_list, "Chapter:").strip()
    file_name = sanitize_filename(f"{chapter}-{first_name}-{last_name}.jpg")
    data = {
        "first_name": first_name,
        "last_name": last_name,
        "email" :  parse_info_list(info_list, "Email:").strip(),
        "requester_email": parse_info_list(info_list, "Submitter:").strip(),
        "phone": '',
        "chapter": chapter,
        "file_name": file_name,
        "jira_ticket": jira_ticket,
        "state" : "JIRA",
        "source" : "JIRA"
    }
    return save_user_photo_to_database(data)
def process_jira_ticket(ticket_id):
    """Fetches and processes a Jira ticket."""
    status_code = 200
    try:
        jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))
        issue = jira.issue(ticket_id)
        
        if "I need to request a new SHP email account" in issue.fields.summary:
            success = handle_email_request(issue)
            ticket_type = "email_request"
        elif "Chapter Page Photo Submission" in issue.fields.summary:
            success = handle_photo_request_jira(issue)
            ticket_type = "photo_request"
        else:
            status_code = 400
            success, ticket_type = False, None
    except Exception as e:
        print(f"Error processing ticket {ticket_id}: {e}", end="\n")
        status_code = e.status_code if hasattr(e, 'status_code') else 500
        success, ticket_type = False, None
    
    return success, ticket_type, status_code


def main():
    parser = argparse.ArgumentParser(description="JIRA Ticket Processor")
    parser.add_argument('ticket_id', type=str, help='The JIRA ticket ID')
    args = parser.parse_args()
    success, ticket_type, status = process_jira_ticket(args.ticket_id)
    print(json.dumps({"added": success, "ticket_type": ticket_type, "status": status}), end="\n")

#run the script main function if this is the main script
if __name__ == '__main__':
    main()