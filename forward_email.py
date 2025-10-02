#!/usr/bin/env python3
import SHP_config
# Removed: from GAM_user_exist import check_user_exists
import os
import logging
# Removed: import pexpect
import re
import argparse
import json
# Added Google API Imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import sys


SERVER_ENVIRONMENT = os.getenv('SERVER_ENVIRONMENT')

# New API Environment Variables
SERVICE_ACCOUNT_FILE = os.getenv('GMAIL_SERVICE_ACCOUNT_FILE_PATH')
ADMIN_EMAIL_FOR_DWD = os.getenv('ADMIN_EMAIL_FOR_DWD')
# Scopes for Directory API (User Lookup) and Gmail API (Forwarding)
DIRECTORY_SCOPES = ['https://www.googleapis.com/auth/admin.directory.user.readonly']
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.settings.sharing',
    "https://www.googleapis.com/auth/gmail.settings.basic"
]

# Global Service Objects
DIRECTORY_SERVICE = None
GMAIL_SERVICE = None


def setup_logging():
    logging.basicConfig(
        filename='/var/www/logs/forward_email.log',
        filemode='a',
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.DEBUG
    )


def get_directory_service():
    """Initializes and returns the Google Admin Directory API service object."""
    global DIRECTORY_SERVICE
    if DIRECTORY_SERVICE:
        return DIRECTORY_SERVICE

    if not SERVICE_ACCOUNT_FILE or not ADMIN_EMAIL_FOR_DWD:
        raise EnvironmentError("Missing environment variables for DWD setup.")
    
    # 1. Load credentials for Directory API
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=DIRECTORY_SCOPES,
        subject=ADMIN_EMAIL_FOR_DWD
    )
    
    # 2. Build the service object
    DIRECTORY_SERVICE = build('admin', 'directory_v1', credentials=credentials)
    return DIRECTORY_SERVICE


def get_gmail_service(user_email=ADMIN_EMAIL_FOR_DWD):
    """Initializes and returns the Gmail API service object impersonating the target user."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=GMAIL_SCOPES
    )
    delegated_creds = creds.with_subject(user_email)  # impersonate target user
    return build('gmail', 'v1', credentials=delegated_creds)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Manage forwarding email addresses.")
    parser.add_argument('method', choices=['SHOW', 'ADD', 'DELETE'], help='Method: SHOW, ADD, DELETE')
    parser.add_argument('email', help='Target email address (must be full email)')
    parser.add_argument('forward_email', nargs='?', default=None, help='Forwarding email (optional)')
    return parser.parse_args()


def check_user_exists_api(email):
    """Checks if a Google Workspace user exists using the Directory API."""
    try:
        service = get_directory_service()
        service.users().get(userKey=email).execute()
        return {"exists": True}
    except HttpError as e:
        if e.resp.status == 404:
            return {"exists": False}
        logging.error(f"Directory API error checking user {email}: {e}")
        final_output('error', [f"API lookup failed: {e.resp.status}"])
    except Exception as e:
        logging.error(f"General error during user lookup for {email}: {e}")
        final_output('error', [f"General lookup failure: {e}"])


def final_output(status, errors=None, forwarding_addresses=None):
    output = {"results": status, "errors": errors}
    if forwarding_addresses is not None:
        output["forwarding_addresses"] = forwarding_addresses
    print(json.dumps(output))
    exit(0)


# Removed: extract_emails, is_shpbeds_email, is_real_email, run_GAM_Command


def show_forwarding_addresses(user_email, return_list=False):
    if SERVER_ENVIRONMENT == "development":
        addresses = [
            {'email': 'josh.walton@shpbeds.org', 'status': 'accepted'},
            {'email': 'zander.krauch@shpbeds.org', 'status': 'accepted'}
        ]
        if return_list: return addresses
        final_output('success', forwarding_addresses=addresses)
    
    if not check_user_exists_api(user_email)["exists"]:
        final_output("error", [f"The email {user_email} does not exist in Google Workspace"])

    try:
        service = get_gmail_service(user_email)
        # The Gmail API uses the full email or 'me' as the user ID
        response = service.users().settings().forwardingAddresses().list(userId=user_email).execute()
        
        addresses = [
            {'email': item['forwardingEmail'], 'status': item.get('verificationStatus', 'unknown')}
            for item in response.get('forwardingAddresses', [])
        ]
        
    except HttpError as e:
        logging.error(f"Gmail API error fetching forwarding addresses for {user_email}: {e}")
        final_output("error", [f"Failed to show forwarding addresses: {e.resp.status}"])
        
    if return_list:
        return addresses
        
    final_output('success', forwarding_addresses=addresses)


def add_forwarding_address(user_email, forwarding_email):
    if SERVER_ENVIRONMENT == "development":
        final_output("success")

    errors = []
    if not check_user_exists_api(user_email)["exists"]:
        errors.append(f"The email {user_email} does not exist in Google Workspace")
    if not check_user_exists_api(forwarding_email)["exists"]:
        errors.append(f"The forwarding email {forwarding_email} does not exist in Google Workspace")
    
    existing_addresses = show_forwarding_addresses(user_email, return_list=True)
    if any(a['email'] == forwarding_email for a in existing_addresses):
        errors.append(f"The forwarding address {forwarding_email} already exists.")
    
    if errors:
        final_output("error", errors)

    try:
        service = get_gmail_service(user_email)
        
        # 1. Add the forwarding address (Admin DWD bypasses confirmation)
        add_body = {"forwardingEmail": forwarding_email}
        service.users().settings().forwardingAddresses().create(
            userId=user_email,
            body=add_body
        ).execute()
        logging.info(f"Forwarding address {forwarding_email} added to {user_email}.")

        # 2. Create a filter to forward ALL mail to the new address (replicates GAM's filter command)
        filter_body = {
            "action": {
                "forward": forwarding_email
            },
            "criteria": {}
        }
        service.users().settings().filters().create(
            userId=user_email,
            body=filter_body
        ).execute()
        logging.info(f"Forwarding filter created for {user_email} to {forwarding_email}.")
        
        final_output("success")

    except HttpError as e:
        logging.error(f"Gmail API error adding forwarding for {user_email}: {e}")
        final_output("error", [f"Failed to add forwarding address: {e.resp.status} - {e.content.decode()}"])
    except Exception as e:
        final_output("error", [f"General error: {e}"])
def delete_forwarding_address(user_email, forwarding_email):
    try:
        service = get_gmail_service(user_email)  # impersonate target user

        # 1. Delete the forwarding address
        service.users().settings().forwardingAddresses().delete(
            userId='me',
            forwardingId=forwarding_email
        ).execute()
        logging.info(f"Forwarding address {forwarding_email} deleted from {user_email}.")

        # 2. Delete the associated filter(s)
        filters_response = service.users().settings().filters().list(userId=user_email).execute()
        deleted_count = 0
        for f in filters_response.get('filter', []):
            if f.get('action', {}).get('forward') == forwarding_email:
                service.users().settings().filters().delete(
                    userId='me',
                    id=f['id']
                ).execute()
                logging.info(f"Forwarding filter {f['id']} deleted.")
                deleted_count += 1

        if deleted_count > 0:
            final_output("success")
        else:
            final_output("error", [
                f"Forwarding address deleted, but no matching forwarding filter was found for {forwarding_email}."
            ])

    except HttpError as e:
        if e.resp.status == 404:
            final_output("error", [f"Forwarding address {forwarding_email} not found or already deleted."])
        else:
            content = e.content.decode() if isinstance(e.content, bytes) else str(e.content)
            logging.error(f"Gmail API error deleting forwarding for {user_email}: {content}")
            final_output("error", [f"Failed to delete forwarding address: {e.resp.status} - {content}"])
    except Exception as e:
        logging.error(f"Unexpected error deleting forwarding for {user_email}: {e}")
        final_output("error", [f"General error: {e}"])

def main():
    setup_logging()
    args = parse_arguments()
    
    # NOTE: Assuming args.email is the FULL email address (e.g., user@domain.com)
    # The Gmail API requires the full email address.
    
    actions = {
        "SHOW": lambda: show_forwarding_addresses(args.email),
        "ADD": lambda: add_forwarding_address(args.email, args.forward_email),
        "DELETE": lambda: delete_forwarding_address(args.email, args.forward_email)
    }

    action = actions.get(args.method)
    if action:
        action()
    else:
        final_output("Error", [f"Invalid method: {args.method}. Expected: SHOW, ADD, DELETE"])


if __name__ == '__main__':
    main()