#!/usr/bin/env python3
"""
Simple Jira CLI - Actually works
"""
import os
import sys
import json
from jira import JIRA

# Get credentials
url = os.getenv("JIRA_URL")
username = os.getenv("JIRA_USERNAME")
token = os.getenv("JIRA_API_TOKEN")

if not all([url, username, token]):
    print("Error: Missing JIRA_URL, JIRA_USERNAME, or JIRA_API_TOKEN")
    sys.exit(1)

# Connect
try:
    jira = JIRA(server=url, basic_auth=(username, token))
except Exception as e:
    print(f"Connection error: {e}")
    sys.exit(1)

# Parse command
if len(sys.argv) < 2:
    print("Usage: jira.py <command> [args]")
    print("Commands: search <jql> | assigned | open")
    sys.exit(1)

command = sys.argv[1]

def print_issues(issues):
    """Pretty print issues"""
    if not issues:
        print("No issues found")
        return
    
    print(f"\nFound {len(issues)} issues:\n")
    for issue in issues:
        # Get assignee name safely
        assignee = "Unassigned"
        if issue.fields.assignee:
            try:
                assignee = issue.fields.assignee.displayName
            except:
                try:
                    assignee = str(issue.fields.assignee)
                except:
                    assignee = "Unknown"
        
        print(f"  {issue.key}: {issue.fields.summary}")
        print(f"    Status: {issue.fields.status.name}")
        print(f"    Assignee: {assignee}")
        print()

try:
    if command == "search":
        jql = sys.argv[2] if len(sys.argv) > 2 else "project = PROJ"
        issues = jira.search_issues(jql, maxResults=50)
        print_issues(issues)
    
    elif command == "assigned":
        # Get all issues assigned to me that are not closed
        issues = jira.search_issues(
            "assignee = currentUser() AND status NOT IN (Done, Closed)",
            maxResults=50
        )
        print_issues(issues)
    
    elif command == "open":
        # Get all open issues
        issues = jira.search_issues(
            "status NOT IN (Done, Closed)",
            maxResults=50
        )
        print_issues(issues)
    
    elif command == "get":
        key = sys.argv[2]
        issue = jira.issue(key)
        print(f"\n{issue.key}: {issue.fields.summary}")
        print(f"Status: {issue.fields.status.name}")
        print(f"Type: {issue.fields.issuetype.name}")
        print(f"Assignee: {issue.fields.assignee.name if issue.fields.assignee else 'Unassigned'}")
        print(f"Description: {issue.fields.description or 'N/A'}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)