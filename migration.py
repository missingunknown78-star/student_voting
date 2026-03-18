# In your Flask shell or a migration script
from extensions import db
from admin.models import AccessCode

# Create the table
db.create_all()

# Insert a default access code
default_code = AccessCode(
    code='CTU-ADMIN-2024',  # Change this to whatever default you want
    description='Default admin access code',
    is_active=True
)
db.session.add(default_code)
db.session.commit()

print("✅ Access code table created with default code: CTU-ADMIN-2024")