#!/usr/bin/env python3
import os
import sys
import time
# Removed: import pexpect  # Replaced by Google API client
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
# Removed: import shlex     # Not needed for API calls
import re
import argparse
import json
import logging
import secrets
import string
# Added Google API Imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError # For handling API errors

# NOTE: Assuming SHP_config and meta_data are still valid
import SHP_config
from meta_data import MetaDataUpdater


# Argument parser
parser = argparse.ArgumentParser(description="Create and update a Google Workspace user using Admin SDK.")
parser.add_argument('user_id_arg', type=str, help='User ID')
parser.add_argument('--dry-run', action='store_true', help='Only print API payloads without running them')
args = parser.parse_args()

# Environment variables (Updated for API usage)
SERVER_ENVIRONMENT = os.getenv('SERVER_ENVIRONMENT')
# Removed: GAM_USER and GAM_PASSWORD
SHP_FROM_EMAIL = os.getenv('EMAIL_SENDER')

# New API Environment Variables
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE_PATH') # Path to the .json key
ADMIN_EMAIL_FOR_DWD = os.getenv('ADMIN_EMAIL_FOR_DWD') # Admin email to impersonate
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']

# Global Directory Service (Initialize on first call)
DIRECTORY_SERVICE = None

# Metadata accessor
metData = MetaDataUpdater()

# Logging
if SERVER_ENVIRONMENT != "development":
    logging.basicConfig(
        filename='/var/www/scripts/create_user_results.log',
        filemode='a',
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.DEBUG
    )


# --- Directory API Functions ---
def generate_strong_password(length=12):
    """Generates a strong password compliant with typical domain requirements."""
    if length < 8:
        length = 8
    
    # Ensure at least one of each type is present
    alphabet = string.ascii_letters + string.digits + string.punctuation
    
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice(string.punctuation)
    ]
    
    # Fill the rest of the password length
    for _ in range(length - 4):
        password.append(secrets.choice(alphabet))
        
    # Shuffle the list to prevent predictable patterns
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)
def get_directory_service():
    """Initializes and returns the Google Admin Directory API service object."""
    global DIRECTORY_SERVICE
    if DIRECTORY_SERVICE:
        return DIRECTORY_SERVICE

    if not SERVICE_ACCOUNT_FILE or not ADMIN_EMAIL_FOR_DWD:
        raise EnvironmentError(
            "Missing environment variables: GOOGLE_APPLICATION_CREDENTIALS or ADMIN_EMAIL_FOR_DWD"
        )
    
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            f"Service account key file not found at: {SERVICE_ACCOUNT_FILE}"
        )

    # 1. Load credentials for Domain-Wide Delegation
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
        subject=ADMIN_EMAIL_FOR_DWD  # Impersonate the admin user
    )
    
    # 2. Build the service object
    DIRECTORY_SERVICE = build('admin', 'directory_v1', credentials=credentials)
    return DIRECTORY_SERVICE


def email_alread_exist(email):
    """Checks if a Google Workspace user exists using the Directory API."""
    try:
        service = get_directory_service()
        # Use users.get to check for existence. If user is found, no exception is raised.
        service.users().get(userKey=email).execute()
        return True
    except HttpError as e:
        # Status code 404 (Not Found) is expected if the user does not exist.
        if e.resp.status == 404:
            return False
        # Re-raise or handle other API errors (403 Permission Denied, etc.)
        logging.error(f"Directory API error checking user {email}: {e}")
        # Treat other HttpErrors as a failure that should stop the script
        finalOutput('error', [f"API lookup failed: {e.resp.status}"])
    except Exception as e:
        # Handle non-HTTP errors like network failure, auth failure before API call
        logging.error(f"General error during user lookup for {email}: {e}")
        finalOutput('error', [f"General lookup failure: {e}"])


# --- Database and Utility Functions (Unchanged) ---

def getUserFromDatabase(user_id):
    # ... (Database connection logic remains the same)
    conn = mysql.connector.connect(
        host='localhost',
        database=os.getenv('DATABASE_NAME'),
        user=os.getenv('DATABASE_USER_NAME'),
        password=os.getenv('DATABASE_USER_PASSWORD')
    )
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id=\"{user_id}\"")
    row = cursor.fetchone()
    if row:
        column_names = [desc[0] for desc in cursor.description]
        return dict(zip(column_names, row))
    return None

def safe_dict(d):
    return {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for k, v in d.items()}

# Removed: shell_escape_if_needed
# Removed: build_create_user_command
# Removed: build_update_user_commands


# --- Main Logic Function (Rewritten) ---

def createGAMUser(user: dict, run: bool):
    """Creates a user and updates properties using the Directory API."""
    shp_email = user.get("email", '').strip()
    
    if email_alread_exist(shp_email):
        finalOutput('error', ['User already exists'])

    first_name = user.get('first_name', '').strip()
    last_name = user.get('last_name', '').strip()
    phone = user.get('phone', '').strip()
    personal_email = user.get('personal_email', '').strip()
    region = user.get('chapter_region', '').strip()
    chapter = user.get('chapter', '').strip()
    NCR_Trainee = bool(user.get('NCR_Training', 0))
    initial_password = metData.get_meta_data_for_key('NCR_Training_password')

    # 1. User Creation Payload (Body for users.insert)
    create_body = {
        'primaryEmail': shp_email,
        'name': {
            'givenName': first_name,
            'familyName': last_name
        },
        'changePasswordAtNextLogin': True,
        'agreedToTerms': True,
        'suspended': False
    }
    
    
    # --- FINAL PASSWORD LOGIC ---
    if NCR_Trainee and initial_password and initial_password.strip():
        # Case 1: Trainee. Use the password from metadata. (Ensure this password is STRONG!)
        create_body['password'] = initial_password
    else:
        # Case 2: Non-Trainee. The API requires a strong password, so we must generate one.
        initial_password = generate_strong_password()
        create_body['password'] = initial_password
        logging.warning(f"Generated temporary password for {shp_email} to satisfy API requirement.")
        
        # NOTE: If you need to log or save this temporary password for the user,
        # you MUST do it here using the `temp_password` variable.
        
    # --- END PASSWORD LOGIC ---
    # 2. User Update Payload (Body for users.patch)
    update_body = {
        # Phones (Format as E.164, e.g., +14085551212)
        'phones': [],
        # Other Emails (type: home)
        'emails': [],
        # Recovery Info (GAM uses this for recovery, API uses dedicated fields)
        'recoveryEmail': personal_email if personal_email else None,
        'recoveryPhone': f"+1{phone}" if phone else None, 
        
        # Organization Info (Mapping GAM fields to API fields)
        'organizations': [
            {
                'name': 'User',
                'description': 'User',
                'title': '',  # To ensure 'clear title' logic is maintained
                'primary': True
            }
        ]
    }
    # Populate nested fields if data exists
    if phone:
        # Note: GAM just set the field, API requires array of dicts
        update_body['phones'].append({'type': 'mobile', 'value': phone, 'primary': True})
    if personal_email:
        update_body['emails'].append({'address': personal_email, 'type': 'home', 'primary': False})
    if region:
        update_body['organizations'][0]['costCenter'] = region
    if chapter:
        update_body['organizations'][0]['department'] = chapter


    # --- Dry Run / Development Output ---
    if args.dry_run or SERVER_ENVIRONMENT == "development":
        # Output the JSON payloads instead of GAM commands
        print(json.dumps({
            "API_CREATE_USER_PAYLOAD": create_body,
            "API_UPDATE_USER_PAYLOAD": update_body,
            "user": safe_dict(user)
        }, indent=4))
        exit(0)
    
    
    # --- Live Execution ---
    result = "success"
    errors = []
    service = get_directory_service()

    # A. CREATE User
    try:
        logging.info(f"Attempting to create user {shp_email}")
        service.users().insert(body=create_body).execute()
        logging.info(f"User {shp_email} created successfully.")
        
        # -------------------------------------------------------------------
        # CRITICAL FIX: Add delay to allow user creation to propagate ⏳
        # -------------------------------------------------------------------
        import time 
        time.sleep(10) # Wait 10 seconds
        # -------------------------------------------------------------------

    except HttpError as e:
        result = "error"
        if e.resp.status == 409: # HTTP 409 Conflict (User already exists, although checked before, this is a race condition check)
            errors.append("Create Failed: Duplicate user detected by API.")
        elif e.resp.status == 403: # HTTP 403 Forbidden
            errors.append("API Authentication failure/Permission Denied.")
        else:
            errors.append(f"User creation failed: HTTP {e.resp.status} - {e.content.decode()}")
        
        logging.error(f"User creation failed for {shp_email}: {e.content.decode()}")
        finalOutput(result, errors, {"create_user": create_body, "update":update_body}) # Stop execution on creation failure
        

    # B. UPDATE User (Only runs if creation was successful)
    try:
        logging.info(f"Attempting to update user {shp_email}")
        # The .patch() method updates only the fields provided in the body
        service.users().patch(userKey=shp_email, body=update_body).execute()
        logging.info(f"User {shp_email} updated successfully.")
    except HttpError as e:
        result = "error"
        errors.append(f"User update failed: HTTP {e.resp.status} - {e.content.decode()}")
        logging.error(f"User update failed for {shp_email}: {e.content.decode()}")
    
    # NOTE: The GAM `notify` logic is now handled by the user creation (if password is set) 
    # or should be handled by an updated `finalOutput` caller that sends the welcome email 
    # (using the SHP_FROM_EMAIL) separately, as the Directory API does not handle email 
    # notifications for creation unless explicitly setting a password.

    finalOutput(status=result, password=initial_password, errors=errors, data={"create_user": create_body, "update":update_body})


# Removed: run_GAM_Command (Replaced by get_directory_service and service calls)

def finalOutput(status, password="", errors=None, data=None):
    print(json.dumps({"results": status, "password":password, "errors": errors, "data":data}, indent=5), end="")
    exit()

def main():
    user = getUserFromDatabase(args.user_id_arg)
    if user is None:
        finalOutput("error", "User not found in database")
    createGAMUser(user=user, run=not args.dry_run)

if __name__ == '__main__':
    # load_dotenv() # Assuming this is called at the start of the environment setup
    main()