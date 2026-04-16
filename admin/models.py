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
    
    # 2FA
    totp_secret = db.Column(db.String(32), nullable=True)  # 32-char base32 key
    
    # Password Reset Token
    reset_token = db.Column(db.String(100), nullable=True, unique=True)
    
    # ✉️ Email Change Verification (ADD THESE 4 COLUMNS)
    email_change_token = db.Column(db.String(100), nullable=True)
    new_email_pending = db.Column(db.String(120), nullable=True)
    email_change_requested_at = db.Column(db.DateTime, nullable=True)
    email_change_expires_at = db.Column(db.DateTime, nullable=True)
    email_change_confirmed = db.Column(db.Boolean, default=False) 

    
    def get_id(self):
        return str(self.id)





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
    __table_args__ = (
        # This creates a composite unique constraint
        # A candidate can have the same name in different elections,
        # but cannot have duplicate name in the same election
        db.UniqueConstraint('first_name', 'last_name', 'election_id', 
                           name='unique_candidate_per_election'),
    )

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    party_list = db.Column(db.String(200), nullable=True)
    platform = db.Column(db.Text, nullable=True)  # Platform field
    
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    department = db.relationship('Department', backref='candidates', lazy=True)
    
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    course = db.relationship('Course', backref='candidates', lazy=True)
    
    # Program Type field (Day/Night)
    program_type_id = db.Column(db.Integer, db.ForeignKey('program_types.id'), nullable=True)
    program_type = db.relationship('ProgramType', backref='candidates', lazy=True)

    # ✅ ADD THIS LINE - Year Level field
    year_level_id = db.Column(db.Integer, db.ForeignKey('year_levels.id'), nullable=True)
    year_level = db.relationship('YearLevel', backref='candidates', lazy=True)
    
    candidate_type = db.Column(db.String(20), default='student')
    studio_name = db.Column(db.String(200), nullable=True)

    position_id = db.Column(db.Integer, db.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False)
    photo = db.Column(db.String(255))
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'))
    
    # Scope field
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
    
    # Helper to get max votes for this candidate's position in this election
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
    
    # Helper to check if candidate matches student's program type
    def matches_student_program_type(self, student_program_type_id):
        """Check if candidate's program type matches student's program type"""
        # If candidate has no program type restriction, they match anyone
        if not self.program_type_id:
            return True
        # Otherwise, must match exactly
        return self.program_type_id == student_program_type_id
    
    # Helper to get program type name
    @property
    def program_type_name(self):
        """Get the program type name (Day/Night) or None"""
        return self.program_type.name if self.program_type else None
    
    # Helper to check if candidate is restricted to a specific program type
    @property
    def is_program_type_restricted(self):
        """Check if candidate is restricted to a specific program type"""
        return self.program_type_id is not None
    
    def __repr__(self):
        return f'<Candidate {self.first_name} {self.last_name} (Election: {self.election_id})>'


# admin/models.py - Complete Election class with caching fields

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

    # ===== NEW: Caching fields for performance optimization =====
    cached_results = db.Column(db.Text, nullable=True)  # JSON string of cached vote counts
    cached_at = db.Column(db.DateTime, nullable=True)   # When results were last cached
    cached_voter_turnout = db.Column(db.Float, nullable=True)  # Pre-calculated turnout
    cached_total_votes = db.Column(db.Integer, nullable=True)  # Pre-calculated total votes

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
    
    # ========== NEW PROPERTIES FOR TIMEZONE-AWARE DATES ==========
    @property
    def start_date_manila(self):
        """Get start_date as Manila timezone-aware"""
        import pytz
        if self.start_date:
            manila = pytz.timezone('Asia/Manila')
            if self.start_date.tzinfo is None:
                return manila.localize(self.start_date)
            return self.start_date.astimezone(manila)
        return None
    
    @property
    def end_date_manila(self):
        """Get end_date as Manila timezone-aware"""
        import pytz
        if self.end_date:
            manila = pytz.timezone('Asia/Manila')
            if self.end_date.tzinfo is None:
                return manila.localize(self.end_date)
            return self.end_date.astimezone(manila)
        return None
    
    @property
    def is_ongoing(self):
        """Check if election is currently ongoing"""
        from datetime import datetime
        import pytz
        if self.start_date_manila and self.end_date_manila:
            now = datetime.now(pytz.timezone('Asia/Manila'))
            return self.start_date_manila <= now <= self.end_date_manila
        return False
    # ========== END OF NEW PROPERTIES ==========
    
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
    
    # ===== Helper methods for cache management =====
    def is_cache_valid(self, max_age_hours=1):
        """Check if cached results are still valid"""
        if not self.cached_at:
            return False
        
        tz = pytz.timezone('Asia/Manila')
        now = datetime.now(tz)
        
        # Ensure cached_at is timezone-aware
        cached_at = self.cached_at
        if cached_at.tzinfo is None:
            cached_at = tz.localize(cached_at)
        
        # Check if cache is older than max_age_hours
        age = (now - cached_at).total_seconds()
        return age < (max_age_hours * 3600)
    
    def invalidate_cache(self):
        """Clear cached results (call when new votes are cast)"""
        self.cached_results = None
        self.cached_at = None
        self.cached_voter_turnout = None
        self.cached_total_votes = None
    
    def update_cache(self, results_data, voter_turnout, total_votes):
        """Update cached results"""
        import json
        from datetime import datetime
        
        self.cached_results = json.dumps(results_data)
        self.cached_voter_turnout = voter_turnout
        self.cached_total_votes = total_votes
        self.cached_at = datetime.now(pytz.timezone('Asia/Manila'))
    
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


import pytz
from datetime import datetime

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

    @property
    def created_at_manila(self):
        """Convert created_at from UTC to Manila time"""
        if self.created_at:
            # Define timezones
            utc = pytz.UTC
            manila = pytz.timezone('Asia/Manila')
            
            # If created_at is naive (no timezone), assume it's UTC
            if self.created_at.tzinfo is None:
                # Tell Python it's UTC
                utc_dt = utc.localize(self.created_at)
            else:
                utc_dt = self.created_at
            
            # Convert to Manila time
            manila_dt = utc_dt.astimezone(manila)
            return manila_dt
        return None

    @property
    def created_at_formatted(self):
        """Get formatted created_at in Manila time"""
        manila_time = self.created_at_manila
        if manila_time:
            return manila_time.strftime('%b %d, %Y at %I:%M %p')
        return None

    def __repr__(self):
        return f"<Announcement {self.title} - {self.date}>"
    

class YearLevel(db.Model):
    __tablename__ = 'year_levels'

    id = db.Column(db.Integer, primary_key=True)
    year_name = db.Column(db.String(50), unique=True, nullable=False)

    # Relationship (future-proof)
    students = db.relationship('Student', backref='year_level', lazy=True)

# In your admin/models.py

class CtuStudent(db.Model):
    __tablename__ = "ctu_students"

    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    course = db.Column(db.String(100))
    email = db.Column(db.String(150))
    year_level = db.Column(db.String(50))  # NEW: Store year level as string (e.g., "1st Year", "2nd Year", etc.)
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
    """Junction table linking elections to positions with vote limits and course/program type restrictions"""
    __tablename__ = 'election_positions'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False)
    
    # Department restriction (for campus-wide elections)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    
    # Course restriction (for both campus and department elections)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='SET NULL'), nullable=True)
    
    # Program type restriction (Day/Night - for both campus and department elections)
    program_type_id = db.Column(db.Integer, db.ForeignKey('program_types.id', ondelete='SET NULL'), nullable=True)
    
    # Year level restriction (1,2,3,4 - for year-specific positions)
    year_level = db.Column(db.Integer, nullable=True)  # 1, 2, 3, 4, or NULL for "All Years"
    
    # THIS IS THE KEY FIELD - how many votes allowed for this position in this election
    max_votes = db.Column(db.Integer, nullable=False, default=1)
    
    # Optional: Add min votes if needed (for positions that require minimum)
    min_votes = db.Column(db.Integer, nullable=False, default=1)
    
    # Optional: Display order in ballot
    display_order = db.Column(db.Integer, default=0)
    
    # Timestamps - FIXED: Added default for updated_at
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relationships
    election = db.relationship('Election', backref=db.backref('election_positions', cascade='all, delete-orphan'))
    position = db.relationship('Position', backref=db.backref('election_positions', cascade='all, delete-orphan'))
    department = db.relationship('Department', backref='election_positions')
    course = db.relationship('Course', backref='election_positions')
    program_type = db.relationship('ProgramType', backref='election_positions')

    # Ensure unique combination of election and position
    __table_args__ = (
        db.UniqueConstraint('election_id', 'position_id', name='unique_election_position'),
    )

    def __repr__(self):
        parts = [f'<ElectionPosition {self.election_id}:{self.position_id} max={self.max_votes}']
        if self.department_id:
            parts.append(f' department={self.department_id}')
        if self.course_id:
            parts.append(f' course={self.course_id}')
        if self.program_type_id:
            parts.append(f' program_type={self.program_type_id}')
        if self.year_level:
            parts.append(f' year_level={self.year_level}')
        parts.append('>')
        return ''.join(parts)



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
        """
        Generate a unique fingerprint for this device.
        🔥 FIXED: Removed IP address - IP changes too frequently!
        Using ONLY stable device characteristics: admin_id + user_agent + browser + os
        """
        import hashlib
        
        # 🔥 CRITICAL FIX: Remove IP address from fingerprint
        # IP addresses change when switching networks, restarting router, etc.
        fingerprint_data = f"{self.admin_id}{self.user_agent}{self.browser}{self.os}"
        # OLD (WRONG): fingerprint_data = f"{self.admin_id}{self.ip_address}{self.user_agent}{self.browser}{self.os}"
        
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


class TwoFADisableToken(db.Model):
    """Model for storing 2FA disable confirmation tokens"""
    __tablename__ = 'twofa_disable_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    # Relationship
    admin = db.relationship('Admin', backref=db.backref('twofa_disable_tokens', lazy='dynamic'))
    
    def __init__(self, admin_id):
        import secrets
        from datetime import datetime, timedelta
        
        self.admin_id = admin_id
        self.token = secrets.token_urlsafe(32)  # Generate secure random token
        self.expires_at = datetime.utcnow() + timedelta(minutes=15)  # 15 minute expiry
    
    def is_valid(self):
        """Check if token is valid (not used and not expired)"""
        from datetime import datetime
        return not self.used and datetime.utcnow() < self.expiresats
    
    def __repr__(self):
        return f'<TwoFADisableToken for Admin {self.admin_id}>'
    
    

class PdfResult(db.Model):
    """Model for storing uploaded PDF result files"""
    __tablename__ = 'pdf_results'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)  # Size in bytes
    uploaded_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    uploaded_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    description = db.Column(db.String(500), nullable=True)
    
    # Relationships
    election = db.relationship('Election', backref=db.backref('pdf_results', lazy=True, cascade='all, delete-orphan'))
    uploader = db.relationship('Admin', backref=db.backref('uploaded_pdfs', lazy=True))
    
    def __repr__(self):
        return f'<PdfResult {self.filename} for Election {self.election_id}>'
    
    @property
    def formatted_size(self):
        """Return file size in human readable format"""
        if not self.file_size:
            return 'Unknown'
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"





# Add to admin/models.py - VoteDistribution model for caching department-level vote counts

class VoteDistribution(db.Model):
    """Cached vote distribution data for faster analytics"""
    __tablename__ = 'vote_distributions'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)

    # --- MODIFIED: Make department_id nullable (can be NULL for course/program_type groupings) ---
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), nullable=True)

    # --- NEW: Add the columns you created in MySQL ---
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='SET NULL'), nullable=True)
    program_type_id = db.Column(db.Integer, db.ForeignKey('program_types.id', ondelete='SET NULL'), nullable=True)
    grouping_type = db.Column(db.String(20), nullable=True)  # 'department', 'course', 'program_type'
    grouping_name = db.Column(db.String(200), nullable=True)

    # Vote counts
    vote_count = db.Column(db.Integer, nullable=False, default=0)
    percentage = db.Column(db.Float, nullable=True)

    # Position info
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    position_name = db.Column(db.String(100), nullable=True)

    # Timestamps
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    election = db.relationship('Election', backref=db.backref('vote_distributions', lazy='dynamic', cascade='all, delete-orphan'))
    candidate = db.relationship('Candidate', backref=db.backref('vote_distributions', lazy='dynamic', cascade='all, delete-orphan'))
    department = db.relationship('Department', backref=db.backref('vote_distributions', lazy='dynamic'))
    # --- NEW: Add relationships for new columns ---
    course = db.relationship('Course', backref='vote_distributions')
    program_type = db.relationship('ProgramType', backref='vote_distributions')
    position = db.relationship('Position', backref='vote_distributions')

    # --- MODIFIED: Update the unique constraint to include new columns ---
    __table_args__ = (
        db.UniqueConstraint('election_id', 'candidate_id', 'department_id',
                           'course_id', 'program_type_id',
                           name='unique_candidate_grouping'),
    )

    def __repr__(self):
        # Optional: update repr for clarity
        group_info = f" Dept:{self.department_id}" if self.department_id else (f" Course:{self.course_id}" if self.course_id else (f" Prog:{self.program_type_id}" if self.program_type_id else ""))
        return f'<VoteDistribution E{self.election_id} C{self.candidate_id}{group_info}: {self.vote_count}>'

    # --- UPDATE: Modify your helper methods if necessary (e.g., update_or_create) ---
    @classmethod
    def update_or_create(cls, election_id, candidate_id, vote_count, position_id,
                         position_name=None, department_id=None, course_id=None,
                         program_type_id=None, grouping_type=None, grouping_name=None):
        """Update existing or create new distribution record with flexible grouping."""
        # Query based on which grouping ID is provided
        query = cls.query.filter_by(
            election_id=election_id,
            candidate_id=candidate_id
        )
        if department_id is not None:
            query = query.filter_by(department_id=department_id, course_id=None, program_type_id=None)
        elif course_id is not None:
            query = query.filter_by(course_id=course_id, department_id=None, program_type_id=None)
        elif program_type_id is not None:
            query = query.filter_by(program_type_id=program_type_id, department_id=None, course_id=None)
        else:
            # Should not happen, but fallback
            return None

        distribution = query.first()

        if distribution:
            distribution.vote_count = vote_count
            distribution.updated_at = datetime.utcnow()
        else:
            distribution = cls(
                election_id=election_id,
                candidate_id=candidate_id,
                department_id=department_id,
                course_id=course_id,
                program_type_id=program_type_id,
                vote_count=vote_count,
                position_id=position_id,
                position_name=position_name,
                grouping_type=grouping_type,
                grouping_name=grouping_name
            )
            db.session.add(distribution)

        return distribution

    @classmethod
    def calculate_percentages(cls, election_id):
        """Recalculate percentages for all records in an election"""
        from sqlalchemy import func

        candidate_totals = db.session.query(
            cls.candidate_id,
            func.sum(cls.vote_count).label('total')
        ).filter(
            cls.election_id == election_id
        ).group_by(cls.candidate_id).all()

        totals_dict = {c_id: total for c_id, total in candidate_totals}

        distributions = cls.query.filter_by(election_id=election_id).all()
        for dist in distributions:
            total = totals_dict.get(dist.candidate_id, 1)
            dist.percentage = (dist.vote_count / total * 100) if total > 0 else 0

        db.session.commit()


# Add to admin/models.py - for tracking analytics exports

class AnalyticsExport(db.Model):
    """Track exports of analytics data"""
    __tablename__ = 'analytics_exports'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    export_type = db.Column(db.String(50), nullable=False)  # 'pdf', 'excel', 'csv'
    file_path = db.Column(db.String(255), nullable=True)
    exported_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)
    
    # Relationships
    admin = db.relationship('Admin', backref='analytics_exports')
    election = db.relationship('Election', backref='analytics_exports')




class DeletionRequestAudit(db.Model):
    """Audit log for processed deletion requests"""
    __tablename__ = 'deletion_request_audit'
    
    id = db.Column(db.Integer, primary_key=True)
    original_request_id = db.Column(db.Integer, nullable=True)  # Original ID from deletion_requests
    student_id = db.Column(db.Integer, nullable=False)
    student_name = db.Column(db.String(255), nullable=False)
    student_id_number = db.Column(db.String(50), nullable=True)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'approved', 'rejected', 'cancelled'
    action_taken = db.Column(db.String(50), nullable=False)  # 'approved', 'rejected'
    admin_notes = db.Column(db.Text, nullable=True)
    request_date = db.Column(db.DateTime, nullable=False)
    processed_date = db.Column(db.DateTime, nullable=False)
    processed_by = db.Column(db.Integer, nullable=True)
    processed_by_username = db.Column(db.String(100), nullable=True)
    votes_anonymized = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DeletionRequestAudit {self.id}: {self.student_name} - {self.status}>'
    




class AccessCode(db.Model):
    """Model for storing admin access codes"""
    __tablename__ = 'access_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), nullable=False)
    secret_path = db.Column(db.String(100), nullable=False, default='access')  # New field for dynamic URL
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)  # Optional expiration
    
    # Relationships
    creator = db.relationship('Admin', foreign_keys=[created_by], backref='created_access_codes')
    updater = db.relationship('Admin', foreign_keys=[updated_by], backref='updated_access_codes')
    
    def __repr__(self):
        return f'<AccessCode {self.code[:5]}...>'
    
    @classmethod
    def get_active_code(cls):
        """Get the currently active access code"""
        return cls.query.filter_by(is_active=True).first()
    
    @classmethod
    def get_secret_path(cls):
        """Get the current secret path"""
        active = cls.get_active_code()
        return active.secret_path if active else 'access'
    
    @classmethod
    def verify_code(cls, entered_code):
        """Verify if entered code matches the active code"""
        active_code = cls.get_active_code()
        if active_code and active_code.code == entered_code:
            # Check if expired
            if active_code.expires_at and active_code.expires_at < datetime.utcnow():
                return False
            return True
        return False
    
    @classmethod
    def verify_path(cls, path):
        """Verify if the path matches the active secret path"""
        active = cls.get_active_code()
        return active and active.secret_path == path