#!/usr/bin/env python3
# This script shows how to use the client in anonymous mode
# against jira.atlassian.com.
from __future__ import annotations
import time
import SHP_config
import os
import re
from jira import JIRA, JIRAError
import argparse
import json
import send_email


def get_issue_status(jira,issue_key):
    """
    Fetches the current status of a JIRA issue.
    
    :param issue_key: The JIRA issue key (e.g., 'PROJECT-123')
    :return: JSON containing the issue key and current status
    """
    try:
        issue = jira.issue(issue_key)
        status = issue.fields.status.name  # Get issue status

        return {
            "issue_key": issue_key,
            "current_status": status,
            "status": "success"
        }
    
    except JIRAError as e:
        return {
            "issue_key": issue_key,
            "status": "failed",
            "error": str(e)
        }
    
    except Exception as e:
        return {
            "issue_key": issue_key,
            "status": "failed",
            "error": f"Unexpected error: {str(e)}"
        }

def can_transition(jira, issue_key, target_status):
    """
    Checks if a JIRA issue can transition to the given target status.

    :param issue_key: The JIRA issue key (e.g., 'PROJECT-123')
    :param target_status: The name of the target transition (e.g., 'Close Issue')
    :return: JSON response with transition possibility and transition ID if available
    """
    try:
        transitions = jira.transitions(issue_key)

        for transition in transitions:
            # Ensure both transition ID and target_status are strings before comparison
            if str(transition["id"]) == str(target_status):
                return True  # Return immediately if a match is found

        return False  # No matching transition found

    except JIRAError as e:
        
        #print(f"JIRA API Error: {e.text}")
        return False  # Default to False if an error occurs

    except Exception as e:
        #print(f"Unexpected error: {str(e)}")
        return False
def transition_issue_with_retry(jira, issue_key, transition_id, max_retries=3, delay=5):
    """
    Attempts to transition a JIRA issue with retry logic and returns a JSON response.
    
    :param issue_key: The JIRA issue key (e.g., 'PROJECT-123')
    :param transition_id: The ID of the transition to apply
    :param max_retries: Maximum number of retry attempts
    :param delay: Delay in seconds between retries
    :return: JSON-formatted response containing success status and details
    """
    if can_transition(jira, issue_key, transition_id) == False:
        return {
                "issue_key": issue_key,
                "transition_id": transition_id,
                "status": "failed",
                "error": "can't transition to the state"
            }
    for attempt in range(1, max_retries + 1):
        try:
            jira.transition_issue(issue_key, transition=transition_id)
            
            # Verify transition was successful
            issue = jira.issue(issue_key)
            status = issue.fields.status.name
            
            response = {
                "issue_key": issue_key,
                "transition_id": transition_id,
                "status": "success",
                "message": f"Issue successfully transitioned to '{status}'",
                "current_status": status
            }
            return response

        except JIRAError as e:
            error_response = {
                "issue_key": issue_key,
                "transition_id": transition_id,
                "status": "failed",
                "attempt": attempt,
                "error": e.text
            }

            if attempt < max_retries:
                time.sleep(delay)
            else:
                return error_response
            
def main():
    JIRA_URL = os.getenv('JIRA_URL')
    JIRA_EMAIL = os.getenv('JIRA_EMAIL')
    JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
    JIRA_CLOSE_ID = "941"
    JIRA_RESOLVE_ID = "761"
    # Create the parser
    parser = argparse.ArgumentParser(description="An example script.")

    # Add arguments
    parser.add_argument('ticket_arg', type=str, help='The method argument')
    # Parse the arguments
    args = parser.parse_args()
    jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))
    jira_ticket = args.ticket_arg
    if can_transition(jira, jira_ticket, JIRA_RESOLVE_ID) is True:
        resolve_issue = transition_issue_with_retry(jira, jira_ticket, JIRA_RESOLVE_ID)
        if resolve_issue['status'] == 'success':
            close_issue = transition_issue_with_retry(jira, jira_ticket, JIRA_CLOSE_ID)
            print(json.dumps(close_issue))
            quit()
        else:
            print(json.dumps(resolve_issue))
    elif can_transition(jira, jira_ticket, JIRA_CLOSE_ID) is True:
        close_issue = transition_issue_with_retry(jira, jira_ticket, JIRA_CLOSE_ID)
        print(json.dumps(close_issue))
        quit()
    else:
        issue_status = get_issue_status(jira, jira_ticket)['current_status']
        results = {
            "issue_key": jira_ticket,
            "status": "failed",
            "error": f"This ticket is is in the {issue_status}, unable to transition to closed"
        }
        print(json.dumps(results))
    
if __name__ == '__main__':
    main()