pipeline {
    agent { label 'Test-DE' }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '15'))
    }

    environment {
        SIGMA_DIR    = 'rules/'
        SPLUNK_HOST  = 'https://host.docker.internal:8089'
        CRED_ID      = 'splunk-api-token'
        GH_CRED_ID   = 'github-credentials-id'
        REPO_NAME    = 'rkdhakad2023-jpg/detection-rules'
    }

    stages {
        stage('1. Validate & Convert Sigma Rules') {
            steps {
                echo '🔍 Validating Sigma rules and converting to Splunk SPL...'
                sh '''
                    python3 -m venv venv
                    ./venv/bin/pip install --quiet --upgrade pip
                    ./venv/bin/pip install --quiet sigma-cli pysigma-backend-splunk requests pyyaml
                    
                    # Validate Sigma Syntax
                    ./venv/bin/sigma check ${SIGMA_DIR}
                    
                    # Convert Sigma rules to SPL
                    mkdir -p output/
                    ./venv/bin/sigma convert -t splunk --without-pipeline ${SIGMA_DIR} > output/splunk_queries.spl
                '''
            }
        }

        stage('2. Deploy to Splunk on Approved PR') {
            when {
                expression { env.CHANGE_ID != null }
            }
            steps {
                withCredentials([
                    usernamePassword(credentialsId: "${CRED_ID}", usernameVariable: 'SPLUNK_USER', passwordVariable: 'SPLUNK_PASS'),
                    usernamePassword(credentialsId: "${GH_CRED_ID}", usernameVariable: 'GH_USER', passwordVariable: 'GH_TOKEN')
                ]) {
                    script {
                        // Check PR review status via GitHub API
                        def prStatus = sh(
                            script: """
                                curl -s -H "Authorization: token ${GH_TOKEN}" \\
                                "https://api.github.com/repos/${REPO_NAME}/pulls/${env.CHANGE_ID}/reviews" | \\
                                python3 -c "import sys, json; reviews=json.load(sys.stdin); print('APPROVED' if any(r.get('state')=='APPROVED' for r in reviews) else 'NOT_APPROVED')"
                            """,
                            returnStdout: true
                        ).trim()

                        if (prStatus == 'APPROVED') {
                            echo '✅ PR Approval confirmed! Proceeding with Splunk Deployment...'
                            
                            // Execute Splunk Deployment Script
                            sh './venv/bin/python3 scripts/deploy_splunk.py'
                            
                            // Post confirmation comment to GitHub PR
                            sh """
                                curl -s -H "Authorization: token ${GH_TOKEN}" \\
                                -H "Accept: application/vnd.github+json" \\
                                -X POST https://api.github.com/repos/${REPO_NAME}/issues/${env.CHANGE_ID}/comments \\
                                -d '{"body": "✅ **Deployment Successful!** The test detection rules have been validated and pushed to Splunk as Saved Searches. You are cleared to merge this PR to master."}'
                            """
                        } else {
                            echo '⏳ PR is not yet approved. Skipping Splunk deployment.'
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            echo '🧹 Pipeline execution completed.'
        }
        failure {
            echo '❌ Pipeline failed! Check logs for details.'
        }
    }
}
