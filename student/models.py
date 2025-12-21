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

    course = db.Column(db.String(100))  # keep existing string field for backward compatibility
    # ✅ Add new columns for relational storage
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)

    birth_date = db.Column(db.Date)
    id_number = db.Column(db.String(50), unique=True)

    # Biometric fields
    passkey_id = db.Column(db.String(255))
    public_key = db.Column(db.Text)
    sign_count = db.Column(db.Integer, default=0)

    user_type = "student"

    # Relationships for easy access
    department = db.relationship('Department', backref='students')
    course_rel = db.relationship('Course', backref='students')  # renamed relationship to avoid conflict with string field

class Vote(db.Model):
    __tablename__ = "votes"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)

    student = db.relationship("Student", backref="student_votes")        # changed
    candidate = db.relationship("Candidate", backref="candidate_votes")  # changed
    election = db.relationship("Election", backref="election_votes")     # changed
