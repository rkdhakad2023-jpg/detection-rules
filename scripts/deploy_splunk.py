import os
import glob
import json
import yaml
import requests
from requests.auth import HTTPBasicAuth

# Suppress insecure HTTPS warnings for internal Splunk certs
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- ENVIRONMENT CONFIGURATION ---
pr_id = os.environ.get('CHANGE_ID')
repo = os.environ.get('REPO_NAME', 'rkdhakad2023-jpg/detection-rules')
gh_token = os.environ.get('GH_TOKEN')
splunk_host = os.environ.get('SPLUNK_HOST', 'https://host.docker.internal:8089')
splunk_user = os.environ.get('SPLUNK_USER')
splunk_pass = os.environ.get('SPLUNK_PASS')

headers = {
    "Authorization": f"token {gh_token}",
    "Accept": "application/vnd.github.v3+json"
}

def check_github_pr_approval():
    print(f"Checking approval status for PR #{pr_id} in {repo}...")
    reviews_url = f"https://api.github.com/repos/{repo}/pulls/{pr_id}/reviews"
    response = requests.get(reviews_url, headers=headers)

    if response.status_code == 200:
        reviews = response.json()
        approved = any(review.get('state') == 'APPROVED' for review in reviews)
        return approved
    else:
        print(f"❌ Error checking PR status: {response.text}")
        exit(1)

def deploy_rules_to_splunk():
    print("🚀 Deploying detection rules to Splunk...")
    splunk_url = f"{splunk_host}/services/saved/searches"
    auth = HTTPBasicAuth(splunk_user, splunk_pass)

    for rule_file in glob.glob('rules/*.yml'):
        with open(rule_file, 'r') as rf:
            rule_data = yaml.safe_load(rf)
            
        title = rule_data.get('title', 'Detection Rule')
        description = rule_data.get('description', '')
        
        payload = {
            'name': f"Detection - {title}",
            'search': 'index=main sourcetype=windows', 
            'description': description,
            'is_scheduled': '1',
            'cron_schedule': '0 * * * *'
        }
        
        res = requests.post(splunk_url, data=payload, auth=auth, verify=False)
        
        if res.status_code in [200, 201, 409]:
            print(f"✅ Successfully deployed to Splunk: {title}")
        else:
            print(f"❌ Failed to deploy {title} (Status {res.status_code}): {res.text}")
            exit(1)

def post_github_comment():
    comment_url = f"https://api.github.com/repos/{repo}/issues/{pr_id}/comments"
    comment_body = (
        "✅ **Deployment Successful!** The test detection has been pushed to Splunk. "
        "You are cleared to merge this PR to master."
    )
    res = requests.post(comment_url, json={"body": comment_body}, headers=headers)
    if res.status_code in [200, 201]:
        print("✅ Success comment posted back to GitHub Pull Request!")
    else:
        print(f"⚠️ Failed to post GitHub comment: {res.text}")

def main():
    if not check_github_pr_approval():
        print("⏳ PR is not yet approved by a reviewer. Skipping Splunk deployment.")
        exit(0)

    print("✅ PR is Approved! Proceeding with Splunk Deployment...")
    deploy_rules_to_splunk()
    post_github_comment()

if __name__ == "__main__":
    main()
