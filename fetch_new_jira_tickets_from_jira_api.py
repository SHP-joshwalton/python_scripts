#!/usr/bin/env python3

import os
import re
import traceback
import requests
from meta_data import MetaDataUpdater
import json
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import SHP_config
from jira import JIRA
import get_specific_jira_ticket
from enum import Enum
import send_email

JIRA_URL = os.getenv('JIRA_URL')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')

class EmailStatus(Enum):
    SUCCESS = 200
    SEARCH_FAILED = 500
    NO_UNREAD_EMAILS = 204
    FETCH_FAILED = 502
    CONNECTION_FAILED = 503


# Configurable constants
IMAP_SERVER = "imap.gmail.com"
NEW_ACCOUNT_TICKET_SUMMARY = "I need to request a new SHP email account"
PHOTO_SUBMISSION_TICKET_SUMMARY = "Chapter Page Photo Submission"
ALERT_RECEIVER = os.getenv('ALERT_RECEIVER_EMAIL')  # Where to send alerts
SERVER_ENVIRONMENT = os.getenv('SERVER_ENVIRONMENT')

def extract_text_between(text, start, end):
    """Extracts text between two markers."""
    start_idx, end_idx = text.find(start) + len(start), text.find(end)
    return text[start_idx:end_idx] if start_idx >= len(start) and end_idx != -1 else ""


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
    
    try:
        updater = MetaDataUpdater()
        last_ticket_pulled = updater.get_meta_data_for_key("last_jira_ticket_pulled")
        # updater.upsert_meta_data("last_jira_ticket_pulled", "IT-6153")
        # updater.close_connection()

        jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))
                
        # Define summary conditions
        summary_conditions = [
            f'summary ~ "{NEW_ACCOUNT_TICKET_SUMMARY}"',
            f'summary ~ "{PHOTO_SUBMISSION_TICKET_SUMMARY}"'
        ]
        ticket_query = ""
        if last_ticket_pulled:
            ticket_query = f"AND issuekey > {last_ticket_pulled}"
        summary_filter = " OR ".join(summary_conditions)

        # JQL query to get issues created after the given date with specific summaries created > '{created_date}' AND 
        jql_query = f"({summary_filter}) {ticket_query} ORDER BY created DESC"

        # Fetch matching issues
        issues = jira.search_issues(jql_query, maxResults=50)  # Adjust maxResults as needed

        if not issues:
            email_status = EmailStatus.NO_UNREAD_EMAILS
            result = "no_unread_emails"
        else:
            # Print results
            for issue in issues:
                #print(f"ticket:{issue.key} \nsummary:\n {issue.fields.summary}\n")
                if NEW_ACCOUNT_TICKET_SUMMARY in issue.fields.summary:
                    success = get_specific_jira_ticket.handle_email_request(issue)
                    if success:
                        added += 1
                        tickets["email_request"] += 1
                        tickets["proceed_tickets"].append(issue.key)
                    else:
                        notAdded += 1
                        tickets["failed_tickets"].append(issue.key)
                # elif EMAIL_SUBJECT_PHOTO_SUBMISSION in issue.fields.summary:
                #     success = get_specific_jira_ticket.handle_photo_request_jira(issue)
                #     if success:
                #         added += 1
                #         tickets["photo_request"] += 1
                #         tickets["proceed_tickets"].append(issue.key)
                #     else:
                #         notAdded += 1
                #         tickets["failed_tickets"].append(issue.key)
            updater.upsert_meta_data("last_jira_ticket_pulled", issues[0].key)
    except Exception as e:
        status_code = e.status_code
        success, ticket_type = False, None

    results = {
        "result": result,
        "added": added,
        "not_added": notAdded,
        "error": error,
        "tickets": tickets,
        "jql_query": jql_query
    }

    if SERVER_ENVIRONMENT == 'development':
        results["stack_trace"] = traceback.format_exc()
    if result != "success":
        send_email.send_failure_alert(
            subject=f"SHP Email Processor Failure: {email_status.name}",
            message=f"file: fetch_new_jira_tickets_from_mail.py\n{json.dumps(results, indent=2)}"
        )

    print(json.dumps(results))
    exit()
if __name__ == '__main__':
    main()
