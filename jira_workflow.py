
import SHP_config
import os
from jira import JIRA

jira_email = os.getenv('JIRA_EMAIL')
jira_api_token = os.getenv('JIRA_API_TOKEN')

def get_all_workflows():
    """
    Fetches all workflows available in JIRA (Requires JIRA Admin permissions).

    :return: JSON containing all workflows and their transitions
    """
    
    jira = JIRA(server='https://shpbeds.atlassian.net',basic_auth=(jira_email, jira_api_token))
    workflows = jira.workflows()
    
    all_workflows = []
    for workflow in workflows:
        all_workflows.append({"name": workflow, "transitions": workflows[workflow]})

    return json.dumps({"workflows": all_workflows}, indent=4)

# Example usage
result = get_all_workflows()
print(result)
