from extensions import db
from flask_login import UserMixin
from datetime import datetime

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

    # backward compatibility
    course = db.Column(db.String(100))

    # relational fields
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)

    birth_date = db.Column(db.Date)
    id_number = db.Column(db.String(50), unique=True)

    # BIOMETRIC / WEBAUTHN
    passkey_id = db.Column(db.LargeBinary)
    public_key = db.Column(db.LargeBinary)
    sign_count = db.Column(db.Integer, default=0)

    # WebAuthn challenge
    current_challenge = db.Column(db.LargeBinary)

    # 🔐 Forgot Password Token
    reset_token = db.Column(db.String(100), nullable=True)

    user_type = "student"

    # Relationships
    department = db.relationship('Department', backref='students')
    course_rel = db.relationship('Course', backref='students')


# ------------------- VOTE -------------------
class Vote(db.Model):
    __tablename__ = "votes"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)

    # relationships
    student = db.relationship("Student", backref="student_votes")
    candidate = db.relationship("Candidate", back_populates="votes")  # <-- match back_populates
    election = db.relationship("Election", backref="election_votes")


class LoginHistory(db.Model):
    __tablename__ = "login_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    device = db.Column(db.String(255))
    ip_address = db.Column(db.String(50))
    browser = db.Column(db.String(255))
    city = db.Column(db.String(100))
    region = db.Column(db.String(100))
    country = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("Student", backref="login_histories")











