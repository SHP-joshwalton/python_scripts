#!/usr/bin/env python3

import os
import re
import traceback
import requests
import imaplib
import smtplib
import email
import json
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import SHP_config
import get_specific_jira_ticket
from enum import Enum
import send_email

class EmailStatus(Enum):
    SUCCESS = 200
    SEARCH_FAILED = 500
    NO_UNREAD_EMAILS = 204
    FETCH_FAILED = 502
    CONNECTION_FAILED = 503


# Configurable constants
IMAP_SERVER = "imap.gmail.com"
EMAIL_SUBJECT_NEW_ACCOUNT = os.getenv('EMAIL_SUBJECT_NEW_ACCOUNT')
EMAIL_SUBJECT_PHOTO_SUBMISSION = os.getenv('EMAIL_SUBJECT_PHOTO_SUBMISSION')
ALERT_RECEIVER = os.getenv('ALERT_RECEIVER_EMAIL')  # Where to send alerts
SERVER_ENVIRONMENT = os.getenv('SERVER_ENVIRONMENT')

def extract_text_between(text, start, end):
    """Extracts text between two markers."""
    start_idx, end_idx = text.find(start) + len(start), text.find(end)
    return text[start_idx:end_idx] if start_idx >= len(start) and end_idx != -1 else ""


def get_email_body(msg):
    """Extract plain text or HTML body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                body = part.get_payload(decode=True)
                return body.decode(errors="ignore")
    else:
        # Not multipart - payload is the body
        body = msg.get_payload(decode=True)
        return body.decode(errors="ignore")
    return ""

def process_email(mail, email_id):
    """Fetch the email and extract the JIRA ticket from the subject."""
    status, msg_data = mail.fetch(email_id, "(RFC822)")

    if status != "OK":
        return None
    status_code = 200
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            email_subject = decode_header(msg["subject"])[0][0]
            email_subject = email_subject.decode() if isinstance(email_subject, bytes) else email_subject
            # Extract the email body
            email_body = get_email_body(msg)
            # Extract JIRA ticket from the subject
            jira_ticket = extract_text_between(email_subject, "[JIRA] (", ")")
                
            if EMAIL_SUBJECT_NEW_ACCOUNT in email_subject:
                text = extract_text_between(email_body, "\"I need to request a new SHP email account\" request. ", "Thank you,")
                info_list = text.split("\n")
                #print("extracting account Data from list")
                success = get_specific_jira_ticket.extract_user_account_info_from_list(info_list, jira_ticket)
                #print(f"success is:\n{success}", end="\n")
                ticket_type = "email_request"
            elif EMAIL_SUBJECT_PHOTO_SUBMISSION in email_subject:
                text = extract_text_between(email_body, "System Information:", "Thank you,")
                info_list = text.split("\n")
                #print("extracting photo request Data from list")
                success = get_specific_jira_ticket.extract_photo_request_info_jira(info_list, jira_ticket)
                #print(f"success is:\n{success}", end="\n")
                ticket_type = "photo_request"
            else:
                status_code = 400
            return {
                "ticket": jira_ticket,
                "success": success,
                "ticket_type": ticket_type,
                "status_code": status_code,
                "email_id": email_id
            }
    return None


def main():
    """Connect to the mailbox, fetch unread emails, and process them."""

    added = 0
    stack_trace = None
    tickets = {
        "email_request" : 0,
        "photo_request" : 0,
        "proceed_tickets" : [],
        "failed_tickets" : []
    }
    notAdded = 0
    error = None
    result = 'error'
    email_status = EmailStatus.FETCH_FAILED

    email_user, email_password = os.getenv('INBOX_EMAIL'), os.getenv('INBOX_EMAIL_PASSWORD')

    if not email_user or not email_password:
        error = "Missing email credentials."
        email_status = EmailStatus.CONNECTION_FAILED

    else:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(email_user, email_password)
            mail.select("inbox")
            status, messages = mail.search(
                None,
                f'(OR (UNSEEN SUBJECT "{EMAIL_SUBJECT_NEW_ACCOUNT}") (UNSEEN SUBJECT "{EMAIL_SUBJECT_PHOTO_SUBMISSION}"))'
            )


            if status != "OK" or messages is None:
                email_status = EmailStatus.CONNECTION_FAILED
                error = "Failed to search the mailbox."

            elif not messages[0]:
                email_status = EmailStatus.NO_UNREAD_EMAILS
                result = "success"

            else:
                for email_id in messages[0].split():
                    #print(f"Processing email ID: {email_id}")
                    results = process_email(mail, email_id)
                    #print(f"results are:\n{results}", end="\n")
                    if results is None:
                        notAdded += 1
                    else:
                        #print("processed email")
                        if results["status_code"] == 200:
                            #print("success")
                            added += 1
                            tickets[results["ticket_type"]] += 1
                            tickets["proceed_tickets"].append(results["ticket"])
                            mail.store(results["email_id"], '+FLAGS', '\\Seen')  # Mark as read
                            mail.expunge()
                        else:
                            #print("failed")
                            notAdded += 1

                email_status = EmailStatus.SUCCESS

            mail.logout()

        except Exception as e:
            error = str(e)
            #print(f"Error: {error}")
            #print(traceback.format_exc())
            email_status = EmailStatus.FETCH_FAILED

    finalResults = {
        "email_status": email_status.name,
        "added": added,
        "not_added": notAdded,
        "error": error,
        "tickets": tickets
    }

    if SERVER_ENVIRONMENT == 'development':
       finalResults["stack_trace"] = traceback.format_exc()

    print(json.dumps(finalResults))
    exit()
if __name__ == '__main__':
    main()
