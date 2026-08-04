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
                allOf {
                    // Only run when triggered by a Pull Request
                    expression { env.CHANGE_ID != null }
                    // Only run if files in rules/ directory were modified
                    expression {
                        def changedFiles = sh(
                            script: "git diff --name-only origin/${env.CHANGE_TARGET} HEAD", 
                            returnStdout: true
                        ).trim()
                        return changedFiles.contains('rules/')
                    }
                }
            }
            steps {
                echo '🚀 Executing deployment script for approved PR...'
                withCredentials([
                    usernamePassword(
                        credentialsId: "${CRED_ID}", 
                        usernameVariable: 'SPLUNK_USER', 
                        passwordVariable: 'SPLUNK_PASS'
                    ),
                    usernamePassword(
                        credentialsId: "${GH_CRED_ID}", 
                        usernameVariable: 'GH_USER', 
                        passwordVariable: 'GH_TOKEN'
                    )
                ]) {
                    // Run the external Python deployment script
                    sh './venv/bin/python3 scripts/deploy_splunk.py'
                }
            }
        }
    }

    post {
        always {
            echo '🧹 Pipeline execution completed.'
        }
        failure {
            echo '❌ Pipeline failed! Please check console logs for errors.'
        }
    }
}
