# create_admin.py
from flask import Flask
from extensions import db
from flask_bcrypt import Bcrypt
from admin.models import Admin
from datetime import datetime

app = Flask(__name__)

# USE THE SAME CONNECTION STRING
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/student_voting'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize bcrypt
bcrypt = Bcrypt(app)

db.init_app(app)

with app.app_context():
    # Check if admin already exists
    existing_admin = Admin.query.filter_by(username='admin').first()
    
    if existing_admin:
        print("⚠️  Admin already exists! Updating...")
        admin = existing_admin
    else:
        print("📝 Creating new admin account...")
        admin = Admin()
    
    # Set admin details
    admin.username = 'admin'
    admin.email = 'ctucomelecprototype@gmail.com'
    admin.first_name = 'System'
    admin.last_name = 'Administrator'
    admin.role = 'Admin'
    admin.status = 'Active'
    admin.password = bcrypt.generate_password_hash('Admin1!').decode('utf-8')
    
    db.session.add(admin)
    db.session.commit()
    
    print("\n" + "=" * 60)
    print("✅ ADMIN ACCOUNT CREATED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Username: {admin.username}")
    print(f"Password: Admin1!")
    print(f"Email: {admin.email}")
    print(f"Name: {admin.first_name} {admin.last_name}")
    print(f"Role: {admin.role}")
    print(f"Status: {admin.status}")
    print("=" * 60)
    print("\n🔐 You can now login to the admin panel!")