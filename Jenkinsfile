pipeline {
    agent { label 'Test-DE' }

    environment {
        SIGMA_DIR   = 'rules/'
        SPLUNK_HOST = 'https://host.docker.internal:8089'
        CRED_ID     = 'splunk-api-token'
    }

    stages {
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
                    // This native variable only exists if Jenkins is running a Pull Request
                    expression { env.CHANGE_ID != null }
                    // Compare against the target branch (usually master) to see if rules changed
                    expression {
                        def changedFiles = sh(script: "git diff --name-only origin/${env.CHANGE_TARGET} HEAD", returnStdout: true).trim()
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

pr_id = os.environ.get('CHANGE_ID')
repo = "rkdhakad2023-jpg/detection-rules" 
gh_token = os.environ.get('GH_TOKEN')
headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}

print(f"Checking approval status for PR #{pr_id} in {repo}...")

# 1. CHECK GITHUB APPROVAL STATUS
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

# 2. DEPLOY TO SPLUNK
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

# 3. POST SUCCESS COMMENT TO GITHUB PR
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
