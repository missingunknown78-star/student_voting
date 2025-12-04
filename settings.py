# settings.py

import os

# Detect if we are running on PythonAnywhere or locally
# (PythonAnywhere automatically sets the environment variable 'PYTHONANYWHERE_DOMAIN')
ON_PYTHONANYWHERE = 'PYTHONANYWHERE_DOMAIN' in os.environ

if ON_PYTHONANYWHERE:
    # PythonAnywhere MySQL credentials
    MYSQL_USER = os.environ.get("MYSQL_USER")             # e.g., yourusername
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")     # your password
    MYSQL_HOST = os.environ.get("MYSQL_HOST")             # e.g., yourusername.mysql.pythonanywhere-services.com
    MYSQL_DB = os.environ.get("MYSQL_DB")                 # e.g., yourusername$student_voting
    SECRET_KEY = os.environ.get("SECRET_KEY", "sabanal")  # can also set a custom one in environment
else:
    # Local XAMPP MySQL credentials
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_DB = os.environ.get("MYSQL_DB", "student_voting")
    SECRET_KEY = os.environ.get("SECRET_KEY", "sabanal")
