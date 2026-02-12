# student/models.py - CORRECTED VERSION

# Use ONLY ONE db import
from extensions import db  # ✅ This imports the shared db instance
from flask_login import UserMixin
from datetime import datetime
import json
from phe import paillier
import pickle
import base64

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
    
    cast_timestamp = db.Column(db.DateTime, nullable=True)
    recorded_timestamp = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    student = db.relationship("Student", backref="student_votes")
    election = db.relationship("Election", backref="election_votes")
    # Note: NO candidate relationship anymore
    
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
        # Create one-hot vector: 1 for selected candidate, 0 for others
        vote_vector = [1 if candidate_id == selected_candidate_id else 0 
                      for candidate_id in candidate_ids]
        
        # Encrypt each element
        enc_vote = [public_key.encrypt(x) for x in vote_vector]
        
        # Serialize for storage
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
        
        # Initialize sum with encrypted zeros
        total = [public_key.encrypt(0) for _ in candidate_ids]
        
        # Add each vote using homomorphic addition
        for vote in votes:
            enc_votes = vote.get_encrypted_vote_as_list(public_key)
            for i in range(len(total)):
                total[i] = total[i] + enc_votes[i]
        
        return total


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