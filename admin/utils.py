# utils.py - Updated helper functions for TallyVote system

from admin.models import TallyVote, Candidate
import os
import json
import pickle
from phe import paillier

# Helper function to check if election has been tallied
def check_if_tallied(election_id):
    """Check if election results have been officially tallied"""
    # Check if any tally records exist for this election
    return TallyVote.query.filter_by(election_id=election_id).first() is not None

# Helper function to get tally timestamp
def get_tally_timestamp(election_id):
    """Get the most recent tally timestamp for an election"""
    # Get the most recent tally record for this election
    tally_record = TallyVote.query.filter_by(
        election_id=election_id
    ).order_by(TallyVote.tally_timestamp.desc()).first()
    
    return tally_record.tally_timestamp if tally_record else None

# Helper function to get tally results for an election
def get_tally_results(election_id):
    """Get all tally results for an election"""
    return TallyVote.query.filter_by(election_id=election_id).all()

# Helper function to get candidate's tally result
def get_candidate_tally(candidate_id, election_id):
    """Get official tally result for a specific candidate"""
    tally = TallyVote.query.filter_by(
        candidate_id=candidate_id,
        election_id=election_id
    ).first()
    
    return tally.vote_count if tally else 0

# Helper function to save tally results
def save_tally_results(election_id, candidate_results, tally_timestamp=None):
    """Save official tally results to database"""
    from datetime import datetime
    from extensions import db
    
    if tally_timestamp is None:
        tally_timestamp = datetime.utcnow()
    
    try:
        # Delete any existing tally records for this election
        TallyVote.query.filter_by(election_id=election_id).delete()
        
        # Create new tally records
        for candidate_data in candidate_results:
            tally = TallyVote(
                election_id=election_id,
                candidate_id=candidate_data.get('candidate_id'),
                vote_count=candidate_data.get('vote_count', 0),
                tally_timestamp=tally_timestamp
            )
            db.session.add(tally)
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error saving tally results: {str(e)}")
        return False

# Helper function to get election summary with tally info
def get_election_tally_summary(election_id):
    """Get summary of election tally including total votes and candidates"""
    from extensions import db
    
    summary = db.session.query(
        db.func.count(TallyVote.id).label('total_candidates_tallied'),
        db.func.sum(TallyVote.vote_count).label('total_votes_tallied'),
        db.func.max(TallyVote.tally_timestamp).label('last_tally_timestamp')
    ).filter_by(election_id=election_id).first()
    
    return {
        'total_candidates_tallied': summary.total_candidates_tallied or 0,
        'total_votes_tallied': summary.total_votes_tallied or 0,
        'last_tally_timestamp': summary.last_tally_timestamp
    }

# Optional: Migration helper for old tally system
def migrate_old_tally_results(election_id):
    """Migrate from old candidate.tally_result to new TallyVote system"""
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    
    if not candidates:
        return False
    
    # Check if any candidate has old tally_result
    has_old_tally = False
    candidate_results = []
    
    for candidate in candidates:
        if hasattr(candidate, 'tally_result') and candidate.tally_result is not None:
            has_old_tally = True
            candidate_results.append({
                'candidate_id': candidate.id,
                'vote_count': candidate.tally_result
            })
    
    if has_old_tally and candidate_results:
        # Migrate to new system
        success = save_tally_results(election_id, candidate_results)
        if success:
            print(f"Migrated old tally results for election {election_id}")
            return True
    
    return False

# Key management functions (keep these if you still need them)
def load_election_public_key(election_id):
    """Load the public key for an election"""
    keys_dir = os.path.join(os.path.dirname(__file__), '..', 'keys')
    key_file = os.path.join(keys_dir, f'election_{election_id}_public.key')
    
    try:
        with open(key_file, 'rb') as f:
            key_data = pickle.load(f)
        return key_data
    except FileNotFoundError:
        return None

def load_election_private_key(election_id):
    """Load the private key for an election (for decryption)"""
    keys_dir = os.path.join(os.path.dirname(__file__), '..', 'keys')
    key_file = os.path.join(keys_dir, f'election_{election_id}_private.key')
    
    try:
        with open(key_file, 'rb') as f:
            key_data = pickle.load(f)
        return key_data
    except FileNotFoundError:
        return None

def decrypt_vote(encrypted_number, election_id):
    """Decrypt a single encrypted vote"""
    private_key = load_election_private_key(election_id)
    if private_key:
        return private_key.decrypt(encrypted_number)
    return None

# New helper for getting real-time vs tallied results
def get_candidate_vote_count(candidate_id, election_id, use_tallied=False):
    """Get vote count for a candidate, either from tally or real-time"""
    if use_tallied:
        return get_candidate_tally(candidate_id, election_id)
    else:
        # Import here to avoid circular imports
        from admin.routes import count_votes_for_candidate
        return count_votes_for_candidate(candidate_id, election_id)

# Helper to check if election can be tallied
def can_tally_election(election_id, force=False):
    """Check if election can be tallied (ended or force allowed)"""
    from models import Election
    import pytz
    from datetime import datetime
    
    election = Election.query.get(election_id)
    if not election:
        return False, "Election not found"
    
    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)
    
    if election.end_date.tzinfo is None:
        election_end = tz.localize(election.end_date)
    else:
        election_end = election.end_date
    
    if force or election_end <= now:
        return True, "Election can be tallied"
    else:
        return False, f"Election ends on {election_end.strftime('%b %d, %Y %I:%M %p')}"
    
from flask import request, session
from datetime import datetime
from admin.models import AuditLog, db

def log_audit(action, description=None):
    """Record an audit log entry"""
    
    # Get current user info from session
    user_id = session.get('user_id')
    role = session.get('role', 'admin')
    
    # Get IP address
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()
    
    # Create log entry
    log = AuditLog(
        user_id=user_id,
        role=role,
        action=action,
        description=description,
        ip_address=ip_address,
        timestamp=datetime.utcnow()
    )
    
    db.session.add(log)
    db.session.commit()
    
    return log



# Add to admin/utils.py or create a new file admin/sync_utils.py

def sync_registered_students_with_ctu():
    """
    Manual function to sync registered students with CTU master list.
    Can be called from admin dashboard or via a management command.
    """
    from admin.models import CtuStudent
    from student.models import Student, Vote
    from extensions import db
    
    # Get all active CTU students
    ctu_students = CtuStudent.query.all()
    ctu_student_numbers = {s.student_number for s in ctu_students}
    
    # Get all registered students
    registered_students = Student.query.all()
    
    deleted_count = 0
    kept_with_votes = 0
    
    for student in registered_students:
        if student.id_number not in ctu_student_numbers:
            # Check if student has votes
            votes = Vote.query.filter_by(student_id=student.id).count()
            
            if votes == 0:
                # Safe to delete
                db.session.delete(student)
                deleted_count += 1
            else:
                # Student has votes - keep for audit but maybe mark as inactive
                kept_with_votes += 1
                # You could add a status field to mark them as graduated
                # student.status = 'graduated'
                # db.session.add(student)
    
    db.session.commit()
    
    return {
        'deleted': deleted_count,
        'kept_with_votes': kept_with_votes
    }





from flask import url_for
from flask_mail import Message
from extensions import mail

def send_admin_device_verification_email(admin, device, token):
    """Send device verification email to admin"""
    verify_url = url_for('admin.verify_admin_device', token=token, _external=True)
    
    msg = Message(
        subject="🔐 Verify New Device Login - COMELEC Admin",
        recipients=[admin.email],
        html=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6fb;">
            <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #ff9900, #ff5500); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">🔐 New Device Login</h1>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 30px;">
                    <p style="font-size: 16px; color: #1f2937; margin-bottom: 20px;">Hello <strong>{admin.first_name} {admin.last_name}</strong>,</p>
                    
                    <p style="font-size: 16px; color: #4b5563; line-height: 1.6; margin-bottom: 20px;">
                        We detected a login to your COMELEC Admin account from a new device:
                    </p>
                    
                    <!-- Device Info Card -->
                    <div style="background: #f8fafc; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #e2e8f0;">
                        <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                            <div style="background: #eef2ff; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                                <span style="font-size: 24px;">💻</span>
                            </div>
                            <div style="flex: 1;">
                                <p style="margin: 0 0 5px 0; color: #1f2937; font-weight: 600;">{device.device_name}</p>
                                <p style="margin: 0; color: #6b7280; font-size: 14px;">IP: {device.ip_address}</p>
                                <p style="margin: 0; color: #6b7280; font-size: 14px;">Browser: {device.browser}</p>
                            </div>
                        </div>
                    </div>
                    
                    <p style="font-size: 16px; color: #4b5563; line-height: 1.6; margin-bottom: 25px;">
                        If this was you, click the button below to verify this device. This will add it to your trusted devices for 30 days.
                    </p>
                    
                    <!-- Verify Button -->
                    <div style="text-align: center; margin: 35px 0;">
                        <a href="{verify_url}" style="display: inline-block; background: linear-gradient(135deg, #ff9900, #ff5500); color: white; text-decoration: none; padding: 15px 40px; border-radius: 40px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 10px rgba(255, 85, 0, 0.3);">✅ Yes, It's Me</a>
                    </div>
                    
                    <p style="font-size: 16px; color: #4b5563; line-height: 1.6; margin-bottom: 25px;">
                        If you didn't attempt to log in, please secure your account immediately.
                    </p>
                    
                    <!-- Security Notice -->
                    <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; border-radius: 8px; margin: 25px 0;">
                        <p style="margin: 0; color: #856404; font-size: 14px;">
                            <strong>⚠️ Security Notice:</strong> This link will expire in 15 minutes. 
                            If you didn't request this, please change your password immediately.
                        </p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background: #f1f5f9; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="margin: 0; color: #64748b; font-size: 14px;">COMELEC Admin - CTU Moalboal</p>
                    <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 12px;">This is an automated message, please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
    )
    
    mail.send(msg)



from flask import url_for
from flask_mail import Message
from extensions import mail

def send_device_removal_confirmation(admin, device, token):
    """Send email confirmation for device removal"""
    confirm_url = url_for('admin.confirm_remove_device', token=token, _external=True)
    cancel_url = url_for('admin.cancel_remove_device', token=token, _external=True)
    
    msg = Message(
        subject="🔐 Confirm Device Removal - COMELEC Admin",
        recipients=[admin.email],
        html=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6fb;">
            <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #ef4444, #dc2626); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">🔐 Confirm Device Removal</h1>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 30px;">
                    <p style="font-size: 16px; color: #1f2937; margin-bottom: 20px;">Hello <strong>{admin.first_name} {admin.last_name}</strong>,</p>
                    
                    <p style="font-size: 16px; color: #4b5563; line-height: 1.6; margin-bottom: 20px;">
                        We received a request to remove this trusted device from your account:
                    </p>
                    
                    <!-- Device Info Card -->
                    <div style="background: #f8fafc; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #e2e8f0;">
                        <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                            <div style="background: #fee2e2; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                                <span style="font-size: 24px;">💻</span>
                            </div>
                            <div style="flex: 1;">
                                <p style="margin: 0 0 5px 0; color: #1f2937; font-weight: 600;">{device.device_name or 'Unknown Device'}</p>
                                <p style="margin: 0; color: #6b7280; font-size: 14px;">IP: {device.ip_address}</p>
                                <p style="margin: 0; color: #6b7280; font-size: 14px;">Browser: {device.browser}</p>
                                <p style="margin: 0; color: #6b7280; font-size: 14px;">Trusted until: {device.expires_at.strftime('%Y-%m-%d %H:%M') if device.expires_at else 'N/A'}</p>
                            </div>
                        </div>
                    </div>
                    
                    <p style="font-size: 16px; color: #4b5563; line-height: 1.6; margin-bottom: 25px;">
                        If you want to remove this device from your trusted devices list, click the button below:
                    </p>
                    
                    <!-- Confirm Button -->
                    <div style="text-align: center; margin: 35px 0;">
                        <a href="{confirm_url}" style="display: inline-block; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; text-decoration: none; padding: 15px 40px; border-radius: 40px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 10px rgba(220, 38, 38, 0.3);">✅ Yes, Remove Device</a>
                    </div>
                    
                    <!-- Cancel Link -->
                    <div style="text-align: center; margin: 20px 0;">
                        <a href="{cancel_url}" style="color: #6b7280; text-decoration: none; font-size: 14px;">❌ No, keep this device</a>
                    </div>
                    
                    <p style="font-size: 16px; color: #4b5563; line-height: 1.6; margin-bottom: 25px;">
                        If you didn't request this, please secure your account immediately.
                    </p>
                    
                    <!-- Security Notice -->
                    <div style="background: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; border-radius: 8px; margin: 25px 0;">
                        <p style="margin: 0; color: #991b1b; font-size: 14px;">
                            <strong>⚠️ Security Notice:</strong> This link will expire in 15 minutes. 
                            If you didn't request this, someone may be trying to access your account.
                        </p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background: #f1f5f9; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="margin: 0; color: #64748b; font-size: 14px;">COMELEC Admin - CTU Moalboal</p>
                    <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 12px;">This is an automated message, please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
    )
    
    mail.send(msg)



    from flask import url_for
from flask_mail import Message
from extensions import mail
from datetime import datetime

def send_device_removal_confirmation(admin, device, token):
    """Send email confirmation for device removal"""
    confirm_url = url_for('admin.confirm_remove_device', token=token, _external=True)
    cancel_url = url_for('admin.cancel_remove_device', token=token, _external=True)
    
    msg = Message(
        subject="🔐 Confirm Device Removal - COMELEC Admin",
        recipients=[admin.email],
        html=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6fb;">
            <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #ef4444, #dc2626); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">🔐 Confirm Device Removal</h1>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 30px;">
                    <p style="font-size: 16px; color: #1f2937; margin-bottom: 20px;">Hello <strong>{admin.first_name} {admin.last_name}</strong>,</p>
                    
                    <p style="font-size: 16px; color: #4b5563; line-height: 1.6; margin-bottom: 20px;">
                        We received a request to remove this trusted device from your account:
                    </p>
                    
                    <!-- Device Info Card -->
                    <div style="background: #f8fafc; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #e2e8f0;">
                        <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                            <div style="background: #fee2e2; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                                <span style="font-size: 24px;">💻</span>
                            </div>
                            <div style="flex: 1;">
                                <p style="margin: 0 0 5px 0; color: #1f2937; font-weight: 600;">{device.device_name or 'Unknown Device'}</p>
                                <p style="margin: 0; color: #6b7280; font-size: 14px;">IP: {device.ip_address}</p>
                                <p style="margin: 0; color: #6b7280; font-size: 14px;">Browser: {device.browser}</p>
                                <p style="margin: 0; color: #6b7280; font-size: 14px;">Trusted until: {device.expires_at.strftime('%Y-%m-%d %H:%M') if device.expires_at else 'N/A'}</p>
                            </div>
                        </div>
                    </div>
                    
                    <p style="font-size: 16px; color: #4b5563; line-height: 1.6; margin-bottom: 25px;">
                        If you want to remove this device from your trusted devices list, click the button below:
                    </p>
                    
                    <!-- Confirm Button -->
                    <div style="text-align: center; margin: 35px 0;">
                        <a href="{confirm_url}" style="display: inline-block; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; text-decoration: none; padding: 15px 40px; border-radius: 40px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 10px rgba(220, 38, 38, 0.3);">✅ Yes, Remove Device</a>
                    </div>
                    
                    <!-- Cancel Link -->
                    <div style="text-align: center; margin: 20px 0;">
                        <a href="{cancel_url}" style="color: #6b7280; text-decoration: none; font-size: 14px;">❌ No, keep this device</a>
                    </div>
                    
                    <p style="font-size: 16px; color: #4b5563; line-height: 1.6; margin-bottom: 25px;">
                        If you didn't request this, please secure your account immediately.
                    </p>
                    
                    <!-- Security Notice -->
                    <div style="background: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; border-radius: 8px; margin: 25px 0;">
                        <p style="margin: 0; color: #991b1b; font-size: 14px;">
                            <strong>⚠️ Security Notice:</strong> This link will expire in 15 minutes. 
                            If you didn't request this, someone may be trying to access your account.
                        </p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background: #f1f5f9; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="margin: 0; color: #64748b; font-size: 14px;">COMELEC Admin - CTU Moalboal</p>
                    <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 12px;">This is an automated message, please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
    )
    
    mail.send(msg)





def send_admin_new_device_email(admin, device):
    """Send email when new device is detected"""
    token = device.generate_verification_token()
    db.session.commit()
    
    confirm_url = url_for('admin.confirm_admin_device', token=token, _external=True)
    deny_url = url_for('admin.reject_admin_device', token=token, _external=True)
    
    msg = Message(
        subject="🔐 New Device Login Verification - COMELEC Admin",
        recipients=[admin.email],
        html=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6fb;">
            <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #ff9900, #ff5500); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">🔐 New Device Login</h1>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 30px;">
                    <p style="font-size: 16px; color: #1f2937; margin-bottom: 20px;">Hello <strong>{admin.first_name} {admin.last_name}</strong>,</p>
                    
                    <p style="font-size: 16px; color: #4b5563; line-height: 1.6; margin-bottom: 20px;">
                        We detected a login to your COMELEC Admin account from a new device:
                    </p>
                    
                    <!-- Device Info Card -->
                    <div style="background: #f8fafc; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #e2e8f0;">
                        <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                            <div style="background: #eef2ff; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                                <span style="font-size: 24px;">💻</span>
                            </div>
                            <div style="flex: 1;">
                                <p style="margin: 0 0 5px 0; color: #1f2937; font-weight: 600;">{device.device_name}</p>
                                <p style="margin: 0; color: #6b7280; font-size: 14px;">IP: {device.ip_address}</p>
                                <p style="margin: 0; color: #6b7280; font-size: 14px;">Browser: {device.browser}</p>
                            </div>
                        </div>
                    </div>
                    
                    <p style="font-size: 16px; color: #4b5563; line-height: 1.6; margin-bottom: 25px;">
                        If this was you, click the button below to verify this device. This will add it to your trusted devices for 30 days.
                    </p>
                    
                    <!-- Two Buttons -->
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin: 25px auto;">
                        <tr>
                            <td style="padding: 5px;">
                                <a href="{confirm_url}" style="
                                    display: inline-block;
                                    padding: 12px 25px;
                                    background: linear-gradient(135deg, #10b981, #059669);
                                    color: #ffffff;
                                    text-decoration: none;
                                    border-radius: 40px;
                                    font-weight: 600;
                                    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
                                ">✅ Yes, it's me</a>
                            </td>
                            <td style="padding: 5px;">
                                <a href="{deny_url}" style="
                                    display: inline-block;
                                    padding: 12px 25px;
                                    background: linear-gradient(135deg, #ef4444, #dc2626);
                                    color: #ffffff;
                                    text-decoration: none;
                                    border-radius: 40px;
                                    font-weight: 600;
                                    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
                                ">❌ No, it's not me</a>
                            </td>
                        </tr>
                    </table>
                    
                    <!-- Security Notice -->
                    <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; border-radius: 8px; margin: 25px 0;">
                        <p style="margin: 0; color: #856404; font-size: 14px;">
                            <strong>⚠️ Security Notice:</strong> This link will expire in 15 minutes. 
                            If you didn't request this, click "No, it's not me" immediately.
                        </p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background: #f1f5f9; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="margin: 0; color: #64748b; font-size: 14px;">COMELEC Admin - CTU Moalboal</p>
                    <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 12px;">This is an automated message, please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
    )
    
    try:
        mail.send(msg)
        print(f"✅ New device verification email sent to {admin.email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")