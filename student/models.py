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

    # keep existing string field for backward compatibility
    course = db.Column(db.String(100))

    # relational fields (UNCHANGED)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)

    birth_date = db.Column(db.Date)
    id_number = db.Column(db.String(50), unique=True)

    # 🔐 BIOMETRIC / WEBAUTHN FIELDS (FIXED TYPES ONLY)
    passkey_id = db.Column(db.LargeBinary)
    public_key = db.Column(db.LargeBinary)
    sign_count = db.Column(db.Integer, default=0)

    # REQUIRED for WebAuthn challenge
    current_challenge = db.Column(db.LargeBinary)

    user_type = "student"

    # Relationships (UNCHANGED)
    department = db.relationship('Department', backref='students')
    course_rel = db.relationship(
        'Course',
        backref='students'
    )  # renamed to avoid conflict with string field


class Vote(db.Model):
    __tablename__ = "votes"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)

    # relationships (UNCHANGED)
    student = db.relationship("Student", backref="student_votes")
    candidate = db.relationship("Candidate", backref="candidate_votes")
    election = db.relationship("Election", backref="election_votes")
