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





# ------------------- POSITION -------------------
class Position(db.Model):
    __tablename__ = 'positions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    color = db.Column(db.String(20), nullable=False, default='#3498db')  # Hex color code
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    # Relationship to candidates
    candidates = db.relationship('Candidate', backref='position', lazy=True)
    
    def __repr__(self):
        return f'<Position {self.name}>'


class Candidate(db.Model):
    __tablename__ = 'candidates'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    party_list = db.Column(db.String(200), nullable=True)
    
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    department = db.relationship('Department', backref='candidates', lazy=True)

    position_id = db.Column(db.Integer, db.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False)
    photo = db.Column(db.String(255))
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'))
    
    # NEW: Add scope field
    scope = db.Column(db.String(50), nullable=False)  # 'campus' or 'department'
    
    # Relationships
    election = db.relationship('Election', backref='candidates', lazy=True)

    @property
    def vote_count(self):
        from student.routes import count_votes_for_candidate
        return count_votes_for_candidate(self.id)
    
    @property
    def election_type(self):
        """Backward compatibility"""
        return 'SSG' if self.scope == 'campus' else 'Department'
    
    # NEW: Helper to get max votes for this candidate's position in this election
    @property
    def max_votes_for_position(self):
        """Get the maximum votes allowed for this position in this election"""
        if self.election_id:
            ep = ElectionPosition.query.filter_by(
                election_id=self.election_id, 
                position_id=self.position_id
            ).first()
            return ep.max_votes if ep else 1
        return 1


# admin/models.py - Replace ONLY the Election class with this

class Election(db.Model):
    __tablename__ = 'elections'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    
    # EXISTING: Keep for backward compatibility
    election_type = db.Column(db.String(50), nullable=False)  # 'Department' or 'SSG'
    
    # EXISTING: Keep both ID and name (your code uses both)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    department = db.Column(db.String(100), nullable=True)  # department name (redundant but needed)
    
    # NEW: More scalable scope field
    # Values: 'campus' or 'department'
    scope = db.Column(db.Enum('campus', 'department', name='election_scope'), 
                      nullable=True)  # Nullable initially for migration

    # NEW: Year level filtering for campus elections
    # Values: comma-separated string like "1,2,3,4" or "all" for all years
    year_levels = db.Column(db.String(50), nullable=True, default='all')

    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    results_published = db.Column(db.Boolean, default=False)
    results_published_at = db.Column(db.DateTime, nullable=True)

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
    
    @property
    def year_levels_list(self):
        """Return year levels as a list for easier checking"""
        if not self.year_levels or self.year_levels == 'all':
            return ['1', '2', '3', '4']  # All years
        return self.year_levels.split(',')
    
    def can_vote(self, student_year):
        """Check if a student with given year level can vote in this election"""
        if self.scope == 'department':
            # Department elections are filtered by department, not year
            return True
        
        if not self.year_levels or self.year_levels == 'all':
            return True
        
        year_levels = self.year_levels.split(',')
        return str(student_year) in year_levels
    
    def __repr__(self):
        return f'<Election {self.id}: {self.title}>'

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


# Add this to your models.py
class TallyVote(db.Model):
    """Model for storing official tally results"""
    __tablename__ = 'tally_votes'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    vote_count = db.Column(db.Integer, nullable=False, default=0)
    tally_timestamp = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Relationships
    election = db.relationship('Election', backref='tally_records')
    candidate = db.relationship('Candidate', backref='tally_records')
    
    def __repr__(self):
        return f'<TallyVote Election:{self.election_id} Candidate:{self.candidate_id} Votes:{self.vote_count}>'
    

 
class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    role = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Manila')).replace(tzinfo=None))

    def __repr__(self):
        return f"<AuditLog {self.action}>"
    
    

    # Add this after your Position model (around line 40-50)

class ElectionPosition(db.Model):
    """Junction table linking elections to positions with vote limits"""
    __tablename__ = 'election_positions'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False)
    
    # THIS IS THE KEY FIELD - how many votes allowed for this position in this election
    max_votes = db.Column(db.Integer, nullable=False, default=1)
    
    # Optional: Add min votes if needed (for positions that require minimum)
    min_votes = db.Column(db.Integer, nullable=False, default=1)
    
    # Optional: Display order in ballot
    display_order = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())

    # Relationships
    election = db.relationship('Election', backref=db.backref('election_positions', cascade='all, delete-orphan'))
    position = db.relationship('Position', backref=db.backref('election_positions', cascade='all, delete-orphan'))

    # Ensure unique combination of election and position
    __table_args__ = (
        db.UniqueConstraint('election_id', 'position_id', name='unique_election_position'),
    )

    def __repr__(self):
        return f'<ElectionPosition {self.election_id}:{self.position_id} max={self.max_votes}>'


        # Add this to your models.py

class Setting(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    section = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Setting {self.key}>'
    


from extensions import db
from datetime import datetime
import hashlib
import secrets
from datetime import datetime, timedelta



class AdminTrustedDevice(db.Model):
    __tablename__ = 'admin_trusted_devices'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    device_fingerprint = db.Column(db.String(255), nullable=False)
    device_name = db.Column(db.String(255))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.Text)
    browser = db.Column(db.String(255))
    os = db.Column(db.String(100))
    device_type = db.Column(db.String(50))
    trusted = db.Column(db.Boolean, default=True)
    is_current = db.Column(db.Boolean, default=False)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # For verification
    verification_token = db.Column(db.String(100), nullable=True)
    verification_sent_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    admin = db.relationship('Admin', backref=db.backref('trusted_devices', lazy='dynamic'))
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.device_fingerprint:
            self.generate_fingerprint()
    
    def generate_fingerprint(self):
        """Generate a unique fingerprint for this device based on consistent device characteristics"""
        import hashlib
        
        # FIXED: Removed secrets.token_hex(8) to make it consistent!
        # Using ONLY stable device characteristics that don't change between logins
        fingerprint_data = f"{self.admin_id}{self.ip_address}{self.user_agent}{self.browser}{self.os}"
        self.device_fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()
        return self.device_fingerprint
    
    def generate_verification_token(self):
        """Generate a verification token for email verification"""
        self.verification_token = secrets.token_urlsafe(32)
        self.verification_sent_at = datetime.utcnow()
        return self.verification_token
    
    def verify(self):
        """Mark device as trusted"""
        self.trusted = True
        self.verification_token = None
        self.verification_sent_at = None
        self.last_used = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(days=30)
    
    def is_expired(self):
        """Check if device trust has expired"""
        if not self.expires_at:
            return True
        return datetime.utcnow() > self.expires_at
    
    def update_last_used(self):
        """Update last used timestamp"""
        self.last_used = datetime.utcnow()
    
    @staticmethod
    def get_device_info(request):
        """Extract device info from request"""
        user_agent = request.headers.get('User-Agent', '')
        
        # Simple device type detection
        device_type = 'desktop'
        if 'mobile' in user_agent.lower() or 'iphone' in user_agent.lower() or 'android' in user_agent.lower():
            device_type = 'mobile'
        elif 'tablet' in user_agent.lower() or 'ipad' in user_agent.lower():
            device_type = 'tablet'
        
        # Browser detection
        browser = 'Unknown'
        if 'chrome' in user_agent.lower() and 'edg' not in user_agent.lower():
            browser = 'Chrome'
        elif 'firefox' in user_agent.lower():
            browser = 'Firefox'
        elif 'safari' in user_agent.lower() and 'chrome' not in user_agent.lower():
            browser = 'Safari'
        elif 'edge' in user_agent.lower() or 'edg' in user_agent.lower():
            browser = 'Edge'
        
        # OS detection
        os = 'Unknown'
        if 'windows' in user_agent.lower():
            os = 'Windows'
        elif 'mac' in user_agent.lower() and 'ios' not in user_agent.lower():
            os = 'macOS'
        elif 'linux' in user_agent.lower():
            os = 'Linux'
        elif 'android' in user_agent.lower():
            os = 'Android'
        elif 'iphone' in user_agent.lower() or 'ipad' in user_agent.lower():
            os = 'iOS'
        
        return {
            'user_agent': user_agent,
            'ip_address': request.remote_addr,
            'device_type': device_type,
            'browser': browser,
            'os': os
        }