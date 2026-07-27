pipeline {
    agent any

    environment {
        SIGMA_DIR   = 'rules/'
        SPLUNK_HOST = 'http://localhost:8000'
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
                        # 1. Create a clean virtual environment
                        python3 -m venv venv
                        
                        # 2. Install dependencies inside the virtual environment
                        ./venv/bin/pip install --quiet --upgrade pip
                        ./venv/bin/pip install --quiet sigma-cli pysigma-backend-splunk
                        
                        # 3. Lint the YAML files using the virtual environment's sigma binary
                        ./venv/bin/sigma check ${SIGMA_DIR}
                        
                        # 4. Convert to test Splunk SPL
                        mkdir -p output/
                        ./venv/bin/sigma convert -t splunk ${SIGMA_DIR} > output/splunk_queries.spl
                    '''
                }
            }
        }

        stage('2. Deploy to Splunk (Runs ONLY after merge to Master/Main)') {
            when {
                branch 'master' // Change to 'main' if your default branch is main
            }
            steps {
                script {
                    echo "PR was merged! Deploying rules to Splunk..."
                    withCredentials([string(credentialsId: "${CRED_ID}", variable: 'SPLUNK_TOKEN')]) {
                        docker.image('python:3.11-slim').inside {
                            sh '''
                                pip install --quiet requests pyyaml
                                python3 - << 'EOF'
import os, requests, glob, yaml

splunk_url = os.environ['SPLUNK_HOST'] + '/services/saved/searches'
headers = {'Authorization': f'Bearer {os.environ["SPLUNK_TOKEN"]}'}

for rule_file in glob.glob('rules/*.yml'):
    with open(rule_file, 'r') as rf:
        rule_data = yaml.safe_load(rf)
        
    title = rule_data.get('title', 'Detection Rule')
    description = rule_data.get('description', '')
    
    payload = {
        'name': f"Detection - {title}",
        'search': 'index=main sourcetype=windows', // Placeholder search query logic
        'description': description,
        'is_scheduled': '1'
    }
    
    res = requests.post(splunk_url, data=payload, headers=headers, verify=False)
    if res.status_code in [200, 201]:
        print(f"Successfully deployed to Splunk: {title}")
    else:
        print(f"Failed to deploy {title}: {res.text}")
        exit(1)
EOF
                            '''
                        }
                    }
                }
            }
        }
    }
}
