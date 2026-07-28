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

        stage('2. Deploy to Splunk (Runs on PR ONLY if rules/ changed)') {
            when {
                allOf {
                    expression { env.CHANGE_ID != null }
                    expression {
                        def changedFiles = sh(script: "git diff --name-only origin/${env.CHANGE_TARGET} HEAD", returnStdout: true).trim()
                        echo "Changed files in this PR:\n${changedFiles}"
                        return changedFiles.contains('rules/')
                    }
                }
            }
            steps {
                script {
                    echo "Rules folder modified. Deploying rules to Splunk..."
                    withCredentials([usernamePassword(credentialsId: "${CRED_ID}", usernameVariable: 'SPLUNK_USER', passwordVariable: 'SPLUNK_PASS')]) {
                        sh '''
                            ./venv/bin/pip install --quiet requests pyyaml
                            ./venv/bin/python3 - << 'EOF'
import os, requests, glob, yaml
from requests.auth import HTTPBasicAuth
splunk_url = os.environ.get('SPLUNK_HOST', 'https://host.docker.internal:8089') + '/services/saved/searches'
auth = HTTPBasicAuth(os.environ["SPLUNK_USER"], os.environ["SPLUNK_PASS"])
print(f"Connecting to Splunk at: {splunk_url}")
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
    if res.status_code in [200, 201]:
        print(f"Successfully deployed to Splunk: {title}")
    else:
        print(f"Failed to deploy {title} (Status {res.status_code}): {res.text}")
        exit(1)
EOF
                        '''
                    }
                }
            }
        }
    }
}