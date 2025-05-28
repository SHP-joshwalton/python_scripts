#!/usr/bin/env python3
# This script shows how to use the client in anonymous mode
# against jira.atlassian.com.
from __future__ import annotations
import os
import SHP_config
import re

from jira import JIRA


import mysql.connector
from mysql.connector import Error
import argparse
import json
import logging

# Create the parser
parser = argparse.ArgumentParser(description="An example script.")

# Add arguments
parser.add_argument('ticket_arg', type=str, help='The Jinra ticket number to search for')
# Parse the arguments
args = parser.parse_args()
jira_email = os.getenv('JIRA_EMAIL')
jira_api_token = os.getenv('JIRA_API_TOKEN')

# Search returns first 50 results, `maxResults` must be set to exceed this
#issues_in_proj = jira.search_issues('project=IT and summary ~ "Create New SHP Email Address for"')
def main():
    jira_ticket = args.ticket_arg
    jira = JIRA(server='https://shpbeds.atlassian.net',basic_auth=(jira_email, jira_api_token))
    issue1 = jira.issue(id=jira_ticket)
    print("summary")
    print(issue1.fields.summary)
    print("description")
    print(issue1.fields.description)
    if len(issue1.fields.attachment) > 0:
        for attachment in issue1.fields.attachment:
            pass
            #print("Name: '{filename}', size: {size}".format(filename=attachment.filename, size=attachment.size))
            # to read content use `get` method:
            #print("Content: '{}'".format(attachment.get()))
if __name__ == "__main__":
    main()