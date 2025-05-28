#!/usr/bin/env python3
import SHP_config
import os
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


wp_chapters_json = None
INBOX_EMAIL = os.getenv('INBOX_EMAIL')
INBOX_EMAIL_PASSWORD = os.getenv('INBOX_EMAIL_PASSWORD')

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
	startFrom = "Your form SHP Chapter Page Photo Submission has a new entry. Here are all the answers."
	finishHere = "Name the photo this:"
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
def get_email_from_list(line):
	# Improved regex with word boundaries to avoid capturing unwanted text
    email_pattern = re.compile(r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b')
    match = email_pattern.search(line)
    if match:
        email = match.group(0)
        # Strip out 'mailto' or any trailing parts, just in case
        return email.replace('mailto', '').strip()
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
	first_name = search_and_get_string_after(info_list, "|First Name of person in photo|")
	last_name = search_and_get_string_after(info_list, "Last Name of person in photo|")
	shp_email = get_email_from_list(search_and_get_string_after(info_list, "||Email of Team Member Photo Submitted |"))
	requester_shp_email = get_email_from_list(search_and_get_string_after(info_list, "||Email address|["))
	chapter_name = search_and_get_string_after(info_list, "Chapter|")
	phone = search_and_get_string_after(info_list, "|Phone|")
	return {
		"first_name": first_name,
		"last_name": last_name,
		"email" : shp_email,
		"requester_email": requester_shp_email,
		"phone": phone,
		"chapter": chapter_name,
		"jira_ticket": jiraTicket,
		"state" : "JIRA",
  		"source" : "Google"
	}
def save_to_database(data):
	try:
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
				INSERT INTO users_photos 
				(first_name, last_name, email, requester_email, phone, chapter, jira_ticket, state)
				VALUES (%(first_name)s, %(last_name)s, %(email)s, %(requester_email)s, %(phone)s, %(chapter)s, %(jira_ticket)s, %(state)s)
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
	mail.login(INBOX_EMAIL, INBOX_EMAIL_PASSWORD)
	
	# Select the inbox
	mail.select("inbox")
	
	# Search for all unread emails with subject containing "SHP Chapter Page Photo Submission"
	status, messages = mail.search(None, '(UNSEEN SUBJECT "Chapter Page Photo Submission")')



	
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
				subjects.append(email_subject)
				if isinstance(email_subject, bytes):
					email_subject = email_subject.decode()
				jiraTicket = partOfTextNeeded(email_subject, "[JIRA] (", ")")
				if "SHP" not in email_subject:
					pass
				# Extract the plain text email body
				elif msg.is_multipart():
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

if __name__ == "__main__":
	connectToMailbox()