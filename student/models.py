# student/models.py

from extensions import db
from flask_login import UserMixin

class Student(db.Model, UserMixin):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    middle_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    suffix = db.Column(db.String(50))
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
    course = db.Column(db.String(100))
    birth_date = db.Column(db.Date)
    id_number = db.Column(db.String(50), unique=True)

    # 🔹 ADD THESE FOR BIOMETRIC LOGIN (WebAuthn passkeys)
    passkey_id = db.Column(db.String(255))        # ID of credential (Base64URL)
    public_key = db.Column(db.Text)               # Public key (Base64URL)
    sign_count = db.Column(db.Integer, default=0) # Counter for replay protection

    user_type = "student"


class Vote(db.Model):
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
