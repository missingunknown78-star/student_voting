from extensions import db
from flask_login import UserMixin
from datetime import datetime
import pytz

# ------------------- ADMIN -------------------
class Admin(db.Model, UserMixin):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    user_type = db.Column(db.String(20), default='admin')


# ------------------- POSITION -------------------
class Position(db.Model):
    __tablename__ = 'positions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    # Relationship to candidates
    candidates = db.relationship('Candidate', backref='position', lazy=True)


# ------------------- CANDIDATE -------------------
class Candidate(db.Model):
    __tablename__ = 'candidates'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    course = db.Column(db.String(50))
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False)
    photo = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    # Relationship
    votes = db.relationship('Vote', backref='candidate', lazy=True)


# ------------------- ELECTION -------------------
class Election(db.Model):
    __tablename__ = 'elections'
    __table_args__ = {'extend_existing': True}  # <-- prevents "table already defined" error

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='Open')

    # NEW: link to Course table
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    # Relationship to access the course object
    course_rel = db.relationship('Course', backref='elections')

@property
def current_status(self):
    local_tz = pytz.timezone("Asia/Manila")
    now = datetime.now(local_tz)

    if now < self.start_date:
        return "Upcoming"
    elif self.start_date <= now <= self.end_date:
        return "Open"
    else:
        return "Closed"


# ------------------- DEPARTMENT -------------------
class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    # Relationship to courses
    courses = db.relationship('Course', backref='department', lazy=True)


# ------------------- COURSE -------------------
class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    course_name = db.Column(db.String(255), nullable=False)
    course_code = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
