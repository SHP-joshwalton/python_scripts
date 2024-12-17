#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import re
import requests
import imaplib
import email
from email.header import decode_header
import mysql.connector
from mysql.connector import Error
import json
# Regex patterns for phone numbers and email addresses
phone_pattern = re.compile(r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b')
email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,3}\b')

# Regex pattern to match "StateAbbreviation-LocationName"
chapter_pattern = re.compile(r'\b[A-Z]{2}-[A-Za-z\s]+\b')

# Specify the path to the .env file
dotenv_path = os.path.join('/var/www/scripts', '.env')

wp_chapters_json = None
# Load the .env file
load_dotenv(dotenv_path)
email_user = os.getenv('AUTOMATION_INBOX_EMAIL')
email_password = os.getenv('AUTOMATION_INBOX_EMAIL_PASSWORD')

wp_chapters_json = read_json_from_file("/var/www/html/chapters.json")#fetch_json_from_url("https://shpbeds2.wpengine.com/wp-json/shp/v1/chapters")

def create_connection():

    try:

        connection = mysql.connector.connect(
            host='localhost',
            database=os.getenv('DATABASE_NAME'),
            user=os.getenv('DATABASE_USER_NAME'),
            password=os.getenv('DATABASE_USER_PASSWORD')
        )

        if connection.is_connected():
            return connection

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None

def close_connection(connection):
    if connection.is_connected():
        connection.close()

def read_json_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            json_data = json.load(file)
        return json_data
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file {file_path} is not a valid JSON file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return None
def fetch_json_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        json_data = response.json()  # Parse the JSON data
        return json_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from {url}: {e}")
        return []


def partOfTheEmailNeeded(text):
	#the following Strings are for the start and end of the part of the email that we want 
	startFrom = "Your form has a new entry. Here are all the answers."
	finishHere = "*The fields below make it easy to copy and paste to Google Admin and Dashboard*"
	return partOfTextNeeded(text, startFrom, finishHere)
def partOfTextNeeded(text, start, end):
	try:
		start_index = text.find(start) + len(start)
		end_index = text.find(end, start_index)
		if start_index - len(start) == -1 or end_index == -1:
			return ""
		return text[start_index:end_index]
	except ValueError:
		return ""
def find_chapter_by_title(json_array, title):
    for obj in json_array:
        if obj.get('title') == title:
            return obj
    return {
            "id" : 0,
            "title" : title,
            "region" : ""}

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
    return None
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

def search_and_get_string_after(data_list, search_string):
    for item in data_list:
        if search_string in item:
            return item.split(search_string)[-1].replace("|", "").strip()
    return ""



def processBody(bodyOfEmail, jiraTicket=""):
	content = partOfTheEmailNeeded(bodyOfEmail)
	if content == "":
		return False
	
	items = content.replace("\r", "").split("\n")
	cleanList = [text.strip() for text in items if text.strip()]
	dictionary = get_dictionary_representation(cleanList, jiraTicket)
	return save_to_database(dictionary)
def get_dictionary_representation(info_list, jiraTicket):
	requestor_first_name = search_and_get_string_after(info_list, "Requestor First Name|").strip()
	requestor_last_name = search_and_get_string_after(info_list, "Requestor Last Name|").strip()
	requestor_name = requestor_first_name + " " + requestor_last_name
	requestor_email = get_email_from_list(info_list, isSHP=True).strip()
	first_name = search_and_get_string_after(info_list, "Account First Name|").strip()
	first_name = search_and_get_string_after(info_list, "Account First Name|").strip()
	last_name = search_and_get_string_after(info_list, "Account Last Name|").strip()
	shp_email = f"{first_name}.{last_name}@shpbeds.org"
	chapter_name = search_and_get_string_after(info_list, "SHP Chapter|").strip()
	chapter = find_chapter_by_title(wp_chapters_json, chapter_name)
	chapter_id = chapter.get("id")
	region = chapter.get("region")
	return {
		"first_name": first_name,
		"last_name": last_name,
		"requestor_name": requestor_name,
		"requestor_email": requestor_email,
		"personal_email": get_email_from_list(info_list, isSHP=False).strip(),
		"email": shp_email,
		"phone": format_phone_number(search_and_get_string_after(info_list, "Account Cell Phone Number|")).strip(),
		"chapter_role": "chapter_staff",
		"chapter": chapter_name,
  		"chapter_id" : chapter_id,
		"chapter_region" : region,
		"chapter_title": search_and_get_string_after(info_list, "Chapter Core Team Role|").strip(),
		"chapter_visibility": search_and_get_string_after(info_list, "Do you want this person's name on your chapter web page?").strip() == "Yes",
		"chapter_portal_account": search_and_get_string_after(info_list, "Do you need a Chapter Portal account?").strip() == "Yes",
		"jira_ticket": jiraTicket,
		"state" : "JIRA"
	}
def save_to_database(data):
	try:
		# Specify the path to the .env file
		dotenv_path = os.path.join('/var/www/scripts', '.env')
		# Load the .env file
		load_dotenv(dotenv_path)
		# Access the environment variables

		conn = mysql.connector.connect(
			host='localhost',
			database=os.getenv('DATABASE_NAME'),
			user=os.getenv('DATABASE_USER_NAME'),
			password=os.getenv('DATABASE_USER_PASSWORD')
		)
		if conn.is_connected():
			# Open a cursor to perform database operations
			cursor = conn.cursor()

			# Prepare the SQL INSERT statement
			insert_query = """
				INSERT INTO users 
				(first_name, last_name, requestor_name, requestor_email, personal_email, email, phone, chapter_role, chapter, chapter_id, chapter_region, chapter_title, chapter_visibility, chapter_portal_account, jira_ticket, state)
				VALUES (%(first_name)s, %(last_name)s, %(requestor_name)s, %(requestor_email)s, %(personal_email)s, %(email)s, %(phone)s, %(chapter_role)s, %(chapter)s, %(chapter_id)s, %(chapter_region)s, %(chapter_title)s, %(chapter_visibility)s, %(chapter_portal_account)s, %(jira_ticket)s, %(state)s)
			"""

			# Execute the INSERT statement
			cursor.execute(insert_query, data)

			# Commit the transaction
			conn.commit()
			added = cursor.rowcount
			# Close the cursor and connection
			cursor.close()
			conn.close()
			return added > 0
	except Error as e:
		print(f"An error occurred: {e}")
		return False
def connectToMailbox():
	# Connect to the server and log in
	mail = imaplib.IMAP4_SSL('imap.gmail.com')
	mail.login(email_user, email_password)
	
	# Select the inbox
	mail.select("inbox")
	
	# Search for all unread emails with subject containing "Create New Email"
	status, messages = mail.search(None, '(UNSEEN SUBJECT "Create New SHP Email Address")')


	
	# Convert the result to a list of email IDs
	email_ids = messages[0].split()
	subjects = []
	added = 0
	notAdded = 0
	# Loop through each email ID
	for email_id in email_ids:
		# Fetch the email by ID
		status, msg_data = mail.fetch(email_id, "(RFC822)")
		#status, msg_data = mail.fetch(email_id, "(BODY.PEEK[])")
		# Extract the email message
		for response_part in msg_data:
			if isinstance(response_part, tuple):
				msg = email.message_from_bytes(response_part[1])
				email_subject = decode_header(msg["subject"])[0][0]
				if isinstance(email_subject, bytes):
					email_subject = email_subject.decode()
				jiraTicket = partOfTextNeeded(email_subject, "[JIRA] (", ")")
				subjects.append(email_subject)
				# Extract the plain text email body
				if msg.is_multipart():
					for part in msg.walk():
						content_type = part.get_content_type()
						if content_type == "text/plain":
							body = msg.get_payload(decode=True).decode()
							saved = processBody(bodyOfEmail=body, jiraTicket=jiraTicket)
							if saved == True:
								added = added + 1
							else:
								notAdded = notAdded + 1
				else:
					content_type = msg.get_content_type()
					if content_type == "text/plain":
						body = msg.get_payload(decode=True).decode()
						saved = processBody(bodyOfEmail=body, jiraTicket=jiraTicket)
						if saved == True:
								added = added + 1
						else:
							notAdded = notAdded + 1
	# Log out
	mail.logout()
	stats = {
		"added" : added,
		"notadded" : notAdded
	}
	print(json.dumps(stats), end="")

if __name__ == '__main__':
	connectToMailbox()