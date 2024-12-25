pipeline {
    agent any
    stages {
        stage('Checkout Code') {
            steps {
                git branch: 'main', 
                    url: 'https://github.com/Faiqa-Nasir/SQE-EMS', 
                    credentialsId: 'github-token'
            }
        }
        stage('Install Dependencies') {
            steps {
                bat 'C:\\Users\\PMLS\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m pip install -r requirements.txt'
            }
        }
        stage('Upgrade Pip') {
            steps {
                bat 'C:\\Users\\PMLS\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m pip install --upgrade pip'
            }
        }
        stage('Run Tests') {
            steps {
                // Use full path to pytest
                bat 'C:\\Users\\PMLS\\AppData\\Local\\Programs\\Python\\Python312\\Scripts\\pytest.exe -v tests/'
            }
        }
    }
    post {
        always {
            echo 'Pipeline Completed'
        }
    }
}
