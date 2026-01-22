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

    role = db.Column(db.String(50), nullable=False, default='Admin')  # link to admin_roles
    status = db.Column(db.String(20), default='Active')
    
    # ✅ Add this line back for 2FA
    totp_secret = db.Column(db.String(32), nullable=True)  # 32-char base32 key


class AdminRole(db.Model):
    __tablename__ = 'admin_roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())



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
    
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    department = db.relationship('Department', backref='candidates', lazy=True)

    position_id = db.Column(db.Integer, db.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False)
    photo = db.Column(db.String(255))
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'))
    election = db.relationship('Election', backref='candidates', lazy=True)

    votes = db.relationship(
        'Vote', 
        back_populates='candidate', 
        lazy=True,
        overlaps="candidate_votes"  # <-- added to fix warning
    )



# ------------------- ELECTION -------------------
class Election(db.Model):
    __tablename__ = 'elections'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    election_type = db.Column(db.String(50), nullable=False)  # Department or SSG

    # Store both ID and name
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    department = db.Column(db.String(100), nullable=True)  # department name

    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)

    # Optional link to Course table
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    # Relationships
    department_rel = db.relationship('Department', backref='elections')
    course_rel = db.relationship('Course', backref='elections')


    @property
    def status(self):
        """Dynamically return election status: Upcoming, Open, or Ended"""
        tz = pytz.timezone('Asia/Manila')
        now = datetime.now(tz)

        # Ensure start_date and end_date are timezone-aware
        start = self.start_date
        end = self.end_date
        if start.tzinfo is None:
            start = tz.localize(start)
        if end.tzinfo is None:
            end = tz.localize(end)

        if now < start:
            return "Upcoming"
        elif now > end:
            return "Ended"
        else:
            return "Open"


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


class Announcement(db.Model):
    __tablename__ = 'announcements'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)  # NULL = All
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Optional: relationship to department
    department = db.relationship('Department', backref=db.backref('announcements', lazy=True))

    def __repr__(self):
        return f"<Announcement {self.title} - {self.date}>"
    

class YearLevel(db.Model):
    __tablename__ = 'year_levels'

    id = db.Column(db.Integer, primary_key=True)
    year_name = db.Column(db.String(50), unique=True, nullable=False)

    # Relationship (future-proof)
    students = db.relationship('Student', backref='year_level', lazy=True)

class CtuStudent(db.Model):
    __tablename__ = "ctu_students"

    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    course = db.Column(db.String(100))
    email = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True)
