pipeline {
    agent any

    environment {
        SIGMA_DIR   = 'rules/'
        SPLUNK_HOST = 'https://host.docker.internal:8089'
        CRED_ID     = 'splunk-api-token'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('1. Validate YAML & Convert (Runs on PR & Master)') {
            steps {
                script {
                    echo "Checking detection file syntax..."
                    sh '''
                        python3 -m venv venv
                        ./venv/bin/pip install --quiet --upgrade pip
                        ./venv/bin/pip install --quiet sigma-cli pysigma-backend-splunk
                        ./venv/bin/sigma check ${SIGMA_DIR}
                        mkdir -p output/
                        ./venv/bin/sigma convert -t splunk --without-pipeline ${SIGMA_DIR} > output/splunk_queries.spl
                    '''
                }
            }
        }

        stage('2. Deploy to Splunk (Runs on PR Post-Approval)') {
            when {
                allOf {
                    // Standard pipelines use GIT_BRANCH. We ensure we aren't on master.
                    expression { env.GIT_BRANCH != 'origin/master' && env.GIT_BRANCH != 'master' }
                    // Compare against master to see if rules/ changed
                    expression {
                        def changedFiles = sh(script: "git diff --name-only origin/master HEAD", returnStdout: true).trim()
                        return changedFiles.contains('rules/')
                    }
                }
            }
            steps {
                script {
                    echo "Checking PR Approval Status..."
                    withCredentials([
                        usernamePassword(credentialsId: "${CRED_ID}", usernameVariable: 'SPLUNK_USER', passwordVariable: 'SPLUNK_PASS'),
                        usernamePassword(credentialsId: 'github-credentials-id', usernameVariable: 'GH_USER', passwordVariable: 'GH_TOKEN') 
                    ]) {
                        sh '''
                            ./venv/bin/pip install --quiet requests pyyaml
                            ./venv/bin/python3 - << 'EOF'
import os, requests, glob, yaml
from requests.auth import HTTPBasicAuth

repo = "rkdhakad2023-jpg/detection-rules" 
gh_token = os.environ.get('GH_TOKEN')
headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}

# 1. FIND THE PR NUMBER USING THE BRANCH NAME
raw_branch = os.environ.get('GIT_BRANCH', 'unknown')
branch_name = raw_branch.replace('origin/', '').replace('refs/remotes/origin/', '')

print(f"Finding Pull Request for branch: {branch_name}...")
pulls_url = f"https://api.github.com/repos/{repo}/pulls?state=open&head=rkdhakad2023-jpg:{branch_name}"
pulls_response = requests.get(pulls_url, headers=headers)
pulls_data = pulls_response.json()

if not pulls_data or not isinstance(pulls_data, list):
    print("⏳ No open Pull Request found for this branch. Skipping Splunk deployment.")
    exit(0)

pr_id = pulls_data[0]['number']
print(f"Found PR #{pr_id}!")

# 2. CHECK GITHUB APPROVAL STATUS
reviews_url = f"https://api.github.com/repos/{repo}/pulls/{pr_id}/reviews"
response = requests.get(reviews_url, headers=headers)

if response.status_code == 200:
    reviews = response.json()
    approved = any(review.get('state') == 'APPROVED' for review in reviews)
else:
    print(f"Error checking PR status: {response.text}")
    exit(1)

if not approved:
    print("⏳ PR is not yet approved by a reviewer. Skipping Splunk deployment.")
    exit(0) 

print("✅ PR is Approved! Proceeding with Splunk Deployment...")

# 3. DEPLOY TO SPLUNK
splunk_url = os.environ.get('SPLUNK_HOST', 'https://host.docker.internal:8089') + '/services/saved/searches'
auth = HTTPBasicAuth(os.environ["SPLUNK_USER"], os.environ["SPLUNK_PASS"])

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
        print(f"Successfully deployed to Splunk: {title}")
    else:
        print(f"Failed to deploy {title} (Status {res.status_code}): {res.text}")
        exit(1)

# 4. POST SUCCESS COMMENT TO GITHUB PR
comment_url = f"https://api.github.com/repos/{repo}/issues/{pr_id}/comments"
comment_body = "✅ **Deployment Successful!** The test detection has been pushed to Splunk. You are cleared to merge this PR to master."
requests.post(comment_url, json={"body": comment_body}, headers=headers)
print("✅ Success comment posted back to GitHub Pull Request!")
EOF
                        '''
                  }
                }
            }
        }
    } 
}
