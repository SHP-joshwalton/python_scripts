from jira import JIRA
import os
import json
import SHP_config
# Environment variables (or hardcode if you prefer for testing)
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

def show_ticket(ticket_id: str):
    jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))
    issue = jira.issue(ticket_id)

    # Convert to dict and pretty print
    issue_dict = issue.raw  # raw JSON returned from Jira
    print(json.dumps(issue_dict, indent=2))

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Show all Jira ticket details")
    parser.add_argument("ticket_id", type=str, help="The JIRA ticket ID, e.g., PROJ-123")
    args = parser.parse_args()

    show_ticket(args.ticket_id)
