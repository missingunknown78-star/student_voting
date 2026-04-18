# setup_database.py - SIMPLE VERSION
from flask import Flask
from extensions import db

# Import ALL your models so SQLAlchemy knows about them
from admin.models import *
from student.models import *

app = Flask(__name__)

# ⚠️ UPDATE THESE 3 LINES with your MySQL credentials
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/student_voting'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    print("🗑️  Dropping all existing tables...")
    db.drop_all()
    
    print("📦 Creating fresh tables...")
    db.create_all()
    
    print("\n✅ DONE! Tables created:")
    
    # Show what was created
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    for table in inspector.get_table_names():
        print(f"   - {table}")
    
    print(f"\n📊 Total: {len(inspector.get_table_names())} tables")