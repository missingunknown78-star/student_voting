# update_admin_password.py
from app import app   # your Flask app instance
from extensions import db, bcrypt
from admin.models import Admin

# Enter new password here
new_password = "admin123"

# Generate hashed password
hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')

# Use app context to access DB
with app.app_context():
    admin = Admin.query.filter_by(username='admin').first()
    if admin:
        admin.password = hashed_password
        db.session.commit()
        print(f"Password for 'admin' has been updated successfully!")
    else:
        print("Admin user not found.")
