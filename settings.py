import os

# Detect if we are running on PythonAnywhere or locally
ON_PYTHONANYWHERE = 'PYTHONANYWHERE_DOMAIN' in os.environ

if ON_PYTHONANYWHERE:
    # PythonAnywhere MySQL credentials (replace with your actual username, password, database)
    MYSQL_USER = "evotingprototype"                               # your PythonAnywhere MySQL username
    MYSQL_PASSWORD = "student_votingdatabase"                     # your PythonAnywhere MySQL password
    MYSQL_HOST = "evotingprototype.mysql.pythonanywhere-services.com"  # host
    MYSQL_DB = "evotingprototype$student_voting"                  # database name
    SECRET_KEY = os.environ.get("SECRET_KEY", "sabanal")          # you can leave this using env
else:
    # Local XAMPP MySQL credentials
    MYSQL_USER = "root"
    MYSQL_PASSWORD = ""                                           # usually empty for XAMPP
    MYSQL_HOST = "localhost"
    MYSQL_DB = "student_voting"
    SECRET_KEY = "sabanal"
