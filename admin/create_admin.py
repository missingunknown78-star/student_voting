# admin/create_admin.py
import sys
import os
import pymysql
pymysql.install_as_MySQLdb()

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extensions import db, bcrypt
from flask import Flask

# Import ALL models to resolve relationships
from admin.models import Admin, YearLevel  # YearLevel needs Student
from student.models import Student  # Import Student to fix the relationship

# Create a minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/student_voting'  # Change this!
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

# Initialize extensions with app
db.init_app(app)
bcrypt.init_app(app)

# Admin credentials
first_name = "Admin"
last_name = "User"
username = "admin"
password_plain = "admin123"
email = "admin@ctu.edu.ph"  # Changed to match your create_tables.py

with app.app_context():
    # Create all tables if they don't exist (optional)
    # db.create_all()
    
    # Check if admin already exists
    existing_admin = Admin.query.filter_by(username=username).first()
    
    if existing_admin:
        print(f"❌ Admin '{username}' already exists!")
        print(f"   ID: {existing_admin.id}")
        print(f"   Email: {existing_admin.email}")
        print(f"   Password hash: {existing_admin.password[:30]}...")
        
        # 🔍 TEST THE EXISTING PASSWORD
        print("\n🔍 Testing existing password:")
        try:
            is_valid = bcrypt.check_password_hash(existing_admin.password, password_plain)
            print(f"   Password '{password_plain}' valid? {is_valid}")
            
            if not is_valid:
                print("   ⚠️ Password hash doesn't match! Updating password...")
                existing_admin.password = bcrypt.generate_password_hash(password_plain).decode('utf-8')
                db.session.commit()
                print("   ✅ Password updated successfully!")
        except Exception as e:
            print(f"   ❌ Error checking password: {e}")
            print("   ⚠️ Password hash may be corrupted. Recreating...")
            existing_admin.password = bcrypt.generate_password_hash(password_plain).decode('utf-8')
            db.session.commit()
            print("   ✅ Password reset successfully!")
    else:
        # Hash password
        hashed_password = bcrypt.generate_password_hash(password_plain).decode('utf-8')
        
        print(f"🔐 Generated hash: {hashed_password[:50]}...")
        print(f"   Hash length: {len(hashed_password)}")
        print(f"   Starts with $2b$? {hashed_password.startswith('$2b$')}")
        
        # Create new admin
        new_admin = Admin(
            first_name=first_name,
            last_name=last_name,
            username=username,
            password=hashed_password,
            email=email,
            role='Admin',  # Explicitly set
            status='Active',  # Explicitly set
            totp_secret=None,  # Explicitly set to None
            is_2fa_enabled=False  # If you added this field
        )
        
        db.session.add(new_admin)
        db.session.commit()
        
        print("=" * 50)
        print("✅ ADMIN ACCOUNT CREATED SUCCESSFULLY!")
        print("=" * 50)
        print(f"   Username: {username}")
        print(f"   Password: {password_plain}")
        print(f"   Email: {email}")
        print(f"   Hash: {hashed_password[:30]}...")
        print("=" * 50)
        
        # 🔍 VERIFY THE NEW PASSWORD
        print("\n🔍 Verifying new password:")
        try:
            # Fetch the admin again to make sure
            test_admin = Admin.query.filter_by(username=username).first()
            is_valid = bcrypt.check_password_hash(test_admin.password, password_plain)
            print(f"   Password verification: {'✅ SUCCESS' if is_valid else '❌ FAILED'}")
            
            if not is_valid:
                print("   ⚠️ Something went wrong with password hashing!")
        except Exception as e:
            print(f"   ❌ Error verifying password: {e}")

print("\n✅ Script completed!")