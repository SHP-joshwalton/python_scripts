#!/usr/bin/env python3
import get_tickets_from_email

# Specify the path to the .env file
dotenv_path = os.path.join('/var/www/scripts', '.env')

# Create the parser
parser = argparse.ArgumentParser(description="An example script.")
parser.add_argument('subject_arg', type=str, help='A positional argument')
# Parse the arguments
args = parser.parse_args()
# Load the .env file
load_dotenv(dotenv_path)
email_user = os.getenv('AUTOMATION_INBOX_EMAIL')
email_password = os.getenv('AUTOMATION_INBOX_EMAIL_PASSWORD')
def processNewEmailRequest(msg):
    # Extract the plain text email body
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                body = msg.get_payload(decode=True).decode()
                saved = processBody(bodyOfEmail=body, jiraTicket=jiraTicket)
    else:
        content_type = msg.get_content_type()
        if content_type == "text/plain":
            body = msg.get_payload(decode=True).decode()
            saved = processBody(bodyOfEmail=body, jiraTicket=jiraTicket)
def markEmailUnread(subject):
    # Connect to the server and log in
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(email_user, email_password)

    # Select the inbox
    mail.select("inbox")

    # Search for all emails containing the Jira ticket in the subject
    search_query = f'(SUBJECT "{subject}")'
    status, messages = mail.search(None, search_query)

    if status == "OK":
        for num in messages[0].split():
            # Fetch the email
            _, data = mail.fetch(num, '(RFC822)')
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Process the email (custom logic here)
            print(f"Processing email with subject: {email_message['subject']}")
            
            
            
            
            
            # Mark the email as unread
            mail.store(num, '-FLAGS', '\\Seen')
    
    # Close the mailbox and logout
    mail.close()
    mail.logout()

def main():
    subject_contains = args.subject_arg
    markEmailUnread(subject=subject_contains)
if __name__ == '__main__':
    main()