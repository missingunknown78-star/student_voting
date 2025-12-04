#I dont know what is this for but thi is
#admin/create_admin.py



from extensions import db, bcrypt
from admin.models import Admin

# Replace these with your preferred credentials
first_name = "Admin"
last_name = "User"
username = "admin"
password_plain = "admin123"
email = "admin@example.com"

# Generate bcrypt hashed password
hashed_password = bcrypt.generate_password_hash(password_plain).decode('utf-8')

# Create new admin
new_admin = Admin(
    first_name=first_name,
    last_name=last_name,
    username=username,
    password=hashed_password,
    email=email
)

db.session.add(new_admin)
db.session.commit()

print(f"Admin account '{username}' created successfully!")
