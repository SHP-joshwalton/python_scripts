#!/usr/bin/env python3

import os
import re
import traceback
import requests
import imaplib
import email
import json
import mysql.connector
from mysql.connector import Error
from email.header import decode_header
import SHP_config
import get_specific_jira_ticket
# Configurable constants
WP_JSON_URL = "https://shpbeds.org/wp-json/shp/v1/chapters"
IMAP_SERVER = "imap.gmail.com"
EMAIL_REQUEST_SUBJECT_FILTER = "I need to request a new SHP email account"
PHOTO_REQUEST_SUBJECT_FILTER = "Chapter Page Photo Submission"

# Regex patterns
PHONE_PATTERN = re.compile(r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,3}\b')
CHAPTER_PATTERN = re.compile(r'\b[A-Z]{2}-[A-Za-z\s]+\b')


def extract_text_between(text, start, end):
    """Extracts text between two markers."""
    start_idx, end_idx = text.find(start) + len(start), text.find(end)
    return text[start_idx:end_idx] if start_idx >= len(start) and end_idx != -1 else ""

def connect_to_mailbox():
    """Connects to an email inbox, fetches unread emails, and processes them."""
    email_user, email_password = os.getenv('INBOX_EMAIL'), os.getenv('INBOX_EMAIL_PASSWORD')
    added = 0
    not_added = 0
    success, ticket_type, status_code = None, None, None
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(email_user, email_password)
        mail.select("inbox")
        search_query = f'(UNSEEN OR (SUBJECT "{EMAIL_REQUEST_SUBJECT_FILTER}") (SUBJECT "{PHOTO_REQUEST_SUBJECT_FILTER}"))'
        status, messages = mail.search(None, search_query)


        if status != "OK":
            return
        for email_id in messages[0].split():
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            if status == "OK":
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        email_subject = decode_header(msg["subject"])[0][0]
                        jira_ticket = extract_text_between(email_subject.decode() if isinstance(email_subject, bytes) else email_subject, "[JIRA] (", ")")
                        
        mail.logout()
        
        print(json.dumps({
            "results": {
                "added": added,
                "not_added": not_added,
                "success": success,
                "ticket_type": ticket_type,
                "status_code": status_code
            },
            "added": added,
            "errors": None
        }))
    except Exception as e:
        print(json.dumps({
            "results": None,
            "errors": [str(e)],
            "stack_trace": traceback.format_exc()
        }))
def main():
    connect_to_mailbox()

if __name__ == '__main__':
    main()
