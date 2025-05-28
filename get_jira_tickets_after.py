
from __future__ import annotations
import SHP_config
import os
import re
from jira import JIRA
import argparse
import json
import logging
import requests
import send_email
from datetime import datetime
# Jira credentials
JIRA_URL = os.getenv('JIRA_URL')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')

parser = argparse.ArgumentParser(description="An example script.")

# Add arguments
parser.add_argument('ticket_arg', type=str, help='The method argument')
# Parse the arguments
args = parser.parse_args()
# Connect to Jira
jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))

# Specify the issue key
issue_key = args.ticket_arg

# Fetch issue details
issue = jira.issue(issue_key)
# Convert created date to valid JQL format (YYYY-MM-DD HH:mm)
created_date_raw = issue.fields.created  # Example: '2025-03-08T03:44:09.069+0000'
created_date = datetime.strptime(created_date_raw[:16], "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M")

print(f"Created date of {issue_key}: {created_date}")

# Define summary conditions
summary_conditions = [
    'summary ~ "Create New SHP Email Address for"',
    'summary ~ "Chapter Page Photo Submission"',
    'summary ~ "SHP Chapter Page Photo Submission"'
]
summary_filter = " OR ".join(summary_conditions)

# JQL query to get issues created after the given date with specific summaries
jql_query = f"created > '{created_date}' AND ({summary_filter}) ORDER BY created ASC"

# Fetch matching issues
issues = jira.search_issues(jql_query, maxResults=50)  # Adjust maxResults as needed

# Print results
for issue in issues:
    print(f"ticket:{issue.key} \nsummary:\n {issue.fields.summary}\ncreated\n{issue.fields.created}\ndescription:\n{issue.fields.description}")
