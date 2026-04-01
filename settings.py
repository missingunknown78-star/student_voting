import os
from dotenv import load_dotenv

load_dotenv()

# Detect platform
ON_PYTHONANYWHERE = 'PYTHONANYWHERE_DOMAIN' in os.environ
ON_RAILWAY = 'RAILWAY_ENVIRONMENT' in os.environ or 'RAILWAY_SERVICE_ID' in os.environ

# ============= DATABASE CONFIGURATION =============
if ON_RAILWAY:
    # Railway MySQL (via marketplace)
    # Railway will provide MYSQL_URL or DATABASE_URL
    if 'MYSQL_URL' in os.environ:
        # Use Railway's MySQL URL directly
        DATABASE_URL = os.environ.get('MYSQL_URL')
        # Parse URL for individual components if needed
        # Format: mysql://user:password@host:port/database
    else:
        # Individual environment variables from Railway MySQL
        MYSQL_USER = os.environ.get('MYSQL_USER')
        MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
        MYSQL_HOST = os.environ.get('MYSQL_HOST')
        MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
        MYSQL_DB = os.environ.get('MYSQL_DB')
        DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
        
elif ON_PYTHONANYWHERE:
    MYSQL_USER = "evotingprototype"
    MYSQL_PASSWORD = "student_votingdatabase"
    MYSQL_HOST = "evotingprototype.mysql.pythonanywhere-services.com"
    MYSQL_DB = "evotingprototype$student_voting"
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"
    
else:
    # Local XAMPP MySQL
    MYSQL_USER = "root"
    MYSQL_PASSWORD = ""
    MYSQL_HOST = "localhost"
    MYSQL_DB = "student_voting"
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"

# ============= SECRET KEY CONFIGURATION =============
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if ON_RAILWAY or ON_PYTHONANYWHERE:
        raise ValueError("No SECRET_KEY set in environment variables!")
    else:
        SECRET_KEY = "sabanal"
        print("⚠️  WARNING: Using development SECRET_KEY!")

# ============= EMAIL CONFIGURATION =============
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))
MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'True').lower() == 'true'
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')