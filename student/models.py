# student/models.py - CORRECTED VERSION

# Use ONLY ONE db import
from extensions import db  # ✅ This imports the shared db instance
from flask_login import UserMixin
from datetime import datetime
import json
from phe import paillier
import pickle
import base64
import pytz

# DO NOT CREATE ANOTHER db INSTANCE HERE!
# Remove this line: db = SQLAlchemy()

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
    course = db.Column(db.String(100))  # backward compatibility
    
    # relational fields
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    year_level_id = db.Column(db.Integer, db.ForeignKey('year_levels.id'), nullable=True)
    
    birth_date = db.Column(db.Date)
    id_number = db.Column(db.String(50), unique=True)
    
    # BIOMETRIC / WEBAUTHN
    passkey_id = db.Column(db.LargeBinary)
    public_key = db.Column(db.LargeBinary)
    sign_count = db.Column(db.Integer, default=0)
    current_challenge = db.Column(db.LargeBinary)
    
    # 🔐 Forgot Password Token
    reset_token = db.Column(db.String(100), nullable=True)
    user_type = "student"
    
    # Relationships
    department = db.relationship('Department', backref='students')
    course_rel = db.relationship('Course', backref='students')



class Vote(db.Model):
    __tablename__ = "votes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    encrypted_vote = db.Column(db.Text, nullable=False)  # Or db.LONGTEXT
    
    # NEW: Add finder_hash for vote verification
    finder_hash = db.Column(db.String(256), unique=True, nullable=True)
    
    cast_timestamp = db.Column(db.DateTime, nullable=True)
    recorded_timestamp = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    student = db.relationship("Student", backref="student_votes")
    election = db.relationship("Election", backref="election_votes")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def get_encrypted_vote_as_list(self, public_key):
        """Helper method to get encrypted vote as list of EncryptedNumbers"""
        vote_list = json.loads(self.encrypted_vote)
        enc_numbers = []
        for enc_dict in vote_list:
            enc_num = paillier.EncryptedNumber(
                public_key,
                int(enc_dict["ciphertext"]),
                int(enc_dict["exponent"])
            )
            enc_numbers.append(enc_num)
        return enc_numbers
    
    @staticmethod
    def encrypt_vote_for_candidates(candidate_ids, selected_candidate_id, public_key):
        """Create one-hot encrypted vote vector for all candidates"""
        vote_vector = [1 if candidate_id == selected_candidate_id else 0 
                      for candidate_id in candidate_ids]
        
        enc_vote = [public_key.encrypt(x) for x in vote_vector]
        
        vote_json = json.dumps([
            {"ciphertext": str(e.ciphertext()), "exponent": e.exponent} 
            for e in enc_vote
        ])
        
        return vote_json
    
    @staticmethod
    def get_total_votes_for_election(election_id, candidate_ids, public_key):
        """Sum all encrypted votes for an election"""
        votes = Vote.query.filter_by(election_id=election_id).all()
        
        if not votes:
            return [0] * len(candidate_ids)
        
        total = [public_key.encrypt(0) for _ in candidate_ids]
        
        for vote in votes:
            enc_votes = vote.get_encrypted_vote_as_list(public_key)
            for i in range(len(total)):
                total[i] = total[i] + enc_votes[i]
        
        return total
    
    @property
    def cast_timestamp_manila(self):
        """Get cast_timestamp in Manila time (stored as Manila time)"""
        if self.cast_timestamp:
            local_tz = pytz.timezone("Asia/Manila")
            
            # Cast timestamp is stored as Manila time (no conversion needed)
            if self.cast_timestamp.tzinfo is None:
                # Just localize it to Manila (since it's already Manila time)
                return local_tz.localize(self.cast_timestamp)
            return self.cast_timestamp.astimezone(local_tz)
        return None
    
    @property
    def recorded_timestamp_manila(self):
        """Get recorded_timestamp in Manila time (converted from UTC)"""
        if self.recorded_timestamp:
            local_tz = pytz.timezone("Asia/Manila")
            utc_tz = pytz.UTC
            
            # recorded_timestamp is always UTC (from datetime.utcnow())
            if self.recorded_timestamp.tzinfo is None:
                # First tell Python it's UTC
                utc_dt = utc_tz.localize(self.recorded_timestamp)
                # Then convert to Manila
                return utc_dt.astimezone(local_tz)
            return self.recorded_timestamp.astimezone(local_tz)
        return None
    
    @property
    def created_at_manila(self):
        """Get created_at in Manila time (converted from UTC)"""
        if self.created_at:
            local_tz = pytz.timezone("Asia/Manila")
            utc_tz = pytz.UTC
            
            # created_at is always UTC (from default=datetime.utcnow)
            if self.created_at.tzinfo is None:
                utc_dt = utc_tz.localize(self.created_at)
                return utc_dt.astimezone(local_tz)
            return self.created_at.astimezone(local_tz)
        return None
    
    @property
    def recorded_timestamp_formatted(self):
        """Get formatted recorded timestamp in Manila time"""
        manila_time = self.recorded_timestamp_manila
        if manila_time:
            return manila_time.strftime("%I:%M:%S %p")
        return None
    
    @property
    def cast_timestamp_formatted(self):
        """Get formatted cast timestamp in Manila time"""
        manila_time = self.cast_timestamp_manila
        if manila_time:
            return manila_time.strftime("%I:%M:%S %p")
        return None
    
    @property
    def created_at_formatted(self):
        """Get formatted created at in Manila time"""
        manila_time = self.created_at_manila
        if manila_time:
            return manila_time.strftime("%I:%M:%S %p")
        return None
    
    def get_all_times(self):
        """Get all times in Manila time as formatted strings"""
        return {
            'cast': self.cast_timestamp_formatted,
            'recorded': self.recorded_timestamp_formatted,
            'created': self.created_at_formatted,
            'cast_full': self.cast_timestamp_manila.strftime("%Y-%m-%d %I:%M:%S %p") if self.cast_timestamp_manila else None,
            'recorded_full': self.recorded_timestamp_manila.strftime("%Y-%m-%d %I:%M:%S %p") if self.recorded_timestamp_manila else None,
            'created_full': self.created_at_manila.strftime("%Y-%m-%d %I:%M:%S %p") if self.created_at_manila else None
        }
    

    def get_secret_nonce(self):
        """Extract the secret nonce from finder_hash"""
        if not self.finder_hash:
            return 'N/A'
        
        try:
            # Try to parse as JSON first
            finder_data = json.loads(self.finder_hash)
            # Check if it's the new format with 'nonce' field
            if isinstance(finder_data, dict) and 'nonce' in finder_data:
                return finder_data['nonce']
            # If it's a list or something else, return as is
            return str(finder_data)
        except:
            # If it's not JSON, return the raw string (might be the old format)
            return self.finder_hash


class TrustedDevice(db.Model):
    __tablename__ = 'trusted_devices'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    device_fingerprint = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(50))
    browser = db.Column(db.String(255))
    device_name = db.Column(db.String(255))
    trusted = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    verification_token = db.Column(db.String(100), nullable=True)
    verification_sent_at = db.Column(db.DateTime, nullable=True)
    
    student = db.relationship('Student', backref='trusted_devices')




class DeletionRequest(db.Model):
    __tablename__ = 'deletion_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum('pending', 'approved', 'rejected', 'cancelled'), default='pending')
    admin_notes = db.Column(db.Text)
    processed_date = db.Column(db.DateTime)
    processed_by = db.Column(db.Integer, db.ForeignKey('admins.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', backref=db.backref('deletion_requests', lazy=True))
    admin = db.relationship('Admin', foreign_keys=[processed_by])