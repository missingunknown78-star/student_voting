# create_tables.py
from flask import Flask
from extensions import db

# ===== IMPORT MODELS ONE BY ONE FROM ADMIN =====
from admin.models import (
    Admin,              # admins table
    Position,           # positions table
    Candidate,          # candidates table
    Election,           # elections table
    Department,         # departments table
    Course,             # courses table
    Announcement,       # announcements table
    YearLevel,          # year_levels table
    CtuStudent,         # ctu_students table
    TallyVote,          # tally_votes table
    AuditLog,           # audit_logs table
    ElectionPosition    # election_positions table
)

# ===== IMPORT MODELS ONE BY ONE FROM STUDENT =====
# ⚠️ IMPORTANT: Import these AFTER admin models to avoid circular imports
from student.models import (
    Student,            # students table
    Vote,               # votes table
    TrustedDevice,      # trusted_devices table
    DeletionRequest     # deletion_requests table
)

import pymysql
from sqlalchemy import inspect
pymysql.install_as_MySQLdb()

# ===== YOUR DATABASE CONFIGURATION =====
MYSQL_USER = 'root'           # Your MySQL username
MYSQL_PASSWORD = ''           # Your MySQL password (empty for XAMPP)
MYSQL_HOST = 'localhost'      # Your MySQL host
MYSQL_DB = 'student_voting'   # ⚠️ CHANGE THIS to your database name!

# ===== CREATE FLASK APP =====
app = Flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ===== INITIALIZE DATABASE =====
db.init_app(app)

# ===== PRINT ALL IMPORTED MODELS (for verification) =====
print("=" * 60)
print("✅ MODELS LOADED SUCCESSFULLY:")
print("=" * 60)
print("\n📋 ADMIN MODELS:")
admin_models = ['Admin', 'Position', 'Candidate', 'Election', 'Department', 
                'Course', 'Announcement', 'YearLevel', 'CtuStudent', 
                'TallyVote', 'AuditLog', 'ElectionPosition']
for model in admin_models:
    print(f"   ✅ {model}")

print("\n📋 STUDENT MODELS:")
student_models = ['Student', 'Vote', 'TrustedDevice', 'DeletionRequest']
for model in student_models:
    print(f"   ✅ {model}")
print("=" * 60)

# ===== SAFETY CHECK =====
print("\n⚠️  D A T A B A S E   R E C R E A T I O N   S C R I P T")
print("=" * 60)
print(f"Database: {MYSQL_DB}")
print(f"Host: {MYSQL_HOST}")
print(f"User: {MYSQL_USER}")
print("=" * 60)
print("\n❌❌❌ WARNING: This will DELETE all existing tables and data! ❌❌❌")
print("\nMake sure you have a backup before continuing!")
print("=" * 60)

response = input("\n👉 Type 'YES' to continue: ")
if response != 'YES':
    print("❌ Operation cancelled.")
    exit()

# ===== DO THE MAGIC =====
with app.app_context():
    try:
        # Test connection first
        print("\n🔍 Testing database connection...")
        db.engine.connect()
        print("✅ Connected successfully!")
        
        # Get inspector
        inspector = inspect(db.engine)
        
        # Show existing tables
        existing_tables = inspector.get_table_names()
        if existing_tables:
            print(f"\n📋 Found {len(existing_tables)} existing tables:")
            for table in existing_tables:
                print(f"   - {table}")
        else:
            print("\n📋 No existing tables found.")
        
        # Final confirmation
        if existing_tables:
            confirm = input(f"\n⚠️  Drop ALL {len(existing_tables)} tables and recreate? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ Operation cancelled.")
                exit()
        
        # DROP all tables
        print("\n🗑️  Dropping all tables...")
        db.drop_all()
        print("✅ Tables dropped!")
        
        # CREATE all tables
        print("\n🏗️  Creating new tables from your models...")
        db.create_all()
        print("✅ Tables created!")
        
        # Show created tables
        inspector = inspect(db.engine)
        new_tables = inspector.get_table_names()
        print(f"\n📋 Tables successfully created ({len(new_tables)}):")
        for table in sorted(new_tables):
            print(f"   ✅ {table}")
        
        # Expected tables from your models
        expected = [
            # Admin models
            'admins', 'positions', 'candidates', 'elections', 
            'departments', 'courses', 'announcements', 'year_levels',
            'ctu_students', 'tally_votes', 'audit_logs', 'election_positions',
            # Student models
            'students', 'votes', 'trusted_devices', 'deletion_requests'
        ]
        
        print(f"\n📋 Expected tables ({len(expected)}):")
        
        # Check which ones are created vs missing
        created_count = 0
        missing_count = 0
        
        for table in sorted(expected):
            if table in new_tables:
                print(f"   ✅ {table}")
                created_count += 1
            else:
                print(f"   ❌ {table}")
                missing_count += 1
        
        print("\n" + "=" * 60)
        print(f"✅ {created_count} tables created successfully")
        if missing_count > 0:
            print(f"❌ {missing_count} tables missing")
        else:
            print("🎉 ALL TABLES CREATED PERFECTLY!")
        print("=" * 60)
        
        # ===== CREATE DEFAULT DATA =====
        print("\n📦 Creating default data...")
        
        # Create default admin if none exists
        from werkzeug.security import generate_password_hash
        from admin.models import Admin
        
        admin_count = Admin.query.count()
        if admin_count == 0:
            default_admin = Admin(
                first_name="System",
                last_name="Administrator",
                username="admin",
                password=generate_password_hash("admin123"),
                email="admin@ctu.edu.ph",
                role="Admin",
                status="Active",
                totp_secret=None  # Explicitly set to None
            )
            db.session.add(default_admin)
            db.session.commit()
            print("   ✅ Default admin created (username: admin, password: admin123)")
        else:
            print("   ⏩ Admin already exists, skipping...")
        
        # Create default year levels
        year_level_count = YearLevel.query.count()
        if year_level_count == 0:
            year_levels = [
                YearLevel(year_name="1st Year"),
                YearLevel(year_name="2nd Year"),
                YearLevel(year_name="3rd Year"),
                YearLevel(year_name="4th Year")
            ]
            db.session.add_all(year_levels)
            db.session.commit()
            print("   ✅ Default year levels created (1st-4th Year)")
        else:
            print("   ⏩ Year levels already exist, skipping...")
        
        print("✅ Default data created successfully!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Is MySQL running in XAMPP?")
        print("2. Does the database exist? (Create it first in phpMyAdmin)")
        print("3. Is your database name correct in the script?")
        print("4. Can Python find your models? (Check folder structure)")
        import traceback
        traceback.print_exc()

print("\nPress Enter to exit...")
input()