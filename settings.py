import os
import re
from dotenv import load_dotenv

load_dotenv()

# Detect platform
ON_PYTHONANYWHERE = 'PYTHONANYWHERE_DOMAIN' in os.environ
ON_RAILWAY = 'RAILWAY_ENVIRONMENT' in os.environ or 'RAILWAY_SERVICE_ID' in os.environ

# ============= DATABASE CONFIGURATION =============
if ON_RAILWAY:
    # Railway MySQL (via marketplace)
    if 'MYSQL_URL' in os.environ:
        # Use Railway's MySQL URL directly
        DATABASE_URL = os.environ.get('MYSQL_URL')
        # Parse URL for individual components
        url = os.environ.get('MYSQL_URL')
        match = re.match(r'mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', url)
        if match:
            MYSQL_USER = match.group(1)
            MYSQL_PASSWORD = match.group(2)
            MYSQL_HOST = match.group(3)
            MYSQL_PORT = match.group(4)
            MYSQL_DB = match.group(5)
    else:
        # Individual environment variables from Railway MySQL
        MYSQL_USER = os.environ.get('MYSQL_USER')
        MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
        MYSQL_HOST = os.environ.get('MYSQL_HOST')
        MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
        MYSQL_DB = os.environ.get('MYSQL_DATABASE')
        DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
        
elif ON_PYTHONANYWHERE:
    MYSQL_USER = "evotingprototype"
    MYSQL_PASSWORD = "student_votingdatabase"
    MYSQL_HOST = "evotingprototype.mysql.pythonanywhere-services.com"
    MYSQL_PORT = "3306"
    MYSQL_DB = "evotingprototype$student_voting"
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"
    
else:
    # Local XAMPP MySQL
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'student_voting')
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

# ============= SECRET KEY CONFIGURATION =============
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if ON_RAILWAY or ON_PYTHONANYWHERE:
        raise ValueError("No SECRET_KEY set in environment variables!")
    else:
        SECRET_KEY = "sabanal"
        print("⚠️  WARNING: Using development SECRET_KEY!")

# ============= EMAIL CONFIGURATION =============
MAIL_SERVER = os.environ.get('MAIL_SERVER', '142.250.150.108')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'False').lower() == 'true'
MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'True').lower() == 'true'
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

# ============= PRINT CONFIG FOR DEBUG (LOCAL ONLY) =============
if not ON_RAILWAY and not ON_PYTHONANYWHERE:
    print("=" * 50)
    print("📝 Configuration Loaded:")
    print(f"   Environment: Local")
    print(f"   SECRET_KEY: {'✅ Set' if SECRET_KEY else '❌ Missing'}")
    print(f"   Database: {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}")
    print(f"   Email: {'✅ Configured' if MAIL_USERNAME else '❌ Missing'}")
    print("=" * 50)