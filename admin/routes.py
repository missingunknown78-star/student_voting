from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session, jsonify, Response
from extensions import db, bcrypt
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime
from functools import wraps
from admin.models import Admin, Candidate, Position, Election, Announcement, Department, Course, CtuStudent, TallyVote, ElectionPosition
from student.models import Student, Vote
import mysql.connector
from settings import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
import pytz
from werkzeug.utils import secure_filename
import os
import logging
import time
import pyotp
from datetime import timedelta
from sqlalchemy import or_
from io import BytesIO
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment
from werkzeug.security import generate_password_hash
import json
from phe import paillier
import pickle
from .utils import check_if_tallied, get_tally_timestamp
from flask import request, render_template, send_file
from sqlalchemy import or_, desc
from datetime import datetime
import io
import csv
from admin.models import AuditLog, Setting
from admin.utils import log_audit
import pandas as pd
from admin.models import AdminTrustedDevice
from flask import make_response
from datetime import datetime
import pytz
# Add this near your other imports





try:
    from admin.models import TallyVote
    TALLY_VOTE_AVAILABLE = True
except ImportError:
    TALLY_VOTE_AVAILABLE = False
    print("Note: TallyVote model not found. Official tally features disabled.")



# ---------------------- Blueprint ---------------------- #
admin_bp = Blueprint('admin', __name__, template_folder='templates', static_folder='static')

# ---------------------- PHE Helper Functions ---------------------- #
def get_encryption_keys():
    """Get Paillier encryption keys"""
    key_dir = "keys"
    os.makedirs(key_dir, exist_ok=True)
    
    public_key_path = os.path.join(key_dir, "public_key.pkl")
    private_key_path = os.path.join(key_dir, "private_key.pkl")
    
    if os.path.exists(public_key_path) and os.path.exists(private_key_path):
        with open(public_key_path, 'rb') as f:
            public_key = pickle.load(f)
        with open(private_key_path, 'rb') as f:
            private_key = pickle.load(f)
    else:
        public_key, private_key = paillier.generate_paillier_keypair()
        with open(public_key_path, 'wb') as f:
            pickle.dump(public_key, f)
        with open(private_key_path, 'wb') as f:
            pickle.dump(private_key, f)
    
    return public_key, private_key

# Initialize keys
public_key, private_key = get_encryption_keys()

def deserialize_encrypted_vote(encrypted_data):
    """Deserialize stored encrypted vote"""
    if not encrypted_data:
        return []
    
    data = json.loads(encrypted_data)
    return [
        paillier.EncryptedNumber(
            public_key,
            int(item["ciphertext"]),
            int(item["exponent"])
        )
        for item in data
    ]

def count_votes_for_candidate(candidate_id, election_id):
    """Count votes for a specific candidate in an election using PHE"""
    # Get all votes for this election
    votes = Vote.query.filter_by(election_id=election_id).all()
    
    if not votes:
        return 0
    
    # Get all candidates in this election
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    candidate_ids = [c.id for c in candidates]
    
    # Find the index of our target candidate
    try:
        candidate_index = candidate_ids.index(candidate_id)
    except ValueError:
        return 0  # Candidate not found in this election
    
    # Initialize encrypted sum
    total_encrypted = public_key.encrypt(0)
    
    # Add all votes homomorphically
    for vote in votes:
        enc_votes = deserialize_encrypted_vote(vote.encrypted_vote)
        if candidate_index < len(enc_votes):
            total_encrypted = total_encrypted + enc_votes[candidate_index]
    
    # Decrypt the total for this candidate
    return private_key.decrypt(total_encrypted)

def get_all_voters_for_election(election_id):
    """Get all unique voters for an election"""
    votes = Vote.query.filter_by(election_id=election_id).all()
    return list(set(vote.student_id for vote in votes))

# ---------------------- Secure Admin Required Decorator ---------------------- #
# Configure logging for unauthorized attempts
logging.basicConfig(filename='admin_access.log', level=logging.WARNING,
                    format='%(asctime)s - %(message)s')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        attempts = session.get(f'admin_attempts_{ip}', 0)
        cooldown = session.get(f'admin_cooldown_{ip}', 0)

        # Check cooldown
        if time.time() < cooldown:
            flash(f"Too many failed attempts. Try again in {int(cooldown - time.time())} seconds.", "admin-warning")
            return redirect(url_for('admin.login'))

        # Check if user is authenticated and has role 'Admin'
        if not current_user.is_authenticated or getattr(current_user, 'role', None) != 'Admin':
            logging.warning(f"Unauthorized admin access attempt from IP: {ip}")

            # Increment failed attempts
            attempts += 1
            session[f'admin_attempts_{ip}'] = attempts

            # Start cooldown if max attempts reached
            if attempts >= MAX_ATTEMPTS:
                session[f'admin_cooldown_{ip}'] = time.time() + COOLDOWN_TIME
                session[f'admin_attempts_{ip}'] = 0
                flash("Too many failed attempts. Admin login temporarily locked.", "admin-warning")
            else:
                flash("Please log in as admin to access this page.", "admin-warning")

            return redirect(url_for('admin.login'))

        # Reset failed attempts on successful admin access
        session[f'admin_attempts_{ip}'] = 0
        session[f'admin_cooldown_{ip}'] = 0

        return f(*args, **kwargs)
    return decorated_function

 
def count_unique_voters(election_id):
    """Count the number of unique students who voted in an election"""
    return db.session.query(Vote.student_id).filter_by(
        election_id=election_id
    ).distinct().count()



def get_all_school_years():
    """Get all unique school years from elections"""
    try:
        elections = Election.query.order_by(Election.start_date.asc()).all()
        school_years = set()
        
        for election in elections:
            if election.start_date:
                year = election.start_date.year
                school_years.add(f"{year}-{year+1}")
        
        # Sort in descending order (newest first)
        return sorted(list(school_years), reverse=True)
    except:
        return []



# ------------------- Configuration ------------------- #
MAX_ATTEMPTS = 3          # max allowed failed username/password attempts
COOLDOWN_TIME = 300       # cooldown in seconds (5 minutes)
MAX_2FA_ATTEMPTS = 5      # max allowed failed 2FA attempts
TWO_FA_COOLDOWN = 300     # cooldown for 2FA in seconds

# ------------------- Admin Login Route ------------------- #
# ------------------- Admin Login Route ------------------- #
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    ip = request.remote_addr
    attempts = session.get(f'login_attempts_{ip}', 0)
    cooldown = session.get(f'login_cooldown_{ip}', 0)

    # Redirect already logged-in admins to dashboard
    if current_user.is_authenticated and getattr(current_user, 'role', None) == 'Admin':
        return redirect(url_for('admin.dashboard'))

    # Check cooldown
    if time.time() < cooldown:
        remaining = int(cooldown - time.time())
        error = f'Too many failed attempts. Try again in {remaining} seconds.'
        return render_template('admin_login.html', error=error)

    error = None

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        admin = Admin.query.filter_by(username=username).first()

        if admin and bcrypt.check_password_hash(admin.password, password) and admin.role == 'Admin':
            # Reset failed attempts
            session[f'login_attempts_{ip}'] = 0
            session[f'login_cooldown_{ip}'] = 0
            session.permanent = True

            # ---------- AUDIT LOG: Successful login attempt ----------
            log_audit(
                action='LOGIN_SUCCESS',
                description=f"Admin user '{username}' logged in successfully from IP: {ip}"
            )

            # Redirect to 2FA setup if no totp_secret
            if not getattr(admin, 'totp_secret', None):
                session['pre_2fa_admin_id'] = admin.id
                # ---------- AUDIT LOG: 2FA not set up ----------
                log_audit(
                    action='2FA_REQUIRED',
                    description=f"Admin user '{username}' redirected to 2FA setup - TOTP secret not configured"
                )
                return redirect(url_for('admin.setup_2fa'))
            else:
                session['pre_2fa_admin_id'] = admin.id
                # ---------- AUDIT LOG: 2FA verification required ----------
                log_audit(
                    action='2FA_VERIFICATION',
                    description=f"Admin user '{username}' redirected to 2FA verification"
                )
                return redirect(url_for('admin.verify_2fa'))

        else:
            # Increment failed attempts
            attempts += 1
            session[f'login_attempts_{ip}'] = attempts

            # ---------- AUDIT LOG: Failed login attempt ----------
            log_audit(
                action='LOGIN_FAILED',
                description=f"Failed login attempt for username '{username}' from IP: {ip} (Attempt {attempts} of {MAX_ATTEMPTS})"
            )

            if attempts >= MAX_ATTEMPTS:
                session[f'login_cooldown_{ip}'] = time.time() + COOLDOWN_TIME
                session[f'login_attempts_{ip}'] = 0
                error = 'Invalid credentials. Admin login temporarily locked.'
                
                # ---------- AUDIT LOG: Account temporarily locked ----------
                log_audit(
                    action='ACCOUNT_LOCKED',
                    description=f"Admin login temporarily locked for IP: {ip} due to {MAX_ATTEMPTS} failed attempts. Cooldown: {COOLDOWN_TIME} seconds"
                )
            else:
                error = f'Invalid username or password. Attempt {attempts} of {MAX_ATTEMPTS}.'

    return render_template('admin_login.html', error=error)



# ------------------- Admin 2FA Verification ------------------- #
@admin_bp.route('/2fa/verify', methods=['GET', 'POST'])
def verify_2fa():
    # Check if user is in pre-2fa session
    if 'pre_2fa_admin_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('admin.login'))

    admin_id = session['pre_2fa_admin_id']
    admin = Admin.query.get(admin_id)
    if not admin:
        session.pop('pre_2fa_admin_id', None)
        return redirect(url_for('admin.login'))

    ip = request.remote_addr
    attempts = session.get(f'2fa_attempts_{ip}', 0)
    cooldown = session.get(f'2fa_cooldown_{ip}', 0)

    # Check cooldown
    if time.time() < cooldown:
        remaining = int(cooldown - time.time())
        error = f"Too many 2FA attempts. Try again in {remaining} seconds."
        return render_template('admin_2fa_verify.html', error=error)

    error = None
    
    if request.method == 'POST':
        # Check if user has TOTP secret
        if not admin.totp_secret:
            error = "2FA not properly set up. Please setup 2FA first."
            return render_template('admin_2fa_verify.html', error=error)

        totp = pyotp.TOTP(admin.totp_secret)
        code = request.form.get('code')
        
        if totp.verify(code):
            # Success: log in the user
            login_user(admin)
            session.permanent = True
            print(f"✅ User {admin.username} logged in after 2FA")

            # ===== DEVICE FINGERPRINT AND TRUST CHECK =====
            device_info = AdminTrustedDevice.get_device_info(request)
            
            # IMPORTANT: Use the EXACT same method as the model's generate_fingerprint()
            # Format: admin_id + ip_address + user_agent + browser + os
            fingerprint_data = f"{admin.id}{device_info['ip_address']}{device_info['user_agent']}{device_info['browser']}{device_info['os']}"
            device_fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()

            print(f"🔑 Generated fingerprint: {device_fingerprint[:20]}...")
            print(f"📊 Data used: admin_id={admin.id}, ip={device_info['ip_address']}, browser={device_info['browser']}, os={device_info['os']}")
            
            # Store in session
            session['admin_device_fingerprint'] = device_fingerprint
            
            # 🔐 CHECK IF THIS IS A NEW DEVICE
            trusted_device = AdminTrustedDevice.query.filter_by(
                admin_id=admin.id,
                device_fingerprint=device_fingerprint,
                trusted=True
            ).first()
            
            print(f"🔍 Trusted device found: {trusted_device is not None}")
            
            # Check if ANY trusted device exists for this admin
            any_trusted_device = AdminTrustedDevice.query.filter_by(
                admin_id=admin.id,
                trusted=True
            ).first()
            
            print(f"🔍 Any trusted device exists: {any_trusted_device is not None}")
            
            if not trusted_device:
                print("📱 This is a NEW device")
                # This is a new/untrusted device
                if any_trusted_device:
                    print("📧 Existing trusted devices found → Sending verification email")
                    # There are existing trusted devices → need verification
                    
                    # Save device as untrusted
                    new_device = AdminTrustedDevice(
                        admin_id=admin.id,
                        device_name=f"{device_info['browser']} on {device_info['os']}",
                        ip_address=device_info['ip_address'],
                        user_agent=device_info['user_agent'],
                        browser=device_info['browser'],
                        os=device_info['os'],
                        device_type=device_info['device_type'],
                        trusted=False
                    )
                    # Set fingerprint using the same method
                    new_device.device_fingerprint = device_fingerprint
                    db.session.add(new_device)
                    db.session.commit()
                    
                    # Send verification email
                    from admin.utils import send_admin_new_device_email
                    send_admin_new_device_email(admin, new_device)
                    
                    # Store in session for verification page
                    session['pending_admin_login'] = admin.id
                    session['pending_device_fp'] = device_fingerprint
                    
                    # Logout temporarily (they'll log in after verification)
                    from flask_login import logout_user
                    logout_user()
                    
                    # Cleanup 2FA session
                    session.pop('pre_2fa_admin_id', None)
                    session.pop(f'2fa_attempts_{ip}', None)
                    session.pop(f'2fa_cooldown_{ip}', None)
                    
                    print("↩️ Redirecting to verification page")
                    flash("New device detected. Please check your email to verify this device.", "warning")
                    return redirect(url_for('admin.verify_device_page'))
                else:
                    print("🎉 FIRST device ever - auto trusting it")
                    # FIRST device ever - auto trust it
                    new_device = AdminTrustedDevice(
                        admin_id=admin.id,
                        device_name=f"{device_info['browser']} on {device_info['os']}",
                        ip_address=device_info['ip_address'],
                        user_agent=device_info['user_agent'],
                        browser=device_info['browser'],
                        os=device_info['os'],
                        device_type=device_info['device_type'],
                        trusted=True,
                        expires_at=datetime.utcnow() + timedelta(days=30)
                    )
                    # Set fingerprint using the same method
                    new_device.device_fingerprint = device_fingerprint
                    db.session.add(new_device)
                    db.session.commit()
                    
                    # Cleanup session
                    session.pop('pre_2fa_admin_id', None)
                    session.pop(f'2fa_attempts_{ip}', None)
                    session.pop(f'2fa_cooldown_{ip}', None)
                    
                    print("🏠 Redirecting to dashboard (first device)")
                    flash("2FA verified successfully! This device has been added to trusted devices.", "success")
                    return redirect(url_for('admin.dashboard'))
            else:
                print("✅ Device ALREADY TRUSTED - direct to dashboard")
                # Device already trusted - just update last used
                trusted_device.update_last_used()
                # Update device info to keep it current
                trusted_device.ip_address = device_info['ip_address']
                trusted_device.user_agent = device_info['user_agent']
                trusted_device.browser = device_info['browser']
                trusted_device.os = device_info['os']
                trusted_device.device_type = device_info['device_type']
                trusted_device.device_name = f"{device_info['browser']} on {device_info['os']}"
                db.session.commit()
                
                # Cleanup session
                session.pop('pre_2fa_admin_id', None)
                session.pop(f'2fa_attempts_{ip}', None)
                session.pop(f'2fa_cooldown_{ip}', None)
                
                print("🏠 Redirecting to dashboard (trusted device)")
                flash("2FA verified successfully! Welcome, Admin.", "success")
                return redirect(url_for('admin.dashboard'))
        else:
            # Increment failed attempts
            attempts += 1
            session[f'2fa_attempts_{ip}'] = attempts

            if attempts >= MAX_2FA_ATTEMPTS:
                session[f'2fa_cooldown_{ip}'] = time.time() + TWO_FA_COOLDOWN
                session[f'2fa_attempts_{ip}'] = 0
                error = "Too many invalid codes. 2FA temporarily locked."
            else:
                error = f"Invalid code. Attempt {attempts} of {MAX_2FA_ATTEMPTS}."

    return render_template('admin_2fa_verify.html', error=error)

# ------------------- 2FA Secret Generation ------------------- #
def generate_2fa_secret(admin):
    if not admin.totp_secret:  # Simpler condition
        admin.totp_secret = pyotp.random_base32()
        db.session.commit()
        
        log_audit(
            action='2FA_SECRET_GENERATED',
            description=f"2FA secret generated for admin user '{admin.username}'"
        )
        
    return admin.totp_secret



# ------------------- Admin 2FA Setup ------------------- #
@admin_bp.route('/2fa/setup', methods=['GET', 'POST'])
def setup_2fa():
    # Check if user is in pre-2fa session
    if 'pre_2fa_admin_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('admin.login'))
    
    admin_id = session['pre_2fa_admin_id']
    admin = Admin.query.get(admin_id)
    
    if not admin:
        session.pop('pre_2fa_admin_id', None)
        return redirect(url_for('admin.login'))
    
    # Generate secret if not exists
    if not admin.totp_secret:
        admin.totp_secret = pyotp.random_base32()
        db.session.commit()
    
    secret = admin.totp_secret
    totp = pyotp.TOTP(secret)

    if request.method == 'POST':
        code = request.form.get('code')
        if totp.verify(code):
            db.session.commit()  # Secret already saved
            
            # Log the user in
            login_user(admin)
            session.permanent = True
            
            # ===== CONSISTENT FINGERPRINT GENERATION =====
            device_info = AdminTrustedDevice.get_device_info(request)
            
            # Use the EXACT same method as the model's generate_fingerprint()
            # Format: admin_id + ip_address + user_agent + browser + os
            fingerprint_data = f"{admin.id}{device_info['ip_address']}{device_info['user_agent']}{device_info['browser']}{device_info['os']}"
            device_fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()
            
            print(f"🔑 Setup generated fingerprint: {device_fingerprint[:20]}...")
            
            # Store in session
            session['admin_device_fingerprint'] = device_fingerprint
            
            # CHECK IF THIS DEVICE ALREADY EXISTS
            existing_device = AdminTrustedDevice.query.filter_by(
                admin_id=admin.id,
                device_fingerprint=device_fingerprint
            ).first()
            
            if existing_device:
                # Update existing device
                existing_device.trusted = True
                existing_device.last_used = datetime.utcnow()
                existing_device.expires_at = datetime.utcnow() + timedelta(days=30)
                # Update device info
                existing_device.ip_address = device_info['ip_address']
                existing_device.user_agent = device_info['user_agent']
                existing_device.browser = device_info['browser']
                existing_device.os = device_info['os']
                existing_device.device_type = device_info['device_type']
                existing_device.device_name = f"{device_info['browser']} on {device_info['os']}"
                db.session.commit()
                print(f"✅ Updated existing device: {existing_device.id}")
            else:
                # Create new trusted device
                new_device = AdminTrustedDevice(
                    admin_id=admin.id,
                    device_name=f"{device_info['browser']} on {device_info['os']}",
                    ip_address=device_info['ip_address'],
                    user_agent=device_info['user_agent'],
                    browser=device_info['browser'],
                    os=device_info['os'],
                    device_type=device_info['device_type'],
                    trusted=True,
                    expires_at=datetime.utcnow() + timedelta(days=30)
                )
                # Set fingerprint using the same method
                new_device.device_fingerprint = device_fingerprint
                db.session.add(new_device)
                db.session.commit()
                print(f"✅ Created new device: {new_device.id}")
            
            # Clean up session
            session.pop('pre_2fa_admin_id', None)
            session.pop('2fa_setup_complete', None)
            
            flash("2FA setup successful! Welcome, Admin.", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            flash("Invalid code. Try again.", "error")

    totp_uri = totp.provisioning_uri(
        name=admin.email,
        issuer_name="CTU-COMELEC Admin"
    )
    return render_template('admin_2fa_setup.html', totp_uri=totp_uri, secret=secret)


@admin_bp.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """Disable 2FA for the current admin"""
    try:
        admin = current_user
        # Remove the TOTP secret from database
        admin.totp_secret = None
        db.session.commit()
        
        # Log the action
        log_audit(
            action='2FA_DISABLE',
            description=f"Admin user '{admin.username}' disabled two-factor authentication"
        )
        
        return jsonify({'success': True, 'message': '2FA disabled successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

        
@admin_bp.route('/verify-device')
def verify_device_page():
    """Page shown when new device needs verification"""
    admin_id = session.get('pending_admin_login')
    fingerprint = session.get('pending_device_fp')
    
    if not admin_id or not fingerprint:
        flash("No pending device verification.", "danger")
        return redirect(url_for('admin.login'))
    
    admin = Admin.query.get(admin_id)
    if not admin:
        session.pop('pending_admin_login', None)
        session.pop('pending_device_fp', None)
        return redirect(url_for('admin.login'))
    
    device = AdminTrustedDevice.query.filter_by(
        admin_id=admin.id,
        device_fingerprint=fingerprint,
        trusted=False
    ).first()
    
    if not device:
        # Maybe already verified? Check session
        return render_template('admin_verify_device.html', admin=admin, message="Device already verified?", redirect_after=3)
    
    return render_template('admin_verify_device.html', admin=admin, device=device)


@admin_bp.route('/verify-device/resend', methods=['POST'])
def resend_admin_verification():
    """Resend verification email"""
    admin_id = session.get('pending_admin_login')
    fingerprint = session.get('pending_device_fp')
    
    if not admin_id or not fingerprint:
        return jsonify({"success": False, "message": "No pending verification"}), 400
    
    admin = Admin.query.get(admin_id)
    device = AdminTrustedDevice.query.filter_by(
        admin_id=admin_id,
        device_fingerprint=fingerprint,
        trusted=False
    ).first()
    
    if not device:
        return jsonify({"success": False, "message": "Device not found"}), 404
    
    from admin.utils import send_admin_new_device_email
    send_admin_new_device_email(admin, device)
    
    return jsonify({"success": True, "message": "Verification email resent"})


@admin_bp.route('/verify-device/confirm/<token>')
def confirm_admin_device(token):
    """Confirm new device via email link (Yes, it's me)"""
    device = AdminTrustedDevice.query.filter_by(verification_token=token).first()
    
    if not device:
        return render_template('admin_device_result.html', 
                             success=False, 
                             message='Invalid or expired verification link.')
    
    # Check if token expired (15 minutes)
    if device.verification_sent_at and datetime.utcnow() > device.verification_sent_at + timedelta(minutes=15):
        db.session.delete(device)
        db.session.commit()
        return render_template('admin_device_result.html',
                             success=False,
                             message='Verification link has expired. Please try logging in again.')
    
    # Mark device as trusted
    device.trusted = True
    device.verification_token = None
    device.expires_at = datetime.utcnow() + timedelta(days=30)
    device.last_used = datetime.utcnow()
    db.session.commit()
    
    # If this is the device that was pending, we can auto-login
    # Check if this matches pending session
    pending_fp = session.get('pending_device_fp')
    if pending_fp and pending_fp == device.device_fingerprint:
        admin = device.admin
        login_user(admin)
        session.permanent = True
        session.pop('pending_admin_login', None)
        session.pop('pending_device_fp', None)
        
        return render_template('admin_device_result.html',
                             success=True,
                             message='Device verified successfully! You are now being logged in...',
                             auto_redirect=True,
                             redirect_url=url_for('admin.dashboard'))
    
    return render_template('admin_device_result.html',
                         success=True,
                         message='Device verified successfully! You can now close this window and return to login.')


@admin_bp.route('/verify-device/reject/<token>')
def reject_admin_device(token):
    """Reject new device via email link (No, it's not me)"""
    device = AdminTrustedDevice.query.filter_by(verification_token=token).first()
    
    if device:
        db.session.delete(device)
        db.session.commit()
    
    return render_template('admin_device_result.html',
                         success=False,
                         message='Device rejected. No action needed.')


@admin_bp.route('/verify-device/status')
def verify_device_status():
    """Check if device has been verified (polling endpoint)"""
    admin_id = session.get('pending_admin_login')
    fingerprint = session.get('pending_device_fp')
    
    if not admin_id or not fingerprint:
        return jsonify({"status": "no_session"})
    
    # Check if device is now trusted
    device = AdminTrustedDevice.query.filter_by(
        admin_id=admin_id,
        device_fingerprint=fingerprint,
        trusted=True
    ).first()
    
    if device:
        # 🚀 AUTO-LOGIN THE ADMIN HERE
        admin = Admin.query.get(admin_id)
        if admin:
            login_user(admin)
            session.permanent = True
            
            # Update last used
            device.update_last_used()
            db.session.commit()
            
            # Clean up session
            session.pop('pending_admin_login', None)
            session.pop('pending_device_fp', None)
            
            return jsonify({"status": "verified"})
    
    # Check if device was rejected/deleted
    device_any = AdminTrustedDevice.query.filter_by(
        admin_id=admin_id,
        device_fingerprint=fingerprint
    ).first()
    
    if device_any is None:
        # Clean up session on rejection
        session.pop('pending_admin_login', None)
        session.pop('pending_device_fp', None)
        return jsonify({"status": "rejected"})
    
    return jsonify({"status": "pending"})





@admin_bp.route('/2fa/setup-data', methods=['GET'])
def get_2fa_setup_data():
    """AJAX endpoint to get 2FA setup data for inline setup"""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    admin = current_user
    
    # Generate secret if not exists
    if not admin.totp_secret:
        admin.totp_secret = pyotp.random_base32()
        db.session.commit()
    
    secret = admin.totp_secret
    totp = pyotp.TOTP(secret)
    
    totp_uri = totp.provisioning_uri(
        name=admin.email,
        issuer_name="CTU-COMELEC Admin"
    )
    
    return jsonify({
        'success': True,
        'totp_uri': totp_uri,
        'secret': secret,
        'email': admin.email
    })

# ---------------------- DASHBOARD ---------------------- #
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Get school year filter from URL parameters or session
    school_year = request.args.get('school_year')
    
    # If no school_year parameter, try to get from session
    if not school_year:
        school_year = session.get('admin_current_school_year')
    
    # Parse school year to date range
    start_date = None
    end_date = None
    if school_year:
        try:
            start_year = int(school_year.split('-')[0])
            end_year = int(school_year.split('-')[1])
            start_date = datetime(start_year, 1, 1)
            end_date = datetime(end_year, 12, 31)
        except (ValueError, IndexError):
            start_date = None
            end_date = None
    
    # Save to session
    if school_year:
        session['admin_current_school_year'] = school_year
    
    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)

    # ================================
    # Build base queries with school year filter
    # ================================
    student_query = Student.query
    election_query = Election.query
    vote_query = Vote.query
    
    if start_date and end_date:
        # For elections, filter by start date in range
        election_query = election_query.filter(
            Election.start_date >= start_date,
            Election.start_date <= end_date
        )
        
        # For votes, filter by cast_timestamp in range
        vote_query = vote_query.filter(
            Vote.cast_timestamp >= start_date,
            Vote.cast_timestamp <= end_date
        )
    
    # ================================
    # KPI counts with school year filter
    # ================================
    total_students = Student.query.count()  # Total students always same
    total_elections = election_query.count()
    total_votes = vote_query.count()

    # ================================
    # Recent elections table with school year filter
    # ================================
    elections = election_query.order_by(Election.start_date.desc()).all()
    recent_elections_all = elections

    # Localize timezone if naive
    for election in recent_elections_all:
        if election.start_date.tzinfo is None:
            election.start_date = tz.localize(election.start_date)
        if election.end_date.tzinfo is None:
            election.end_date = tz.localize(election.end_date)

    recent_elections = recent_elections_all[:5]
    
    # Calculate ongoing elections (based on current date, not filtered by school year)
    ongoing_elections = sum(1 for e in Election.query.all() if e.status == 'Open')

    # Calculate voter turnout (using filtered votes)
    voter_turnout = "0%"
    if total_students > 0:
        turnout_percentage = (total_votes / total_students) * 100
        voter_turnout = f"{turnout_percentage:.1f}%"

    # Get all available school years from elections
    all_elections = Election.query.order_by(Election.start_date.asc()).all()
    school_years = set()
    for election in all_elections:
        if election.start_date:
            year = election.start_date.year
            school_years.add(f"{year}-{year+1}")
    
    # Sort school years in descending order (newest first)
    school_years = sorted(list(school_years), reverse=True)

    # ---------- AUDIT LOG: Dashboard viewed ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='DASHBOARD_VIEW',
        description=f"Admin user '{username}' viewed the dashboard from IP: {ip} | School Year: {school_year or 'All'} | Stats: {total_students} students, {total_elections} elections, {total_votes} votes"
    )

    return render_template(
        'admin_dashboard.html',
        admin=current_user,
        total_students=total_students,
        total_elections=total_elections,
        ongoing_elections=ongoing_elections,
        total_votes=total_votes,
        voter_turnout=voter_turnout,
        recent_elections=recent_elections,
        recent_elections_all=recent_elections_all,
        school_years=school_years,
        current_sy=school_year,
        now=now
    )




# Add these imports at the top of your admin/routes.py if not already present
from datetime import datetime, timedelta
from sqlalchemy import func
from flask import jsonify
import pytz

@admin_bp.route('/api/voting-trends')
@admin_required
def get_voting_trends():
    """API endpoint to get voting trends data for charts"""
    try:
        # Get parameters
        election_id = request.args.get('election_id', 'all')
        school_year = request.args.get('school_year')
        
        # Parse school year to date range
        start_date = None
        end_date = None
        if school_year:
            try:
                start_year = int(school_year.split('-')[0])
                end_year = int(school_year.split('-')[1])
                start_date = datetime(start_year, 1, 1)
                end_date = datetime(end_year, 12, 31)
            except (ValueError, IndexError):
                start_date = None
                end_date = None
        
        # Get timezone
        tz = pytz.timezone('Asia/Manila')
        
        # Get last 24 hours
        end_date_chart = datetime.now(tz)
        start_date_chart = end_date_chart - timedelta(hours=24)
        
        # Create a list of all hours in the last 24 hours
        hours = []
        current = start_date_chart
        while current <= end_date_chart:
            hours.append(current.strftime('%Y-%m-%d %H:00'))
            current += timedelta(hours=1)
        
        # Base query for votes
        vote_query = Vote.query
        
        # Apply school year filter if specified
        if start_date and end_date:
            vote_query = vote_query.filter(
                Vote.cast_timestamp >= start_date,
                Vote.cast_timestamp <= end_date
            )
        
        if election_id != 'all':
            # Filter by specific election
            vote_query = vote_query.filter(Vote.election_id == election_id)
        
        # Apply time range filter
        vote_query = vote_query.filter(
            Vote.cast_timestamp >= start_date_chart,
            Vote.cast_timestamp <= end_date_chart
        )
        
        votes = vote_query.all()
        
        # Group votes by hour
        votes_by_hour = {}
        for vote in votes:
            if vote.cast_timestamp:
                hour_key = vote.cast_timestamp.strftime('%Y-%m-%d %H:00')
                votes_by_hour[hour_key] = votes_by_hour.get(hour_key, 0) + 1
        
        # Create data arrays for all hours
        labels = []
        data = []
        for hour in hours:
            labels.append(hour)
            data.append(votes_by_hour.get(hour, 0))
        
        # Get all elections for the filter buttons (with school year filter)
        election_query = Election.query.order_by(Election.start_date.desc())
        
        if start_date and end_date:
            election_query = election_query.filter(
                Election.start_date >= start_date,
                Election.start_date <= end_date
            )
        
        elections = election_query.all()
        election_list = []
        
        # Add "All Elections" option
        all_votes_query = Vote.query
        if start_date and end_date:
            all_votes_query = all_votes_query.filter(
                Vote.cast_timestamp >= start_date,
                Vote.cast_timestamp <= end_date
            )
        all_votes_count = all_votes_query.count()
        
        election_list.append({
            'id': 'all',
            'name': 'All Elections',
            'scope': 'all',
            'total_votes': all_votes_count
        })
        
        # Add each election
        for e in elections:
            # Determine display name based on scope
            if e.scope == 'campus':
                display_name = f" {e.title}"
            else:
                # Get department name
                if e.department_rel:
                    dept_name = e.department_rel.name
                else:
                    dept_name = e.department or 'Department'
                display_name = f"📚 {dept_name}: {e.title}"
            
            # Count votes for this election (with school year filter)
            vote_count_query = Vote.query.filter_by(election_id=e.id)
            if start_date and end_date:
                vote_count_query = vote_count_query.filter(
                    Vote.cast_timestamp >= start_date,
                    Vote.cast_timestamp <= end_date
                )
            vote_count = vote_count_query.count()
            
            # Get status emoji
            status_emoji = '🟢' if e.status == 'Open' else '🟡' if e.status == 'Upcoming' else '🔴'
            
            election_list.append({
                'id': e.id,
                'name': display_name,
                'scope': e.scope,
                'status': e.status,
                'status_emoji': status_emoji,
                'total_votes': vote_count,
                'start_date': e.start_date.strftime('%Y-%m-%d') if e.start_date else 'N/A',
                'end_date': e.end_date.strftime('%Y-%m-%d') if e.end_date else 'N/A'
            })
        
        # Format labels for display (e.g., "2 PM", "10 AM")
        display_labels = []
        for label in labels:
            try:
                dt = datetime.strptime(label, '%Y-%m-%d %H:00')
                hour = dt.hour
                if hour == 0:
                    display_labels.append('12 AM')
                elif hour < 12:
                    display_labels.append(f'{hour} AM')
                elif hour == 12:
                    display_labels.append('12 PM')
                else:
                    display_labels.append(f'{hour-12} PM')
            except:
                display_labels.append(label)
        
        return jsonify({
            'success': True,
            'labels': display_labels,
            'data': data,
            'elections': election_list,
            'current_election': election_id,
            'current_school_year': school_year
        })
        
    except Exception as e:
        print(f"Error in voting trends: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'labels': [],
            'data': [],
            'elections': []
        })



@admin_bp.route('/api/election-stats/<election_id>')
@admin_required
def get_election_stats(election_id):
    """Get detailed stats for a specific election"""
    try:
        # Get school year parameter
        school_year = request.args.get('school_year')
        
        # Parse school year to date range
        start_date = None
        end_date = None
        if school_year:
            try:
                start_year = int(school_year.split('-')[0])
                end_year = int(school_year.split('-')[1])
                start_date = datetime(start_year, 1, 1)
                end_date = datetime(end_year, 12, 31)
            except (ValueError, IndexError):
                start_date = None
                end_date = None
        
        tz = pytz.timezone('Asia/Manila')
        
        if election_id == 'all':
            # All elections combined
            vote_query = Vote.query
            if start_date and end_date:
                vote_query = vote_query.filter(
                    Vote.cast_timestamp >= start_date,
                    Vote.cast_timestamp <= end_date
                )
            total_votes = vote_query.count()
            
            total_eligible = Student.query.count()
            
            # Get ongoing elections count (not filtered by school year)
            ongoing = Election.query.filter(
                Election.start_date <= datetime.now(tz),
                Election.end_date >= datetime.now(tz)
            ).count()
            
            # Calculate turnout
            if total_eligible > 0:
                turnout = f"{(total_votes/total_eligible*100):.1f}%"
            else:
                turnout = "0%"
            
            title = 'All Elections'
            if school_year:
                title += f' (SY {school_year})'
            
            return jsonify({
                'success': True,
                'total_votes': total_votes,
                'total_eligible': total_eligible,
                'turnout': turnout,
                'election_title': title,
                'election_scope': 'Combined',
                'ongoing_elections': ongoing,
                'school_year': school_year
            })
        
        else:
            election = Election.query.get_or_404(int(election_id))
            
            # Get eligible students based on election scope
            if election.scope == 'campus':
                eligible_students = Student.query.count()
            else:
                # Department election - filter by department
                if election.department_id:
                    eligible_students = Student.query.filter_by(department_id=election.department_id).count()
                else:
                    # Fallback to department name
                    eligible_students = Student.query.filter_by(department=election.department).count()
            
            # Get votes for this election (with school year filter)
            vote_query = Vote.query.filter_by(election_id=election.id)
            if start_date and end_date:
                vote_query = vote_query.filter(
                    Vote.cast_timestamp >= start_date,
                    Vote.cast_timestamp <= end_date
                )
            total_votes = vote_query.count()
            
            # Calculate turnout
            if eligible_students > 0:
                turnout = f"{(total_votes/eligible_students*100):.1f}%"
            else:
                turnout = "0%"
            
            title = election.title
            if school_year:
                title += f' (SY {school_year})'
            
            return jsonify({
                'success': True,
                'total_votes': total_votes,
                'total_eligible': eligible_students,
                'turnout': turnout,
                'election_title': title,
                'election_scope': 'Campus-wide' if election.scope == 'campus' else 'Departmental',
                'election_status': election.status,
                'start_date': election.start_date.strftime('%Y-%m-%d %H:%M') if election.start_date else 'N/A',
                'end_date': election.end_date.strftime('%Y-%m-%d %H:%M') if election.end_date else 'N/A',
                'school_year': school_year
            })
            
    except Exception as e:
        print(f"Error in election stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'total_votes': 0,
            'total_eligible': 0,
            'turnout': '0%'
        })


# Add this to your admin routes file (where your dashboard route is)

@admin_bp.route('/settings')
@admin_required
def settings():
    """
    System Settings page
    """
    try:
        tz = pytz.timezone('Asia/Manila')
        now = datetime.now(tz)
        
        # Get audit logs for the logs section
        page = request.args.get("page", 1, type=int)
        search = request.args.get("search", "")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        
        query = AuditLog.query
        
        # Search filter
        if search:
            query = query.filter(
                or_(
                    AuditLog.action.ilike(f"%{search}%"),
                    AuditLog.role.ilike(f"%{search}%"),
                    AuditLog.description.ilike(f"%{search}%")
                )
            )
        
        # Date filters
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(AuditLog.timestamp >= start_date_obj)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
                query = query.filter(AuditLog.timestamp <= end_date_obj)
            except ValueError:
                pass
        
        # Order by latest first
        query = query.order_by(desc(AuditLog.timestamp))
        
        # Pagination
        logs = query.paginate(page=page, per_page=20)
        
        # Get trusted devices for current admin
        trusted_devices = AdminTrustedDevice.query.filter_by(
            admin_id=current_user.id
        ).order_by(AdminTrustedDevice.last_used.desc()).all()
        
        # Mark current device
        current_fingerprint = session.get('admin_device_fingerprint')
        for device in trusted_devices:
            device.is_current = (device.device_fingerprint == current_fingerprint)
        
        # Get last backup info (you can implement this later)
        last_backup = None
        
        # Log the settings page view
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        log_audit(
            action='SETTINGS_VIEW',
            description=f"Admin user '{username}' viewed system settings from IP: {ip}"
        )
        
        return render_template(
            'admin_settings.html',
            admin=current_user,
            now=now,
            logs=logs,
            search=search,
            start_date=start_date,
            end_date=end_date,
            pytz=pytz,
            last_backup=last_backup,
            trusted_devices=trusted_devices  # ADD THIS LINE
        )
        
    except Exception as e:
        flash(f'Error loading settings: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

    

@admin_bp.route('/settings/save', methods=['POST'])
@admin_required
def save_settings():
    """
    Save system settings
    """
    try:
        data = request.get_json()
        section = data.get('section')
        settings = data.get('settings', {})
        
        # Log the settings change
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        log_audit(
            action='SETTINGS_UPDATE',
            description=f"Admin user '{username}' updated {section} settings from IP: {ip}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Settings saved successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500





from datetime import datetime, timedelta
from flask import jsonify, request, render_template, flash, redirect, url_for, session
from flask_login import login_required, current_user
import secrets
import hashlib

@admin_bp.route('/trusted-devices')
@login_required
def trusted_devices():
    """View all trusted devices for current admin"""
    devices = AdminTrustedDevice.query.filter_by(
        admin_id=current_user.id
    ).order_by(AdminTrustedDevice.last_used.desc()).all()
    
    # Mark current device
    current_fingerprint = session.get('admin_device_fingerprint')
    for device in devices:
        device.is_current = (device.device_fingerprint == current_fingerprint)
    
    return render_template('trusted_devices.html', devices=devices)



@admin_bp.route('/trusted-devices/add', methods=['POST'])
@login_required
def add_trusted_device():
    """Add current device as trusted"""
    device_info = AdminTrustedDevice.get_device_info(request)
    
    # Use the EXACT same fingerprint generation method
    # Format: admin_id + ip_address + user_agent + browser + os
    fingerprint_data = f"{current_user.id}{device_info['ip_address']}{device_info['user_agent']}{device_info['browser']}{device_info['os']}"
    device_fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()
    
    print(f"🔑 Add trusted device fingerprint: {device_fingerprint[:20]}...")
    
    # Check if this specific device (by fingerprint) already exists
    existing_device = AdminTrustedDevice.query.filter_by(
        admin_id=current_user.id,
        device_fingerprint=device_fingerprint
    ).first()
    
    if existing_device:
        # Update existing device
        existing_device.trusted = True
        existing_device.expires_at = datetime.utcnow() + timedelta(days=30)
        existing_device.last_used = datetime.utcnow()
        existing_device.device_name = f"{device_info['browser']} on {device_info['os']}"
        existing_device.ip_address = device_info['ip_address']
        existing_device.user_agent = device_info['user_agent']
        existing_device.browser = device_info['browser']
        existing_device.os = device_info['os']
        existing_device.device_type = device_info['device_type']
        
        db.session.commit()
        
        # Set the fingerprint in session
        session['admin_device_fingerprint'] = existing_device.device_fingerprint
        
        return jsonify({
            'success': True, 
            'message': 'Device already trusted and updated!',
            'device_added': True
        })
    else:
        # Create NEW trusted device
        device = AdminTrustedDevice(
            admin_id=current_user.id,
            device_name=f"{device_info['browser']} on {device_info['os']}",
            ip_address=device_info['ip_address'],
            user_agent=device_info['user_agent'],
            browser=device_info['browser'],
            os=device_info['os'],
            device_type=device_info['device_type'],
            trusted=True,
            expires_at=datetime.utcnow() + timedelta(days=30),
            last_used=datetime.utcnow()
        )
        
        # Set the consistent fingerprint
        device.device_fingerprint = device_fingerprint
        
        db.session.add(device)
        db.session.commit()
        
        # Store fingerprint in session
        session['admin_device_fingerprint'] = device.device_fingerprint
        
        return jsonify({
            'success': True, 
            'message': 'Device added to trusted devices!',
            'device_added': True
        })



@admin_bp.route('/trusted-devices/remove/<int:device_id>', methods=['POST'])
@login_required
def request_remove_device(device_id):
    """Request to remove a trusted device (sends confirmation email)"""
    print(f"=== DEBUG: Device removal requested for device ID: {device_id} ===")
    print(f"Current user ID: {current_user.id}")
    print(f"Request method: {request.method}")
    print(f"Request headers: {dict(request.headers)}")
    
    try:
        # Get JSON data if sent
        data = request.get_json(silent=True) or {}
        print(f"Request data: {data}")
        
        device = AdminTrustedDevice.query.filter_by(
            id=device_id,
            admin_id=current_user.id
        ).first()
        
        if not device:
            print(f"DEBUG: Device not found - ID: {device_id}, admin_id: {current_user.id}")
            return jsonify({
                'success': False,
                'message': 'Device not found or already removed'
            }), 404
        
        print(f"DEBUG: Device found - ID: {device.id}, Name: {device.device_name}, Trusted: {device.trusted}")
        print(f"DEBUG: Device fingerprint: {device.device_fingerprint}")
        
        # Check if device is trusted
        if not device.trusted:
            return jsonify({
                'success': False,
                'message': 'Device is not trusted'
            }), 400
        
        # Don't allow removing current device
        current_fingerprint = session.get('admin_device_fingerprint')
        print(f"DEBUG: Current session fingerprint: {current_fingerprint}")
        
        if device.device_fingerprint and current_fingerprint and device.device_fingerprint == current_fingerprint:
            print(f"DEBUG: Cannot remove current device")
            return jsonify({
                'success': False,
                'message': 'Cannot remove your current device'
            }), 400
        
        # Generate removal token
        removal_token = secrets.token_urlsafe(32)
        print(f"DEBUG: Generated token: {removal_token}")
        
        device.verification_token = removal_token
        device.verification_sent_at = datetime.utcnow()
        db.session.commit()
        print(f"DEBUG: Token saved to database for device {device.id}")
        
        # Send confirmation email
        try:
            from admin.utils import send_device_removal_confirmation
            
            # Check if email function exists
            if 'send_device_removal_confirmation' not in dir():
                print(f"DEBUG: Email function not found, creating mock response")
                # For testing, return success without email
                return jsonify({
                    'success': True,
                    'message': 'Device removal initiated (email simulation)',
                    'dev_mode': True
                })
            
            print(f"DEBUG: Attempting to send email to: {current_user.email}")
            send_device_removal_confirmation(current_user, device, removal_token)
            print(f"DEBUG: Email sent successfully")
            
            return jsonify({
                'success': True,
                'message': 'Removal confirmation email sent. Please check your inbox.'
            })
            
        except ImportError as e:
            print(f"DEBUG: Email function import error: {str(e)}")
            # For development, return success anyway
            return jsonify({
                'success': True,
                'message': 'Device removal initiated (email disabled in development)',
                'dev_mode': True
            })
            
        except Exception as e:
            print(f"DEBUG: Email sending failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Rollback token if email fails
            device.verification_token = None
            device.verification_sent_at = None
            db.session.commit()
            
            return jsonify({
                'success': False,
                'message': f'Failed to send email: {str(e)}'
            }), 500
            
    except Exception as e:
        print(f"DEBUG: Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Server error occurred'
        }), 500

    
    


@admin_bp.route('/trusted-devices/confirm-remove/<token>')
def confirm_remove_device(token):
    """Confirm device removal via email link"""
    device = AdminTrustedDevice.query.filter_by(verification_token=token).first()
    
    if not device:
        return render_template('device_removal_result.html',
                             success=False,
                             message='Invalid or expired confirmation link.')
    
    # Check if token expired (15 minutes)
    if device.verification_sent_at and datetime.utcnow() > device.verification_sent_at + timedelta(minutes=15):
        device.verification_token = None
        device.verification_sent_at = None
        db.session.commit()
        
        return render_template('device_removal_result.html',
                             success=False,
                             message='Confirmation link has expired. Please try again.')
    
    # Don't allow removing current device
    current_fingerprint = session.get('admin_device_fingerprint')
    if device.device_fingerprint == current_fingerprint:
        return render_template('device_removal_result.html',
                             success=False,
                             message='Cannot remove your current device.')
    
    # Remove the device
    device_name = device.device_name
    db.session.delete(device)
    db.session.commit()
    
    # Log the action
    username = getattr(current_user, 'username', 'Unknown') if current_user.is_authenticated else 'Unknown'
    ip = request.remote_addr
    
    log_audit(
        action='DEVICE_REMOVED',
        description=f"Admin user removed trusted device '{device_name}' from IP: {ip}"
    )
    
    return render_template('device_removal_result.html',
                         success=True,
                         message='Device has been successfully removed from your trusted devices.')

@admin_bp.route('/trusted-devices/cancel-remove/<token>')
def cancel_remove_device(token):
    """Cancel device removal request"""
    device = AdminTrustedDevice.query.filter_by(verification_token=token).first()
    
    if device:
        # Clear the verification token
        device.verification_token = None
        device.verification_sent_at = None
        db.session.commit()
    
    return render_template('device_removal_result.html',
                         success=True,
                         message='Device removal request has been cancelled. Your device remains trusted.')

@admin_bp.route('/trusted-devices/verify/send', methods=['POST'])
@login_required
def send_device_verification():
    """Send verification email for new device"""
    device_info = AdminTrustedDevice.get_device_info(request)
    
    # Check if device already exists and is trusted
    existing = AdminTrustedDevice.query.filter_by(
        admin_id=current_user.id,
        ip_address=device_info['ip_address'],
        browser=device_info['browser'],
        trusted=True
    ).first()
    
    if existing:
        # Device already trusted, update last used
        existing.last_used = datetime.utcnow()
        existing.expires_at = datetime.utcnow() + timedelta(days=30)
        db.session.commit()
        
        # Store fingerprint in session
        session['admin_device_fingerprint'] = existing.device_fingerprint
        
        return jsonify({
            'success': True,
            'trusted': True,
            'message': 'Device already trusted'
        })
    
    # Create or get unverified device
    device = AdminTrustedDevice.query.filter_by(
        admin_id=current_user.id,
        ip_address=device_info['ip_address'],
        browser=device_info['browser'],
        trusted=False
    ).first()
    
    if not device:
        device = AdminTrustedDevice(
            admin_id=current_user.id,
            device_name=f"{device_info['browser']} on {device_info['os']}",
            trusted=False,
            **device_info
        )
        device.generate_fingerprint()
        db.session.add(device)
    
    # Generate verification token
    token = device.generate_verification_token()
    db.session.commit()
    
    # Send verification email
    from admin.utils import send_admin_device_verification_email
    send_admin_device_verification_email(current_user, device, token)
    
    return jsonify({
        'success': True,
        'trusted': False,
        'message': 'Verification email sent'
    })

@admin_bp.route('/trusted-devices/verify/<token>')
def verify_admin_device(token):
    """Verify device via email link"""
    device = AdminTrustedDevice.query.filter_by(verification_token=token).first()
    
    if not device:
        return render_template('device_verification_result.html', 
                             success=False, 
                             message='Invalid or expired verification link.')
    
    # Check if token expired (15 minutes)
    if device.verification_sent_at and datetime.utcnow() > device.verification_sent_at + timedelta(minutes=15):
        db.session.delete(device)
        db.session.commit()
        return render_template('device_verification_result.html',
                             success=False,
                             message='Verification link has expired. Please try again.')
    
    # Mark device as trusted
    device.trusted = True
    device.verification_token = None
    device.expires_at = datetime.utcnow() + timedelta(days=30)
    device.last_used = datetime.utcnow()
    db.session.commit()
    
    # Store fingerprint in session if this is the current device
    if device.ip_address == request.remote_addr:
        session['admin_device_fingerprint'] = device.device_fingerprint
    
    return render_template('device_verification_result.html',
                         success=True,
                         message='Device verified successfully! You can now use this device without 2FA.')

@admin_bp.route('/trusted-devices/check', methods=['POST'])
def check_device_trust():
    """Check if current device is trusted (used during login)"""
    if not current_user.is_authenticated:
        return jsonify({'trusted': False})
    
    device_info = AdminTrustedDevice.get_device_info(request)
    current_fingerprint = session.get('admin_device_fingerprint')
    
    # Check by fingerprint first
    if current_fingerprint:
        device = AdminTrustedDevice.query.filter_by(
            admin_id=current_user.id,
            device_fingerprint=current_fingerprint,
            trusted=True
        ).first()
        
        if device and not device.is_expired():
            device.last_used = datetime.utcnow()
            db.session.commit()
            return jsonify({'trusted': True})
    
    # Fallback to IP and browser check
    device = AdminTrustedDevice.query.filter_by(
        admin_id=current_user.id,
        ip_address=device_info['ip_address'],
        browser=device_info['browser'],
        trusted=True
    ).first()
    
    if device and not device.is_expired():
        device.last_used = datetime.utcnow()
        db.session.commit()
        # Update session fingerprint
        session['admin_device_fingerprint'] = device.device_fingerprint
        return jsonify({'trusted': True})
    
    return jsonify({'trusted': False})



from student.models import TrustedDevice 
# ---------------------- IMPORT STUDENTS ---------------------- #
@admin_bp.route("/import_students", methods=["GET", "POST"])
def import_students():
    import time
    import pandas as pd
    from sqlalchemy import text
    from datetime import datetime
    
    start_time = time.time()

    if request.method == "POST":
        file = request.files.get("excel_file")

        if not file or file.filename == "":
            flash("No file selected.", "import-danger")
            return redirect(url_for("admin.import_students"))

        temp_file_path = None
        try:
            # Save file temporarily to avoid memory issues with large Excel
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                file.save(tmp.name)
                temp_file_path = tmp.name
            
            print(f"📊 STEP 0: File saved in {time.time() - start_time:.2f}s")
            
            # STEP 1: Read Excel with optimized settings
            # Only read necessary columns, use faster engine
            df = pd.read_excel(
                temp_file_path, 
                dtype={"StudentNo": str},
                usecols=["StudentNo", "LastName", "FirstName"],  # Only read needed columns
                engine='openpyxl'  # Default Excel engine  # Faster engine if available, otherwise 'openpyxl'
            )
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            print(f"📊 STEP 1: Loaded Excel in {time.time() - start_time:.2f}s")
            
            # STEP 2: Clean data using vectorized operations (MUCH faster than loops)
            df['StudentNo'] = df['StudentNo'].astype(str).str.strip()
            df['StudentNo'] = df['StudentNo'].str.replace(r'\.0$', '', regex=True)
            df['FirstName'] = df['FirstName'].astype(str).str.strip()
            df['LastName'] = df['LastName'].astype(str).str.strip()
            
            # Remove rows with invalid student numbers
            df = df[df['StudentNo'].notna() & (df['StudentNo'] != '') & (df['StudentNo'] != 'nan')]
            
            # Get unique student numbers (remove duplicates)
            df = df.drop_duplicates(subset=['StudentNo'])
            
            excel_student_nos = set(df['StudentNo'].tolist())
            excel_data = df.to_dict('records')
            
            print(f"📊 STEP 2: Cleaned data - {len(excel_data)} unique students in {time.time() - start_time:.2f}s")

            # ===== OPTIMIZATION 1: Use RAW SQL for bulk operations =====
            # Get connection for raw SQL (fastest for bulk operations)
            connection = db.session.connection()
            
            # STEP 3: Get existing CTU students in one query
            existing_result = connection.execute(
                text("SELECT student_number, id, first_name, last_name FROM ctu_students")
            )
            existing_ctu = {}
            for row in existing_result:
                existing_ctu[row[0]] = {'id': row[1], 'first_name': row[2], 'last_name': row[3]}
            
            print(f"📊 STEP 3: Fetched {len(existing_ctu)} CTU students in {time.time() - start_time:.2f}s")
            
            # STEP 4: Get registered students and their vote status in ONE query
            registered_result = connection.execute(
                text("""
                    SELECT s.id, s.id_number, 
                           CASE WHEN v.student_id IS NOT NULL THEN 1 ELSE 0 END as has_voted
                    FROM students s
                    LEFT JOIN votes v ON s.id = v.student_id
                """)
            )
            registered_map = {}
            students_with_votes = set()
            for row in registered_result:
                registered_map[row[1]] = {'id': row[0], 'has_voted': row[2]}
                if row[2]:
                    students_with_votes.add(row[0])
            
            print(f"📊 STEP 4: Fetched {len(registered_map)} registered students in {time.time() - start_time:.2f}s")

            # ===== OPTIMIZATION 2: Prepare bulk operations =====
            # Prepare lists for batch operations
            to_insert = []
            to_update = []
            
            for student in excel_data:
                student_no = student['StudentNo']
                first_name = student['FirstName']
                last_name = student['LastName']
                
                if student_no in existing_ctu:
                    # Only update if name changed (reduce unnecessary updates)
                    existing = existing_ctu[student_no]
                    if existing['first_name'] != first_name or existing['last_name'] != last_name:
                        to_update.append({
                            'student_number': student_no,
                            'first_name': first_name,
                            'last_name': last_name
                        })
                else:
                    to_insert.append({
                        'student_number': student_no,
                        'first_name': first_name,
                        'last_name': last_name
                    })
            
            print(f"📊 STEP 5: Prepared {len(to_insert)} inserts, {len(to_update)} updates in {time.time() - start_time:.2f}s")

            # ===== OPTIMIZATION 3: BULK INSERT using executemany =====
            if to_insert:
                # Use SQLAlchemy's bulk insert (safer and still fast)
                chunk_size = 1000
                for i in range(0, len(to_insert), chunk_size):
                    chunk = to_insert[i:i+chunk_size]
                    
                    # Prepare data for insertion
                    insert_data = [{
                        'student_number': s['student_number'],
                        'first_name': s['first_name'],
                        'last_name': s['last_name']
                    } for s in chunk]
                    
                    # Use SQLAlchemy's bulk insert
                    db.session.bulk_insert_mappings(CtuStudent, insert_data)
                    db.session.flush()  # Flush but don't commit yet
                    
                    print(f"   Inserted chunk {i//chunk_size + 1}/{(len(to_insert)-1)//chunk_size + 1}")
            
            print(f"📊 STEP 6: Completed inserts in {time.time() - start_time:.2f}s")

            # ===== OPTIMIZATION 4: BULK UPDATE using SQLAlchemy =====
            if to_update:
                chunk_size = 1000
                for i in range(0, len(to_update), chunk_size):
                    chunk = to_update[i:i+chunk_size]
                    
                    for student_data in chunk:
                        # Update each student individually but in same transaction
                        db.session.query(CtuStudent)\
                            .filter(CtuStudent.student_number == student_data['student_number'])\
                            .update({
                                'first_name': student_data['first_name'],
                                'last_name': student_data['last_name']
                            }, synchronize_session=False)
                    
                    db.session.flush()
                    print(f"   Updated chunk {i//chunk_size + 1}/{(len(to_update)-1)//chunk_size + 1}")
            
            print(f"📊 STEP 7: Completed updates in {time.time() - start_time:.2f}s")

            # ===== OPTIMIZATION 5: Handle deletions =====
            # Find students to delete (in DB but not in Excel)
            to_delete_ctu = []
            to_delete_registered = []
            
            for student_no, existing in existing_ctu.items():
                if student_no not in excel_student_nos:
                    to_delete_ctu.append(student_no)
                    
                    # Check if registered
                    if student_no in registered_map and not registered_map[student_no]['has_voted']:
                        to_delete_registered.append(registered_map[student_no]['id'])
            
            deleted_from_ctu = len(to_delete_ctu)
            deleted_from_registration = 0
            
            # Bulk delete CTU students
            if to_delete_ctu:
                chunk_size = 500
                for i in range(0, len(to_delete_ctu), chunk_size):
                    chunk = to_delete_ctu[i:i+chunk_size]
                    db.session.query(CtuStudent)\
                        .filter(CtuStudent.student_number.in_(chunk))\
                        .delete(synchronize_session=False)
                    db.session.flush()
            
            print(f"📊 STEP 8: Deleted {deleted_from_ctu} CTU students in {time.time() - start_time:.2f}s")
            
            # Bulk delete registered students (with no votes)
            if to_delete_registered:
                # First delete TrustedDevice records
                chunk_size = 500
                for i in range(0, len(to_delete_registered), chunk_size):
                    chunk = to_delete_registered[i:i+chunk_size]
                    from student.models import TrustedDevice
                    db.session.query(TrustedDevice)\
                        .filter(TrustedDevice.student_id.in_(chunk))\
                        .delete(synchronize_session=False)
                    db.session.flush()
                
                # Then delete students
                for i in range(0, len(to_delete_registered), chunk_size):
                    chunk = to_delete_registered[i:i+chunk_size]
                    db.session.query(Student)\
                        .filter(Student.id.in_(chunk))\
                        .delete(synchronize_session=False)
                    db.session.flush()
                
                deleted_from_registration = len(to_delete_registered)
            
            print(f"📊 STEP 9: Deleted {deleted_from_registration} registered students in {time.time() - start_time:.2f}s")
            
            # ===== OPTIMIZATION 6: Commit once at the end =====
            db.session.commit()
            
            total_time = time.time() - start_time
            print(f"✅ TOTAL TIME: {total_time:.2f} seconds for {len(excel_data)} students")
            
            # Audit log
            username = getattr(current_user, 'username', 'Unknown') if current_user.is_authenticated else 'Unknown'
            ip = request.remote_addr
            filename = file.filename if file else 'Unknown'
            
            log_audit(
                action='IMPORT_STUDENTS',
                description=f"Admin user '{username}' imported students from '{filename}' from IP: {ip} | Imported: {len(to_insert)}, Updated: {len(to_update)}, Deleted from CTU: {deleted_from_ctu}, Deleted registered: {deleted_from_registration}, Time: {total_time:.2f}s"
            )

            flash(
                f"✅ Sync complete in {total_time:.1f}s!\n"
                f"📥 Imported: {len(to_insert)}\n"
                f"🔄 Updated: {len(to_update)}\n"
                f"🗑️ Removed from CTU list: {deleted_from_ctu}\n"
                f"🚫 Removed registered students: {deleted_from_registration}",
                "import-success"
            )
            
            return redirect(url_for("admin.import_students"))

        except Exception as e:
            db.session.rollback()
            print(f"❌ ERROR: {str(e)}")
            print(f"❌ ERROR after {time.time() - start_time:.2f} seconds")
            
            # Clean up temp file if it exists
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            
            flash(f"Error importing file: {str(e)}", "import-danger")
            return redirect(url_for("admin.import_students"))

    # ------------------ GET ------------------
    page = request.args.get("page", 1, type=int)
    search_query = request.args.get("q", "", type=str)

    students_query = CtuStudent.query

    if search_query:
        search = f"%{search_query.strip()}%"
        students_query = students_query.filter(
            or_(
                CtuStudent.student_number.ilike(search),
                CtuStudent.first_name.ilike(search),
                CtuStudent.last_name.ilike(search)
            )
        )

    students = students_query.order_by(CtuStudent.last_name.asc()) \
        .paginate(page=page, per_page=20, error_out=False)

    # ------------------ TOTAL STUDENTS ------------------
    total_students = CtuStudent.query.count()

    # ---------- AUDIT LOG: Import students page viewed ----------
    if request.method == "GET" and current_user.is_authenticated:
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        log_audit(
            action='IMPORT_STUDENTS_VIEW',
            description=f"Admin user '{username}' viewed the import students page from IP: {ip}"
        )

    return render_template(
        "import_students.html",
        students=students,
        total_students=total_students
    )


    # ------------------ GET ------------------
    page = request.args.get("page", 1, type=int)
    search_query = request.args.get("q", "", type=str)

    students_query = CtuStudent.query

    if search_query:
        search = f"%{search_query.strip()}%"
        students_query = students_query.filter(
            or_(
                CtuStudent.student_number.ilike(search),
                CtuStudent.first_name.ilike(search),
                CtuStudent.last_name.ilike(search)
            )
        )

    students = students_query.order_by(CtuStudent.last_name.asc()) \
        .paginate(page=page, per_page=20, error_out=False)

    # ------------------ TOTAL STUDENTS ------------------
    total_students = CtuStudent.query.count()

    # ---------- AUDIT LOG: Import students page viewed ----------
    if request.method == "GET" and current_user.is_authenticated:
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        log_audit(
            action='IMPORT_STUDENTS_VIEW',
            description=f"Admin user '{username}' viewed the import students page from IP: {ip}"
        )

    return render_template(
        "import_students.html",
        students=students,
        total_students=total_students
    )



# Add this import with your other imports at the top of admin/routes.py
from admin.utils import sync_registered_students_with_ctu

@admin_bp.route('/sync-registered-students', methods=['POST'])
@admin_required
def sync_registered_students():
    """Manual sync endpoint"""
    try:
        result = sync_registered_students_with_ctu()
        return jsonify({
            'success': True,
            'deleted': result['deleted'],
            'kept_with_votes': result['kept_with_votes']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# import_students_table function remains EXACTLY THE SAME - no changes needed
@admin_bp.route("/import_students_table")
def import_students_table():
    from flask import request, render_template
    from sqlalchemy import or_
    from admin.models import CtuStudent

    try:
        page = request.args.get("page", 1, type=int)
        search_query = request.args.get("q", "", type=str)

        students_query = CtuStudent.query

        if search_query:
            search = f"%{search_query.strip()}%"
            students_query = students_query.filter(
                or_(
                    CtuStudent.student_number.ilike(search),
                    CtuStudent.first_name.ilike(search),
                    CtuStudent.last_name.ilike(search)
                )
            )

        # Prevent paginate error if page > total_pages
        students = students_query.order_by(CtuStudent.last_name.asc()) \
                                 .paginate(page=page, per_page=20, error_out=False)

        # Ensure string comparison
        student_numbers = [str(s.student_number) for s in students.items]
        if student_numbers:
            registered_students = Student.query.filter(
                Student.id_number.in_(student_numbers)
            ).all()
            registered_numbers = set(str(s.id_number) for s in registered_students)
        else:
            registered_numbers = set()

        # ---------- AUDIT LOG: Import students table AJAX request ----------
        if current_user.is_authenticated:
            username = getattr(current_user, 'username', 'Unknown')
            ip = request.remote_addr
            search_term = search_query if search_query else 'none'
            
            log_audit(
                action='IMPORT_STUDENTS_TABLE_VIEW',
                description=f"Admin user '{username}' viewed/refreshed import students table from IP: {ip} | Page: {page}, Search: '{search_term}'"
            )

        return render_template(
            "partials/_students_table.html",
            students=students,
            registered_numbers=registered_numbers
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        
        # ---------- AUDIT LOG: Import students table error ----------
        if current_user.is_authenticated:
            username = getattr(current_user, 'username', 'Unknown')
            ip = request.remote_addr
            
            log_audit(
                action='IMPORT_STUDENTS_TABLE_ERROR',
                description=f"Admin user '{username}' encountered error viewing import students table from IP: {ip} | Error: {str(e)[:100]}..."
            )
        
        # Return a simple HTML message instead of plain text, for AJAX
        return render_template(
            "partials/_students_table.html",
            students=None,
            registered_numbers=set()
        )

@admin_bp.route('/students')
@admin_required
def manage_students():
    # Get school year filter from session (set by dashboard) - ONLY FOR ELECTIONS DROPDOWN
    school_year = session.get('admin_current_school_year')
    
    # Parse school year to date range for elections filtering
    start_date = None
    end_date = None
    if school_year:
        try:
            start_year = int(school_year.split('-')[0])
            end_year = int(school_year.split('-')[1])
            start_date = datetime(start_year, 1, 1)
            end_date = datetime(end_year, 12, 31)
        except (ValueError, IndexError):
            start_date = None
            end_date = None
    
    # -------------------- Fetch Departments & Courses -------------------- #
    departments = Department.query.order_by(Department.name).all()
    courses = Course.query.order_by(Course.course_name).all()

    departments_data = [{"id": d.id, "name": d.name} for d in departments]
    courses_data = [{"id": c.id, "name": c.course_name} for c in courses]

    # -------------------- Fetch Elections with scope - FILTERED BY SCHOOL YEAR -------------------- #
    election_query = Election.query.order_by(Election.start_date.desc())
    
    # Apply school year filter to elections ONLY
    if start_date and end_date:
        election_query = election_query.filter(
            Election.start_date >= start_date,
            Election.start_date <= end_date
        )
    
    elections = election_query.all()
    elections_data = [{
        "id": e.id, 
        "title": e.title,
        "scope": e.scope,
        "year_levels": e.year_levels  # Include year_levels for display
    } for e in elections]

    # ---------- AUDIT LOG: Manage Students page viewed ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    school_year_info = f" | School Year: {school_year}" if school_year else ""
    
    log_audit(
        action='MANAGE_STUDENTS_VIEW',
        description=f"Admin user '{username}' viewed the manage students page from IP: {ip}{school_year_info} | Elections available: {len(elections)}"
    )

    # -------------------- Render Template -------------------- #
    return render_template(
        'manage_students.html',
        departments=departments_data,
        courses=courses_data,
        elections=elections_data,
        current_sy=school_year  # Pass current school year to template
    )


from sqlalchemy import or_, func

# ---------------------- AJAX STUDENT DATA (with voting status) ---------------------- #
@admin_bp.route('/students/data')
@admin_required
def students_data():
    filter_type = request.args.get('filter_type', 'all')
    filter_id = request.args.get('filter_id')
    search = request.args.get('search', '')
    election_id = request.args.get('election_id')  # Selected election
    page = int(request.args.get('page', 1))
    per_page = 10

    query = Student.query

    # Apply filters
    if filter_type == 'department' and filter_id:
        query = query.filter(Student.department_id == int(filter_id))

    if filter_type == 'course' and filter_id:
        query = query.filter(Student.course_id == int(filter_id))

    # Apply search
    if search:
        query = query.filter(
            or_(
                Student.id_number.ilike(f'%{search}%'),
                Student.first_name.ilike(f'%{search}%'),
                Student.last_name.ilike(f'%{search}%'),
                func.coalesce(Student.course, '').ilike(f'%{search}%')
            )
        )

    # Get election details if selected
    election = None
    if election_id and election_id != "all":
        election = Election.query.get(int(election_id))
        
        # 🎯 Filter students based on election's year levels (but not by school year)
        if election and election.scope == 'campus' and election.year_levels:
            # Join with year_level to filter by year
            if election.year_levels != 'all':
                # Get list of allowed year levels
                allowed_years = election.year_levels.split(',')
                
                # Filter students whose year_level_id matches allowed years
                query = query.filter(Student.year_level_id.in_(allowed_years))
            
        # 🎯 For department elections, filter by department
        elif election and election.scope == 'department' and election.department_id:
            query = query.filter(Student.department_id == election.department_id)

    # Pagination
    pagination = query.order_by(Student.last_name).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Convert students to simple dicts
    students = []
    for s in pagination.items:
        # Check voting status if election_id is provided
        has_voted = False
        if election_id and election_id != "all":
            has_voted = Vote.query.filter_by(student_id=s.id, election_id=int(election_id)).first() is not None

        # Get year level name if available
        year_level_name = ""
        if s.year_level:
            year_level_name = s.year_level.year_name

        students.append({
            "id": s.id,
            "id_number": s.id_number,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "course": s.course,
            "year_level": year_level_name,
            "year_level_id": s.year_level_id,
            "has_voted": has_voted
        })

    # Log the filter info for debugging
    current_app.logger.info(f"Students data - Election: {election_id}, Total students: {len(students)}")

    # ---------- AUDIT LOG: Student data AJAX request ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='STUDENTS_DATA_VIEW',
        description=f"Admin user '{username}' fetched student data via AJAX from IP: {ip} | Election: {election_id}, Filter: {filter_type}, Search: '{search}', Page: {page}"
    )

    return jsonify({
        "students": students,
        "total_pages": pagination.pages,
        "current_page": pagination.page
    })
   

@admin_bp.route('/students/export-excel')
@admin_required
def export_students_excel():
    # ------------------- GET FILTERS ------------------- #
    filter_type = request.args.get('filter_type', 'all')
    filter_id = request.args.get('filter_id')
    search = request.args.get('search', '')
    election_id = request.args.get('election_id')

    # ------------------- QUERY STUDENTS ------------------- #
    query = Student.query

    if filter_type == 'department' and filter_id:
        query = query.filter(Student.department_id == int(filter_id))
    if filter_type == 'course' and filter_id:
        query = query.filter(Student.course_id == int(filter_id))
    if search:
        query = query.filter(
            or_(
                Student.id_number.ilike(f'%{search}%'),
                Student.first_name.ilike(f'%{search}%'),
                Student.last_name.ilike(f'%{search}%'),
                Student.course.ilike(f'%{search}%')
            )
        )

    # Get election details if selected
    election = None
    if election_id and election_id != "all":
        election = Election.query.get(int(election_id))
        
        # 🎯 NEW: Filter students based on election's year levels
        if election and election.scope == 'campus' and election.year_levels:
            if election.year_levels != 'all':
                # Filter by allowed year levels
                allowed_years = election.year_levels.split(',')
                query = query.filter(Student.year_level_id.in_(allowed_years))
        
        # 🎯 NEW: For department elections, filter by department
        elif election and election.scope == 'department' and election.department_id:
            query = query.filter(Student.department_id == election.department_id)

    students = query.order_by(Student.last_name).all()

    # ------------------- FETCH SELECTED ELECTION ------------------- #
    election = None
    if election_id and election_id != "all":
        election = Election.query.get(int(election_id))

    # ------------------- CREATE EXCEL ------------------- #
    wb = Workbook()
    ws = wb.active
    ws.title = "Students"

    # ------------------- HEADER STYLES ------------------- #
    mustard_fill = PatternFill(start_color='F1C40F', end_color='F1C40F', fill_type='solid')
    header_font = Font(name='Calibri', bold=True, color='FFFFFF')
    center_alignment = Alignment(horizontal='center', vertical='center')

    max_col = 6  # A–F

    # ------------------- HEADER ROWS ------------------- #
    # Row 1: Election Title with Year Info
    election_title = f"{election.title if election else 'All Elections'}"
    if election and election.scope == 'campus' and election.year_levels:
        if election.year_levels == 'all':
            election_title += " (All Years)"
        else:
            election_title += f" (Year {election.year_levels})"
    
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
    ws.cell(row=1, column=1, value=election_title)
    ws.cell(row=1, column=1).font = header_font
    ws.cell(row=1, column=1).fill = mustard_fill
    ws.cell(row=1, column=1).alignment = center_alignment

    # Row 2: Department / All
    department_text = "-"
    if filter_type == "department" and filter_id:
        dept_obj = Department.query.get(int(filter_id))
        if dept_obj:
            department_text = dept_obj.name
    elif election and election.department:
        department_text = election.department
    elif election and election.scope == 'campus':
        department_text = "Campus-Wide"

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max_col)
    ws.cell(row=2, column=1, value=f"Department: {department_text}")
    ws.cell(row=2, column=1).font = header_font
    ws.cell(row=2, column=1).fill = mustard_fill
    ws.cell(row=2, column=1).alignment = center_alignment

    # Row 3: Course / All
    course_text = "-"
    if filter_type == "course" and filter_id:
        course_obj = Course.query.get(int(filter_id))
        if course_obj:
            course_text = course_obj.course_name
    elif election and election.course_rel:
        course_text = election.course_rel.course_name

    # Add year level info to row 3
    if election and election.scope == 'campus' and election.year_levels:
        if election.year_levels == 'all':
            course_text += " | Target: All Year Levels"
        else:
            course_text += f" | Target: Year {election.year_levels}"

    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=max_col)
    ws.cell(row=3, column=1, value=f"Course: {course_text}")
    ws.cell(row=3, column=1).font = header_font
    ws.cell(row=3, column=1).fill = mustard_fill
    ws.cell(row=3, column=1).alignment = center_alignment

    # ------------------- COLUMN HEADERS ------------------- #
    headers = ["Student ID", "First Name", "Last Name", "Course", "Year Level", "Status"]
    for col_num, header in enumerate(headers, start=1):
        cell = ws.cell(row=4, column=col_num, value=header)
        cell.font = Font(name='Calibri', bold=True, color='FFFFFF')
        cell.fill = PatternFill(start_color='2980b9', end_color='2980b9', fill_type='solid')
        cell.alignment = center_alignment

    # ------------------- ADD STUDENTS ------------------- #
    for idx, s in enumerate(students, start=5):
        has_voted = False
        if election:
            has_voted = Vote.query.filter_by(student_id=s.id, election_id=election.id).first() is not None
        status_text = "Voted" if has_voted else "Not Voted"

        # Get year level name
        year_level_name = ""
        if s.year_level:
            year_level_name = s.year_level.year_name

        row_values = [
            s.id_number,
            s.first_name,
            s.last_name,
            s.course,
            year_level_name,
            status_text
        ]

        for col_num, value in enumerate(row_values, start=1):
            cell = ws.cell(row=idx, column=col_num, value=value)
            cell.alignment = Alignment(horizontal='left', vertical='center')
            if col_num == 6:  # Status column
                if has_voted:
                    cell.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
                    cell.font = Font(color='006100')
                else:
                    cell.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
                    cell.font = Font(color='9C0006')

    # ------------------- AUTO FIT COLUMNS ------------------- #
    for col in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)) + 2)
        ws.column_dimensions[col_letter].width = max_length

    # ---------- AUDIT LOG: Export students Excel ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    student_count = len(students)
    election_name = election.title if election else 'All Elections'
    
    log_audit(
        action='EXPORT_STUDENTS_EXCEL',
        description=f"Admin user '{username}' exported {student_count} students to Excel from IP: {ip} | Election: {election_name}, Filter: {filter_type}, Search: '{search}'"
    )

    # ------------------- RETURN EXCEL ------------------- #
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return Response(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=students.xlsx"}
    )

# ---------------------- DELETE STUDENT ---------------------- #
@admin_bp.route('/students/delete/<int:id>', methods=['POST'])
@admin_required
def delete_student(id):
    student = Student.query.get_or_404(id)
    
    # Store student info before deletion for audit log
    student_name = f"{student.first_name} {student.last_name}"
    student_id_number = student.id_number
    
    db.session.delete(student)
    db.session.commit()
    
    # ---------- AUDIT LOG: Delete student ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='DELETE_STUDENT',
        description=f"Admin user '{username}' deleted student: {student_name} (ID: {student_id_number}) from IP: {ip}"
    )
    
    return jsonify({"success": True})


from student.models import DeletionRequest
# Add these routes to your admin routes file

@admin_bp.route('/deletion-requests')
def account_deletion_requests():
    """Render the account deletion requests page"""
    return render_template('account_deletion_requests.html')

@admin_bp.route('/deletion-requests/data')
def get_deletion_requests_data():
    """Get paginated deletion requests data for AJAX"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    search = request.args.get('search', '')
    date = request.args.get('date', '')
    
    per_page = 10
    query = DeletionRequest.query
    
    # Apply filters
    if status != 'all':
        query = query.filter(DeletionRequest.status == status)
    
    if search:
        query = query.join(Student).filter(
            db.or_(
                Student.first_name.ilike(f'%{search}%'),
                Student.last_name.ilike(f'%{search}%'),
                Student.id_number.ilike(f'%{search}%')
            )
        )
    
    if date:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        query = query.filter(
            db.func.date(DeletionRequest.request_date) == date_obj.date()
        )
    
    # Order by most recent first
    query = query.order_by(DeletionRequest.request_date.desc())
    
    # Paginate
    paginated = query.paginate(page=page, per_page=per_page)
    
    # Format data for response
    requests_data = []
    for req in paginated.items:
        requests_data.append({
            'id': req.id,
            'student_name': f"{req.student.first_name} {req.student.last_name}",
            'student_id_number': req.student.id_number,
            'reason': req.reason,
            'request_date': req.request_date.isoformat(),
            'status': req.status,
            'processed_by_name': req.admin.username if req.admin else None
        })
    
    return jsonify({
        'requests': requests_data,
        'total_pages': paginated.pages,
        'current_page': page
    })

@admin_bp.route('/deletion-requests/stats')
def get_deletion_requests_stats():
    """Get statistics for deletion requests"""
    total = DeletionRequest.query.count()
    pending = DeletionRequest.query.filter_by(status='pending').count()
    approved = DeletionRequest.query.filter_by(status='approved').count()
    rejected = DeletionRequest.query.filter_by(status='rejected').count()
    
    return jsonify({
        'total': total,
        'pending': pending,
        'approved': approved,
        'rejected': rejected
    })

@admin_bp.route('/deletion-requests/<int:request_id>')
def get_deletion_request(request_id):
    """Get details of a specific deletion request"""
    req = DeletionRequest.query.get_or_404(request_id)
    
    return jsonify({
        'id': req.id,
        'student_name': f"{req.student.first_name} {req.student.last_name}",
        'student_id_number': req.student.id_number,
        'reason': req.reason,
        'request_date': req.request_date.isoformat(),
        'status': req.status,
        'admin_notes': req.admin_notes,
        'processed_by_name': req.admin.username if req.admin else None,
        'processed_date': req.processed_date.isoformat() if req.processed_date else None
    })

@admin_bp.route('/deletion-requests/<int:request_id>/process', methods=['POST'])
def process_deletion_request(request_id):
    """Approve or reject a deletion request"""
    req = DeletionRequest.query.get_or_404(request_id)
    data = request.get_json()
    
    action = data.get('action')
    admin_notes = data.get('admin_notes', '')
    
    if action not in ['approve', 'reject']:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400
    
    # Update request
    req.status = 'approved' if action == 'approve' else 'rejected'
    req.admin_notes = admin_notes
    req.processed_date = datetime.utcnow()
    req.processed_by = current_admin.id  # Assuming you have current_admin
    
    # If approved, you might want to delete the student account
    if action == 'approve':
        # Option 1: Actually delete the student
        # db.session.delete(req.student)
        
        # Option 2: Just mark as approved and handle separately
        pass
    
    db.session.commit()
    
    return jsonify({'success': True})



# ---------------------- Departments & Courses ---------------------- #
@admin_bp.route('/departments')
@admin_required
def manage_departments():
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM departments ORDER BY name")
    departments = cursor.fetchall()

    cursor.execute("""
        SELECT c.*, d.name AS department_name
        FROM courses c
        JOIN departments d ON c.department_id = d.id
        ORDER BY d.name, c.course_name
    """)
    courses = cursor.fetchall()

    cursor.close()
    connection.close()
    
    # ---------- AUDIT LOG: Manage Departments page viewed ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='MANAGE_DEPARTMENTS_VIEW',
        description=f"Admin user '{username}' viewed the departments & courses page from IP: {ip} | Total Departments: {len(departments)}, Total Courses: {len(courses)}"
    )

    return render_template('manage_departments.html', departments=departments, courses=courses)


# --- Department routes ---
@admin_bp.route('/departments/add', methods=['POST'])
@admin_required
def add_department():
    name = request.form['name'].strip()
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = connection.cursor()
    cursor.execute("INSERT INTO departments (name) VALUES (%s)", (name,))
    connection.commit()
    cursor.close()
    connection.close()

    # ---------- AUDIT LOG: Add department ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='ADD_DEPARTMENT',
        description=f"Admin user '{username}' added new department: '{name}' from IP: {ip}"
    )

    flash('Department added successfully', 'success')
    return redirect(url_for('admin.manage_departments'))  # <-- fixed


@admin_bp.route('/departments/delete-multiple', methods=['POST'])
@admin_required
def delete_multiple_departments():
    ids = request.form.getlist('department_ids')
    if ids:
        # Get department names before deletion for audit log
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        cursor = connection.cursor(dictionary=True)
        format_strings = ','.join(['%s'] * len(ids))
        cursor.execute(f"SELECT id, name FROM departments WHERE id IN ({format_strings})", tuple(ids))
        departments_to_delete = cursor.fetchall()
        department_names = [d['name'] for d in departments_to_delete]
        
        # Delete departments
        cursor.execute(f"DELETE FROM departments WHERE id IN ({format_strings})", tuple(ids))
        connection.commit()
        cursor.close()
        connection.close()
        
        # ---------- AUDIT LOG: Delete multiple departments ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        log_audit(
            action='DELETE_MULTIPLE_DEPARTMENTS',
            description=f"Admin user '{username}' deleted {len(ids)} department(s) from IP: {ip} | Departments: {', '.join(department_names)} (IDs: {', '.join(ids)})"
        )
        
        flash(f'{len(ids)} department(s) deleted successfully!', 'success')
    else:
        # ---------- AUDIT LOG: Attempted delete with no selection ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        log_audit(
            action='DELETE_DEPARTMENTS_NO_SELECTION',
            description=f"Admin user '{username}' attempted to delete departments but no selection was made from IP: {ip}"
        )
        
        flash('No departments selected for deletion.', 'warning')
    return redirect(url_for('admin.manage_departments'))  # <-- fixed


# --- Course routes ---
@admin_bp.route('/courses/add', methods=['POST'])
@admin_required
def add_course():
    course_name = request.form['course_name'].strip()
    department_id = request.form['department_id']

    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO courses (course_name, department_id) VALUES (%s, %s)",
        (course_name, department_id)
    )
    connection.commit()
    
    # Get department name for audit log
    cursor.execute("SELECT name FROM departments WHERE id = %s", (department_id,))
    department_result = cursor.fetchone()
    department_name = department_result[0] if department_result else 'Unknown'
    
    cursor.close()
    connection.close()

    # ---------- AUDIT LOG: Add course ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='ADD_COURSE',
        description=f"Admin user '{username}' added new course: '{course_name}' to department: '{department_name}' (ID: {department_id}) from IP: {ip}"
    )

    flash('Course added successfully', 'success')
    return redirect(url_for('admin.manage_departments'))  # <-- fixed


@admin_bp.route('/courses/delete-multiple', methods=['POST'])
@admin_required
def delete_multiple_courses():
    ids = request.form.getlist('course_ids')
    if ids:
        # Get course names and department info before deletion for audit log
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        cursor = connection.cursor(dictionary=True)
        format_strings = ','.join(['%s'] * len(ids))
        cursor.execute(f"""
            SELECT c.id, c.course_name, d.name AS department_name 
            FROM courses c
            JOIN departments d ON c.department_id = d.id
            WHERE c.id IN ({format_strings})
        """, tuple(ids))
        courses_to_delete = cursor.fetchall()
        course_names = [f"{c['course_name']} ({c['department_name']})" for c in courses_to_delete]
        
        # Delete courses
        cursor.execute(f"DELETE FROM courses WHERE id IN ({format_strings})", tuple(ids))
        connection.commit()
        cursor.close()
        connection.close()
        
        # ---------- AUDIT LOG: Delete multiple courses ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        log_audit(
            action='DELETE_MULTIPLE_COURSES',
            description=f"Admin user '{username}' deleted {len(ids)} course(s) from IP: {ip} | Courses: {', '.join(course_names)} (IDs: {', '.join(ids)})"
        )
        
        flash(f'{len(ids)} course(s) deleted successfully!', 'success')
    else:
        # ---------- AUDIT LOG: Attempted delete with no selection ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        log_audit(
            action='DELETE_COURSES_NO_SELECTION',
            description=f"Admin user '{username}' attempted to delete courses but no selection was made from IP: {ip}"
        )
        
        flash('No courses selected for deletion.', 'warning')
    return redirect(url_for('admin.manage_departments'))  # <-- fixed



# ---------------------- MANAGE CANDIDATES ---------------------- #
# ---------------------- MANAGE CANDIDATES ---------------------- #
@admin_bp.route('/candidates', methods=['GET', 'POST'])
@admin_required
def manage_candidates():
    # Get school year filter from session (set by dashboard)
    school_year = session.get('admin_current_school_year')
    
    # Parse school year to date range
    start_date = None
    end_date = None
    if school_year:
        try:
            start_year = int(school_year.split('-')[0])
            end_year = int(school_year.split('-')[1])
            start_date = datetime(start_year, 1, 1)
            end_date = datetime(end_year, 12, 31)
        except (ValueError, IndexError):
            start_date = None
            end_date = None
    
    # Get positions, departments (these are not filtered by school year)
    positions = Position.query.all()
    departments = Department.query.order_by(Department.name).all()
    
    # Filter elections by school year if set
    election_query = Election.query.order_by(Election.start_date.desc())
    if start_date and end_date:
        election_query = election_query.filter(
            Election.start_date >= start_date,
            Election.start_date <= end_date
        )
    elections = election_query.all()

    # ================= FILTER =================
    selected_scope = request.args.get('scope', default=None)
    department_id = request.args.get('department_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 10
    selected_department = None

    query = Candidate.query

    # Filter by school year through elections
    if start_date and end_date:
        # Get election IDs within the school year
        election_ids = [e.id for e in elections]
        if election_ids:
            query = query.filter(Candidate.election_id.in_(election_ids))
        else:
            # No elections in this school year, return empty result
            query = query.filter(False)  # This will return no candidates

    # Filter by scope
    if selected_scope:
        query = query.filter(Candidate.scope == selected_scope)

    # Filter by department
    if selected_scope == 'department' and department_id:
        selected_department = Department.query.get(department_id)
        if selected_department:
            query = query.filter(Candidate.department_id == department_id)

    # ---------------- PAGINATE ----------------
    candidates_pagination = query.order_by(Candidate.id.desc()).paginate(page=page, per_page=per_page)
    candidates = candidates_pagination.items
    # ==========================================

    # ---------- ADD CANDIDATE ----------
    if request.method == 'POST':
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        party_list = request.form.get('party_list')
        platform = request.form.get('platform')  # NEW: Add platform field
        department_id_form = request.form.get('department_id', type=int)
        course_id = request.form.get('course_id', type=int)  # NEW: Add course_id field
        position_id = request.form.get('position_id')
        election_id = request.form.get('election_id')
        scope = request.form.get('scope')  # Get scope from form

        # Get election to verify
        election = Election.query.get(election_id)
        if not election:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Selected election does not exist.'})
            flash('Selected election does not exist.', 'danger')
            return redirect(url_for('admin.manage_candidates'))

        # Validate required fields
        if not all([first_name, last_name, position_id, election_id, scope]):
            if is_ajax:
                return jsonify({'success': False, 'message': 'Please fill in all required fields.'})
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('admin.manage_candidates'))

        # Validate department based on scope (but department is now optional)
        if scope == 'department' and not department_id_form:
            # Department is optional now, so we don't require it
            # Just set department_id_form to None if not provided
            department_id_form = None

        # Save photo if uploaded
        photo_file = request.files.get('photo')
        photo_filename = None
        photo_folder = os.path.join(current_app.root_path, 'admin', 'static', 'images')
        os.makedirs(photo_folder, exist_ok=True)

        if photo_file and photo_file.filename:
            filename = secure_filename(photo_file.filename)
            name, ext = os.path.splitext(filename)
            photo_filename = f"{name}_{int(time.time())}{ext}"
            photo_file.save(os.path.join(photo_folder, photo_filename))

        # Create candidate with new fields
        new_candidate = Candidate(
            first_name=first_name,
            last_name=last_name,
            party_list=party_list if party_list else None,
            platform=platform if platform else None,  # NEW: Add platform
            department_id=department_id_form,
            course_id=course_id,  # NEW: Add course_id
            position_id=position_id,
            election_id=election_id,
            scope=scope,  # Save scope directly
            photo=photo_filename
        )

        db.session.add(new_candidate)
        db.session.commit()

        # Audit log
        department_name = new_candidate.department.name if new_candidate.department else 'N/A'
        position_name = new_candidate.position.name if new_candidate.position else 'N/A'
        election_title = new_candidate.election.title if new_candidate.election else 'N/A'
        party_list_name = new_candidate.party_list if new_candidate.party_list else 'Independent'
        
        school_year_info = f" | School Year: {school_year}" if school_year else ""
        
        log_audit(
            action='CREATE_CANDIDATE',
            description=f"Added candidate: {first_name} {last_name} | Party: {party_list_name} | Position: {position_name} | Department: {department_name} | Election: {election_title} ({scope}){school_year_info}"
        )

        # Return JSON for AJAX requests
        if is_ajax:
            return jsonify({
                'success': True,
                'message': 'Candidate added successfully!',
                'id': new_candidate.id,
                'first_name': new_candidate.first_name,
                'last_name': new_candidate.last_name,
                'party_list': new_candidate.party_list,
                'platform': new_candidate.platform,
                'department': new_candidate.department.name if new_candidate.department else '',
                'department_id': new_candidate.department_id,
                'course_id': new_candidate.course_id,
                'position': new_candidate.position.name,
                'position_id': new_candidate.position_id,
                'election_id': new_candidate.election_id,
                'scope': new_candidate.scope,
                'photo': url_for('admin.static', filename='images/' + new_candidate.photo) if new_candidate.photo else None
            })

        flash('Candidate added successfully!', 'success')
        return redirect(url_for('admin.manage_candidates'))

    # Filter elections for modals
    campus_elections = [e for e in elections if e.scope == 'campus']
    department_elections = [e for e in elections if e.scope == 'department']

    return render_template(
        'manage_candidates.html',
        candidates=candidates,
        candidates_pagination=candidates_pagination,
        positions=positions,
        departments=departments,
        elections=elections,
        campus_elections=campus_elections,
        department_elections=department_elections,
        selected_department=selected_department,
        selected_scope=selected_scope,
        current_sy=school_year  # Pass current school year to template
    )



@admin_bp.route('/candidates/filter', methods=['GET'])
@admin_required
def filter_candidates():
    """AJAX endpoint for filtering candidates"""
    # Get school year filter from session
    school_year = session.get('admin_current_school_year')
    
    # Parse school year to date range
    start_date = None
    end_date = None
    if school_year:
        try:
            start_year = int(school_year.split('-')[0])
            end_year = int(school_year.split('-')[1])
            start_date = datetime(start_year, 1, 1)
            end_date = datetime(end_year, 12, 31)
        except (ValueError, IndexError):
            start_date = None
            end_date = None
    
    selected_scope = request.args.get('scope', default=None)
    department_id = request.args.get('department_id', type=int)
    search = request.args.get('search', default='')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = Candidate.query

    # Filter by school year through elections
    if start_date and end_date:
        # Get elections within the school year
        election_query = Election.query.filter(
            Election.start_date >= start_date,
            Election.start_date <= end_date
        )
        election_ids = [e.id for e in election_query.all()]
        if election_ids:
            query = query.filter(Candidate.election_id.in_(election_ids))
        else:
            # No elections in this school year, return empty result
            candidates_data = []
            return jsonify({
                'candidates': candidates_data,
                'pagination': {
                    'current_page': 1,
                    'total_pages': 1,
                    'total_items': 0,
                    'has_prev': False,
                    'has_next': False,
                    'prev_page': None,
                    'next_page': None
                },
                'current_sy': school_year
            })

    # Filter by scope
    if selected_scope:
        query = query.filter(Candidate.scope == selected_scope)

    # Filter by department
    if selected_scope == 'department' and department_id:
        query = query.filter(Candidate.department_id == department_id)

    # Search functionality
    if search:
        search_term = f'%{search}%'
        query = query.join(Position).join(Election, isouter=True).filter(
            db.or_(
                Candidate.first_name.ilike(search_term),
                Candidate.last_name.ilike(search_term),
                Candidate.party_list.ilike(search_term),
                Candidate.platform.ilike(search_term),  # NEW: Add platform to search
                Position.name.ilike(search_term),
                Election.title.ilike(search_term)
            )
        )

    # Paginate
    pagination = query.order_by(Candidate.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    candidates = pagination.items

    # Format candidates for JSON response
    candidates_data = []
    for c in candidates:
        candidates_data.append({
            'id': c.id,
            'first_name': c.first_name,
            'last_name': c.last_name,
            'party_list': c.party_list,
            'platform': c.platform,  # NEW: Add platform to response
            'department': c.department.name if c.department else '',
            'department_id': c.department_id,
            'course_id': c.course_id,  # NEW: Add course_id to response
            'position': c.position.name if c.position else '',
            'position_id': c.position_id,
            'election_id': c.election_id,
            'election_title': c.election.title if c.election else '',
            'scope': c.scope,
            'photo': url_for('admin.static', filename='images/' + c.photo) if c.photo else None
        })

    return jsonify({
        'candidates': candidates_data,
        'pagination': {
            'current_page': pagination.page,
            'total_pages': pagination.pages,
            'total_items': pagination.total,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next,
            'prev_page': pagination.prev_num if pagination.has_prev else None,
            'next_page': pagination.next_num if pagination.has_next else None
        },
        'current_sy': school_year
    })



@admin_bp.route('/candidates/edit/<int:id>', methods=['POST'])
@admin_required
def update_candidate(id):
    candidate = Candidate.query.get_or_404(id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Store old values
    old_first_name = candidate.first_name
    old_last_name = candidate.last_name
    old_party_list = candidate.party_list
    old_platform = candidate.platform  # NEW
    old_position = candidate.position.name if candidate.position else 'N/A'
    old_department = candidate.department.name if candidate.department else 'N/A'
    old_scope = candidate.scope

    # Get form data
    candidate.first_name = request.form.get('first_name')
    candidate.last_name = request.form.get('last_name')
    
    party_list = request.form.get('party_list')
    candidate.party_list = party_list if party_list else None
    
    platform = request.form.get('platform')  # NEW
    candidate.platform = platform if platform else None  # NEW
    
    candidate.position_id = request.form.get('position_id')
    candidate.election_id = request.form.get('election_id')
    
    scope = request.form.get('scope')
    candidate.scope = scope  # Update scope
    
    department_id = request.form.get('department_id', type=int)
    course_id = request.form.get('course_id', type=int)  # NEW
    
    candidate.department_id = department_id if department_id else None
    candidate.course_id = course_id if course_id else None  # NEW
    
    # Get election to verify
    election = Election.query.get(candidate.election_id)
    
    # Handle photo upload
    photo_file = request.files.get('photo')
    if photo_file and photo_file.filename:
        filename = secure_filename(photo_file.filename)
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(time.time())}{ext}"
        
        photo_folder = os.path.join(current_app.root_path, 'admin', 'static', 'images')
        os.makedirs(photo_folder, exist_ok=True)
        photo_file.save(os.path.join(photo_folder, filename))
        candidate.photo = filename

    db.session.commit()
    
    # Audit log
    new_department = candidate.department.name if candidate.department else 'N/A'
    new_position = candidate.position.name if candidate.position else 'N/A'
    new_party_list = candidate.party_list if candidate.party_list else 'Independent'
    
    log_audit(
        action='UPDATE_CANDIDATE',
        description=f"Updated candidate: {old_first_name} {old_last_name} → {candidate.first_name} {candidate.last_name} | Scope: {old_scope} → {scope} | Party: {old_party_list or 'Independent'} → {new_party_list} | Position: {old_position} → {new_position} | Department: {old_department} → {new_department}"
    )
    
    if is_ajax:
        return jsonify({
            'success': True,
            'message': 'Candidate updated successfully!',
            'id': candidate.id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'party_list': candidate.party_list,
            'platform': candidate.platform,  # NEW
            'department': candidate.department.name if candidate.department else '',
            'department_id': candidate.department_id,
            'course_id': candidate.course_id,  # NEW
            'position': candidate.position.name if candidate.position else '',
            'position_id': candidate.position_id,
            'election_id': candidate.election_id,
            'scope': candidate.scope,
            'photo': url_for('admin.static', filename='images/' + candidate.photo) if candidate.photo else None
        })
    
    flash('Candidate updated successfully!', 'success')
    return redirect(url_for('admin.manage_candidates'))


@admin_bp.route('/candidates/delete/<int:id>', methods=['POST'])
@admin_required
def delete_candidate(id):
    candidate = Candidate.query.get_or_404(id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Store candidate info for audit log before deletion
    candidate_name = f"{candidate.first_name} {candidate.last_name}"
    party_list = candidate.party_list if candidate.party_list else 'Independent'
    position_name = candidate.position.name if candidate.position else 'N/A'
    department_name = candidate.department.name if candidate.department else 'N/A'
    election_title = candidate.election.title if candidate.election else 'N/A'
    
    try:
        db.session.delete(candidate)
        db.session.commit()
        
        # ---------- AUDIT LOG ----------
        log_audit(
            action='DELETE_CANDIDATE',
            description=f"Deleted candidate: {candidate_name} | Party: {party_list} | Position: {position_name} | Department: {department_name} | Election: {election_title}"
        )
        
        # Always return JSON for AJAX requests
        if is_ajax:
            return jsonify({
                'success': True,
                'message': 'Candidate deleted successfully!'
            })
        
        flash('Candidate deleted successfully!', 'success')
        return redirect(url_for('admin.manage_candidates'))
        
    except Exception as e:
        db.session.rollback()
        if is_ajax:
            return jsonify({
                'success': False,
                'message': f'Error deleting candidate: {str(e)}'
            }), 500
        flash(f'Error deleting candidate: {str(e)}', 'error')
        return redirect(url_for('admin.manage_candidates'))


# NEW: Add route to get courses by department
# NEW: Add route to get courses by department
@admin_bp.route('/courses/by_department/<int:department_id>', methods=['GET'])
@admin_required
def get_courses_by_department(department_id):
    """AJAX endpoint to get courses for a department"""
    from admin.models import Course
    
    courses = Course.query.filter_by(department_id=department_id).order_by(Course.course_name).all()
    
    courses_data = []
    for course in courses:
        courses_data.append({
            'id': course.id,
            'course_name': course.course_name,  # Changed from 'name' to match model
            'course_code': course.course_code    # Changed from 'code' to match model
        })
    
    return jsonify({'courses': courses_data})

        
# ---------------------- Manage Positions ---------------------- #
@admin_bp.route('/manage_positions', methods=['GET', 'POST'])
@admin_required
def manage_positions():
    if request.method == 'POST':
        position_name = request.form.get('position_name', '').strip()
        position_color = request.form.get('position_color', '#3498db').strip()
        
        if not position_color.startswith('#'):
            position_color = f'#{position_color}'
        
        if position_name:
            existing = Position.query.filter_by(name=position_name).first()
            if existing:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    # ---------- AUDIT LOG: Attempt to add duplicate position (AJAX) ----------
                    username = getattr(current_user, 'username', 'Unknown')
                    ip = request.remote_addr
                    log_audit(
                        action='ADD_POSITION_DUPLICATE',
                        description=f"Admin user '{username}' attempted to add duplicate position: '{position_name}' from IP: {ip}"
                    )
                    return jsonify({"success": False, "message": f'Position "{position_name}" already exists!'})
                flash(f'Position "{position_name}" already exists!', 'warning')
            else:
                new_position = Position(name=position_name, color=position_color)
                db.session.add(new_position)
                db.session.commit()
                
                # ---------- AUDIT LOG: Add position ----------
                username = getattr(current_user, 'username', 'Unknown')
                ip = request.remote_addr
                log_audit(
                    action='ADD_POSITION',
                    description=f"Admin user '{username}' added new position: '{position_name}' with color: {position_color} from IP: {ip}"
                )
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"success": True, "message": f'Position "{position_name}" added successfully!'})
                flash(f'Position "{position_name}" added successfully!', 'success')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": True, "message": f'Position "{position_name}" added successfully!'})
        return redirect(url_for('admin.manage_positions'))
    
    positions = Position.query.all()
    
    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        positions_data = [{"id": p.id, "name": p.name, "color": p.color} for p in positions]
        
        # ---------- AUDIT LOG: Get positions data via AJAX ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        log_audit(
            action='GET_POSITIONS_DATA',
            description=f"Admin user '{username}' fetched positions data via AJAX from IP: {ip} | Total positions: {len(positions)}"
        )
        
        return jsonify(positions_data)
    
    # ---------- AUDIT LOG: Manage Positions page viewed ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    log_audit(
        action='MANAGE_POSITIONS_VIEW',
        description=f"Admin user '{username}' viewed the manage positions page from IP: {ip} | Total positions: {len(positions)}"
    )
    
    return render_template('manage_positions.html', positions=positions)


# Get positions data (AJAX endpoint)
@admin_bp.route('/manage_positions/data')
@admin_required
def get_positions_data():
    positions = Position.query.all()
    positions_data = [{"id": p.id, "name": p.name, "color": p.color} for p in positions]
    
    # ---------- AUDIT LOG: Get positions data endpoint ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    log_audit(
        action='GET_POSITIONS_DATA_ENDPOINT',
        description=f"Admin user '{username}' fetched positions data from API endpoint from IP: {ip} | Total positions: {len(positions)}"
    )
    
    return jsonify(positions_data)


# Update position
@admin_bp.route('/manage_positions/<int:position_id>', methods=['PUT'])
@admin_required
def update_position(position_id):
    position = Position.query.get_or_404(position_id)
    old_name = position.name
    old_color = position.color
    data = request.get_json()
    
    if not data or 'position_name' not in data:
        return jsonify({"success": False, "message": "Position name is required"}), 400
    
    position_name = data['position_name'].strip()
    position_color = data.get('position_color', '#3498db').strip()
    
    if not position_color.startswith('#'):
        position_color = f'#{position_color}'
    
    if not position_name:
        return jsonify({"success": False, "message": "Position name cannot be empty"}), 400
    
    # Check if position name already exists (excluding current position)
    existing = Position.query.filter(Position.name == position_name, Position.id != position_id).first()
    if existing:
        # ---------- AUDIT LOG: Attempt to update to duplicate position name ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        log_audit(
            action='UPDATE_POSITION_DUPLICATE',
            description=f"Admin user '{username}' attempted to update position '{old_name}' to duplicate name: '{position_name}' from IP: {ip}"
        )
        return jsonify({"success": False, "message": f'Position "{position_name}" already exists!'})
    
    position.name = position_name
    position.color = position_color
    db.session.commit()
    
    # ---------- AUDIT LOG: Update position ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    log_audit(
        action='UPDATE_POSITION',
        description=f"Admin user '{username}' updated position from '{old_name}' (color: {old_color}) to '{position_name}' (color: {position_color}) (ID: {position_id}) from IP: {ip}"
    )
    
    return jsonify({"success": True, "message": f'Position "{position_name}" updated successfully!'})


# Delete position
@admin_bp.route('/manage_positions/<int:position_id>', methods=['DELETE'])
@admin_required
def delete_position(position_id):
    position = Position.query.get_or_404(position_id)
    position_name = position.name
    
    # Check if position is being used by any candidate
    candidates_using = Candidate.query.filter_by(position_id=position_id).first()
    if candidates_using:
        # ---------- AUDIT LOG: Attempt to delete position in use ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        log_audit(
            action='DELETE_POSITION_IN_USE',
            description=f"Admin user '{username}' attempted to delete position '{position_name}' (ID: {position_id}) but it is being used by candidates from IP: {ip}"
        )
        return jsonify({"success": False, "message": f'Cannot delete position "{position.name}" because it is being used by candidates.'})
    
    db.session.delete(position)
    db.session.commit()
    
    # ---------- AUDIT LOG: Delete position ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    log_audit(
        action='DELETE_POSITION',
        description=f"Admin user '{username}' deleted position: '{position_name}' (ID: {position_id}) from IP: {ip}"
    )
    
    return jsonify({"success": True, "message": f'Position "{position_name}" deleted successfully!'})



@admin_bp.route('/configure-election-positions/<int:election_id>', methods=['GET', 'POST'])
@admin_required
def configure_election_positions(election_id):
    """Configure which positions are in an election and their vote limits"""
    # Get the election first
    election = Election.query.get_or_404(election_id)
    
    # Get all positions
    all_positions = Position.query.order_by(Position.name).all()
    
    # Get all courses for dropdown (for campus-wide elections)
    all_courses = Course.query.order_by(Course.course_name).all()
    
    # Get all program types (Day/Night)
    from student.models import ProgramType  # Import ProgramType
    program_types = ProgramType.query.order_by(ProgramType.name).all()
    
    # Get currently configured positions for this election
    configured_positions = ElectionPosition.query.filter_by(election_id=election_id).all()
    configured_position_ids = [ep.position_id for ep in configured_positions]
    configured_positions_dict = {ep.position_id: ep.max_votes for ep in configured_positions}
    
    # Get course restrictions for configured positions
    position_courses = {ep.position_id: ep.course_id for ep in configured_positions if ep.course_id}
    
    # Get program type restrictions for configured positions
    position_program_types = {ep.position_id: ep.program_type_id for ep in configured_positions if ep.program_type_id}
    
    if request.method == 'POST':
        # Get form data
        selected_positions = request.form.getlist('positions')
        
        # Delete existing configurations
        ElectionPosition.query.filter_by(election_id=election_id).delete()
        
        # Add new configurations
        display_order = 0
        for position_id_str in selected_positions:
            position_id = int(position_id_str)
            max_votes = request.form.get(f'max_votes_{position_id}', type=int, default=1)
            
            # Get course restriction if applicable
            course_id = request.form.get(f'course_{position_id}', type=int)
            
            # Get program type restriction
            program_type_id = request.form.get(f'program_type_{position_id}', type=int)
            
            ep = ElectionPosition(
                election_id=election_id,
                position_id=position_id,
                max_votes=max_votes,
                min_votes=1,  # Default minimum
                course_id=course_id if course_id else None,
                program_type_id=program_type_id if program_type_id else None,
                display_order=display_order
            )
            db.session.add(ep)
            display_order += 1
        
        db.session.commit()
        
        # Audit log
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        log_audit(
            action='CONFIGURE_ELECTION_POSITIONS',
            description=f"Admin user '{username}' configured {len(selected_positions)} positions for election '{election.title}' (ID: {election_id}) from IP: {ip}"
        )
        
        flash('Election positions configured successfully!', 'success')
        
        # CHANGED: Redirect back to the same page instead of create_election
        return redirect(url_for('admin.configure_election_positions', election_id=election_id))
    
    # For GET request, pass ALL needed variables to template
    return render_template(
        'configure_election_positions.html',
        election=election,
        all_positions=all_positions,
        all_courses=all_courses,
        program_types=program_types,
        configured_position_ids=configured_position_ids,
        configured_positions=configured_positions_dict,
        position_courses=position_courses,
        position_program_types=position_program_types
    )
    
# admin/routes.py - UPDATE your create_election route
@admin_bp.route('/create-election', methods=['GET', 'POST'])
@admin_required
def create_election():
    """
    IMPROVED CREATE ELECTION ROUTE
    - Handles both campus and department elections
    - Adds year level filtering for campus elections
    - Redirects to position configuration after creation
    """
    # Clear any existing flash messages from other pages
    # This ensures only messages from this page will be shown
    session.pop('_flashes', None)
    
    # Get all departments
    departments = Department.query.order_by(Department.name).all()

    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        scope = request.form.get('scope', '').strip().lower()  # 'campus' or 'department'
        department_id_str = request.form.get('department_id')
        description = request.form.get('description', '').strip()
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        
        # Get year levels (for campus elections)
        year_levels = request.form.getlist('year_levels')
        
        # ========== VALIDATION ==========
        if not all([title, scope, start_date_str, end_date_str]):
            flash('All required fields must be filled.', 'election-error')
            return redirect(url_for('admin.create_election'))

        if scope not in ['campus', 'department']:
            flash('Invalid election scope. Must be campus or department.', 'election-error')
            return redirect(url_for('admin.create_election'))

        # Parse dates
        try:
            start_date = tz.localize(datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M'))
            end_date = tz.localize(datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M'))
        except ValueError:
            flash('Invalid date format.', 'election-error')
            return redirect(url_for('admin.create_election'))

        if end_date <= start_date:
            flash('End date must be later than start date.', 'election-error')
            return redirect(url_for('admin.create_election'))

        # Handle department based on scope
        department_id = None
        department_name = None
        
        if scope == 'department':
            if not department_id_str:
                flash('Department is required for Department Elections.', 'election-error')
                return redirect(url_for('admin.create_election'))
            
            department_id = int(department_id_str)
            dept_obj = Department.query.get(department_id)
            if not dept_obj:
                flash('Selected department does not exist.', 'election-error')
                return redirect(url_for('admin.create_election'))
            department_name = dept_obj.name
        
        # Handle year levels for campus elections
        year_levels_str = 'all'  # Default to all years
        if scope == 'campus' and year_levels:
            # Sort year levels for consistency
            year_levels.sort()
            year_levels_str = ','.join(year_levels)
        
        # Map scope to election_type for backward compatibility
        election_type = 'SSG' if scope == 'campus' else 'Department'

        # Create election - populate ALL fields
        new_election = Election(
            title=title,
            election_type=election_type,  # For backward compatibility
            scope=scope,                   # New scalable field
            department_id=department_id,
            department=department_name,     # Keep redundant field for existing code
            year_levels=year_levels_str,    # New year levels field
            description=description,
            start_date=start_date,
            end_date=end_date
        )
        
        db.session.add(new_election)
        db.session.commit()
        
        # ---------- AUDIT LOG ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        year_levels_display = 'All Years' if year_levels_str == 'all' else f"Year(s) {year_levels_str}"
        
        log_audit(
            action='CREATE_ELECTION',
            description=f"Admin user '{username}' created new {scope} election: '{title}' from IP: {ip} | Department: {department_name or 'N/A'}, Target: {year_levels_display}, Start: {start_date.strftime('%Y-%m-%d %H:%M')}, End: {end_date.strftime('%Y-%m-%d %H:%M')}"
        )
        
        # MODIFIED: Redirect to position configuration instead of back to create page
        flash('Election created successfully! Now configure positions and vote limits.', 'election-success')
        return redirect(url_for('admin.configure_election_positions', election_id=new_election.id))

    # GET request: fetch elections
    elections_all = Election.query.order_by(Election.start_date).all()

    # Ensure datetime are timezone-aware
    for e in elections_all:
        if e.start_date.tzinfo is None:
            e.start_date = tz.localize(e.start_date)
        if e.end_date.tzinfo is None:
            e.end_date = tz.localize(e.end_date)

    # Filter elections
    upcoming_elections = [e for e in elections_all if e.start_date > now]
    active_elections = [e for e in elections_all if e.start_date <= now <= e.end_date]
    
    # AUDIT LOG
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='CREATE_ELECTION_VIEW',
        description=f"Admin user '{username}' viewed the create election page from IP: {ip} | Total elections: {len(elections_all)}, Active: {len(active_elections)}, Upcoming: {len(upcoming_elections)}"
    )

    return render_template(
        'create_election.html',
        departments=departments,
        upcoming=upcoming_elections,
        active=active_elections,
        now=now
    )

# Keep the old route for backward compatibility
@admin_bp.route('/create-department-election', methods=['GET', 'POST'])
@admin_required
def create_department_election():
    """Legacy route - redirects to new unified create election page"""
    return redirect(url_for('admin.create_election'))


# ----------- ANNOUNCEMENTS ROUTE -----------
@admin_bp.route('/announcements', methods=['GET', 'POST'])
@login_required
def announcements():
    departments = Department.query.all()  # For dropdown
    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)  # Get current datetime

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        date = request.form.get('date')
        department_id = request.form.get('department')

        if department_id == "all":
            department_id = None  # None means visible to all

        new_announcement = Announcement(
            title=title,
            content=content,
            date=date,
            department_id=department_id
        )
        db.session.add(new_announcement)
        db.session.commit()
        
        # ---------- AUDIT LOG: Create announcement ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        # Get department name for audit log
        department_name = "All Departments"
        if department_id:
            dept = Department.query.get(department_id)
            department_name = dept.name if dept else f"ID: {department_id}"
        
        log_audit(
            action='CREATE_ANNOUNCEMENT',
            description=f"Admin user '{username}' created new announcement: '{title}' from IP: {ip} | Target: {department_name}, Date: {date}"
        )

        # Tag the flash message for announcements page
        flash('announcements_page:Announcement created successfully!', 'success')
        return redirect(url_for('admin.announcements'))

    # GET: fetch announcements to display
    announcements_list = Announcement.query.order_by(Announcement.date.desc()).all()
    
    # ---------- AUDIT LOG: Announcements page viewed ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='ANNOUNCEMENTS_VIEW',
        description=f"Admin user '{username}' viewed the announcements page from IP: {ip} | Total announcements: {len(announcements_list)}"
    )

    return render_template(
        'announcements.html', 
        departments=departments, 
        announcements=announcements_list,
        now=now  # Pass current datetime to template
    )

# ----------- UPDATE ANNOUNCEMENT -----------
@admin_bp.route('/update-announcement/<int:announcement_id>', methods=['POST'])
@login_required
def update_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    
    title = request.form.get('title')
    content = request.form.get('content')
    date = request.form.get('date')
    department_id = request.form.get('department')
    
    if department_id == "all":
        department_id = None
    else:
        department_id = int(department_id)
    
    announcement.title = title
    announcement.content = content
    announcement.date = datetime.strptime(date, '%Y-%m-%d').date()
    announcement.department_id = department_id
    
    db.session.commit()
    
    # Audit log
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='UPDATE_ANNOUNCEMENT',
        description=f"Admin user '{username}' updated announcement: '{title}' (ID: {announcement_id}) from IP: {ip}"
    )
    
    # Tag the flash message for announcements page
    flash('announcements_page:Announcement updated successfully!', 'success')
    return redirect(url_for('admin.announcements'))

# ----------- DELETE ANNOUNCEMENT -----------
@admin_bp.route('/delete-announcement/<int:announcement_id>', methods=['POST'])
@login_required
def delete_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    title = announcement.title
    
    db.session.delete(announcement)
    db.session.commit()
    
    # Audit log
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='DELETE_ANNOUNCEMENT',
        description=f"Admin user '{username}' deleted announcement: '{title}' (ID: {announcement_id}) from IP: {ip}"
    )
    
    # Tag the flash message for announcements page
    flash('announcements_page:Announcement deleted successfully!', 'success')
    return redirect(url_for('admin.announcements'))

from student.models import ContactInfo, HelpPageContent

# ----------- GET ANNOUNCEMENT FOR EDIT -----------
@admin_bp.route('/get-announcement/<int:announcement_id>', methods=['GET'])
@login_required
def get_announcement(announcement_id):
    try:
        announcement = Announcement.query.get_or_404(announcement_id)
        
        # Format the date properly
        date_str = announcement.date.strftime('%Y-%m-%d') if announcement.date else ''
        
        return jsonify({
            'success': True,
            'announcement': {
                'id': announcement.id,
                'title': announcement.title,
                'content': announcement.content,
                'date': date_str,
                'department_id': announcement.department_id
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ----------- HELP PAGE MANAGEMENT -----------
@admin_bp.route('/help-settings', methods=['GET', 'POST'])
@login_required
def help_settings():
    contact_info = ContactInfo.get_settings()
    help_content = HelpPageContent.get_content()
    
    if request.method == 'POST':
        # Update contact info
        contact_info.email = request.form.get('email')
        contact_info.phone = request.form.get('phone')
        contact_info.committee_name = request.form.get('committee_name')
        contact_info.additional_info = request.form.get('additional_info')
        contact_info.updated_by = current_user.id
        
        # Update help content
        help_content.common_issues = request.form.get('common_issues')
        help_content.updated_by = current_user.id
        
        db.session.commit()
        
        # Audit log
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        log_audit(
            action='UPDATE_HELP_SETTINGS',
            description=f"Admin user '{username}' updated help page settings from IP: {ip}"
        )
        
        flash('announcements_page:Help page settings updated successfully!', 'success')
        return redirect(url_for('admin.help_settings'))
    
    return render_template('help_settings.html', 
                         contact=contact_info, 
                         help_content=help_content)



# ----------- GET HELP SETTINGS FOR AJAX -----------
@admin_bp.route('/get-help-settings')
@login_required
def get_help_settings():
    contact_info = ContactInfo.get_settings()
    help_content = HelpPageContent.get_content()
    
    return jsonify({
        'success': True,
        'contact': {
            'email': contact_info.email,
            'phone': contact_info.phone,
            'committee_name': contact_info.committee_name,
            'additional_info': contact_info.additional_info
        },
        'help_content': {
            'common_issues': help_content.common_issues
        }
    })



# ----------- GUIDELINES MANAGEMENT -----------
@admin_bp.route('/guidelines-settings', methods=['GET', 'POST'])
@login_required
def guidelines_settings():
    from student.models import GuidelinesContent
    
    guidelines_content = GuidelinesContent.get_content()
    
    if request.method == 'POST':
        # Update guidelines content
        guidelines_content.purpose = request.form.get('purpose')
        guidelines_content.voting_rules = request.form.get('voting_rules')
        guidelines_content.how_to_vote = request.form.get('how_to_vote')
        guidelines_content.privacy_security = request.form.get('privacy_security')
        guidelines_content.important_reminders = request.form.get('important_reminders')
        guidelines_content.fingerprint_info = request.form.get('fingerprint_info')
        # REMOVE THIS LINE - don't set updated_by
        # guidelines_content.updated_by = current_user.id
        
        db.session.commit()
        
        # Audit log
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        log_audit(
            action='UPDATE_GUIDELINES',
            description=f"Admin user '{username}' updated voting guidelines from IP: {ip}"
        )
        
        flash('announcements_page:Guidelines updated successfully!', 'success')
        return redirect(url_for('admin.guidelines_settings'))
    
    return render_template('guidelines_settings.html', content=guidelines_content)


# ----------- GET GUIDELINES FOR AJAX -----------
@admin_bp.route('/get-guidelines')
@login_required
def get_guidelines():
    from student.models import GuidelinesContent
    
    guidelines_content = GuidelinesContent.get_content()
    
    return jsonify({
        'success': True,
        'content': {
            'purpose': guidelines_content.purpose,
            'voting_rules': guidelines_content.voting_rules,
            'how_to_vote': guidelines_content.how_to_vote,
            'privacy_security': guidelines_content.privacy_security,
            'important_reminders': guidelines_content.important_reminders,
            'fingerprint_info': guidelines_content.fingerprint_info
        }
    })


@admin_bp.route('/results')
@admin_required
def results_page():
    # Get school year filter from session (set by dashboard)
    school_year = session.get('admin_current_school_year')
    
    # Parse school year to date range
    start_date = None
    end_date = None
    if school_year:
        try:
            start_year = int(school_year.split('-')[0])
            end_year = int(school_year.split('-')[1])
            start_date = datetime(start_year, 1, 1)
            end_date = datetime(end_year, 12, 31)
        except (ValueError, IndexError):
            start_date = None
            end_date = None
    
    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)
    
    # Filter elections by school year if set
    election_query = Election.query.order_by(Election.end_date.desc())
    
    if start_date and end_date:
        # Convert to timezone-aware for comparison
        start_date_aware = tz.localize(start_date) if start_date.tzinfo is None else start_date
        end_date_aware = tz.localize(end_date) if end_date.tzinfo is None else end_date
        
        election_query = election_query.filter(
            Election.start_date >= start_date,
            Election.start_date <= end_date
        )
    
    elections = election_query.all()
    
    upcoming, active, completed = [], [], []
    
    for election in elections:
        # Create timezone-aware copies for comparison
        start_date_e = election.start_date
        end_date_e = election.end_date
        
        # Convert to timezone-aware if naive
        if start_date_e.tzinfo is None:
            start_date_e = tz.localize(start_date_e)
        if end_date_e.tzinfo is None:
            end_date_e = tz.localize(end_date_e)
        
        # Add timezone-aware attributes to election object for template use
        election.tz_start = start_date_e
        election.tz_end = end_date_e
        
        # Categorize based on the dates
        if end_date_e < now:
            completed.append(election)
        elif start_date_e <= now <= end_date_e:
            active.append(election)
        else:
            upcoming.append(election)
    
    # Get total elections count (unfiltered) for context
    total_elections = Election.query.count()
    
    # ---------- AUDIT LOG: Results page viewed ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    school_year_info = f" | School Year: {school_year}" if school_year else ""
    
    log_audit(
        action='RESULTS_PAGE_VIEW',
        description=f"Admin user '{username}' viewed the results page from IP: {ip}{school_year_info} | Displayed elections: {len(elections)} (filtered), Total: {total_elections}, Active: {len(active)}, Completed: {len(completed)}, Upcoming: {len(upcoming)}"
    )
    
    return render_template(
        'admin_results.html',
        upcoming_elections=upcoming,
        active_elections=active,
        completed_elections=completed,
        now=now,
        current_sy=school_year,  # Pass current school year to template
        total_filtered=len(elections),
        total_elections=total_elections
    )


@admin_bp.route('/vote-distribution')
def vote_distribution():
    """Vote Distribution Analysis Page"""
    # Sample data - will be replaced with database queries later
    current_sy = session.get('current_sy')
    
    return render_template('vote_distribution.html', 
                         current_sy=current_sy,
                         title='Vote Distribution')



@admin_bp.route('/results/<int:election_id>')
@admin_required
def election_results(election_id):
    """OPTIMIZED: Uses finder_hashes for live results, TallyVote for official results"""
    import json
    from collections import defaultdict
    
    election = Election.query.get_or_404(election_id)
    
    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)
    
    if election.start_date.tzinfo is None:
        election.start_date = tz.localize(election.start_date)
    if election.end_date.tzinfo is None:
        election.end_date = tz.localize(election.end_date)
    
    if election.end_date < now:
        status = "Completed"
    elif election.start_date <= now <= election.end_date:
        status = "Active"
    else:
        status = "Upcoming"
    
    # Check if election has been officially tallied
    is_tallied = False
    tally_timestamp = None
    
    if TALLY_VOTE_AVAILABLE:
        tally_record = TallyVote.query.filter_by(election_id=election_id).first()
        is_tallied = tally_record is not None
        if is_tallied:
            latest_tally = TallyVote.query.filter_by(
                election_id=election_id
            ).order_by(TallyVote.tally_timestamp.desc()).first()
            tally_timestamp = latest_tally.tally_timestamp if latest_tally else None
    
    # Get all candidates
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    
    # GET POSITION LIMITS
    position_limits = {}
    election_positions = ElectionPosition.query.filter_by(election_id=election_id).all()
    for ep in election_positions:
        position_limits[ep.position_id] = ep.max_votes
    
    # COUNT UNIQUE VOTERS
    unique_voters = db.session.query(Vote.student_id).filter_by(
        election_id=election_id
    ).distinct().count()
    
    # ===== GET VOTE COUNTS - OPTIMIZED! =====
    if is_tallied and TALLY_VOTE_AVAILABLE:
        # STATE 1: OFFICIALLY TALLIED - Use TallyVote table (INSTANT!)
        print("📊 Using official tally results")
        tally_records = TallyVote.query.filter_by(election_id=election_id).all()
        vote_counts = {t.candidate_id: t.vote_count for t in tally_records}
        
        # Ensure all candidates have at least 0
        for candidate in candidates:
            if candidate.id not in vote_counts:
                vote_counts[candidate.id] = 0
                
    else:
        # STATE 2: LIVE RESULTS - Use finder_hashes (NO DECRYPTION, 2-3 seconds!)
        print("📊 Using finder_hashes for live results")
        vote_counts = get_admin_live_vote_counts(election_id)
    
    # Build candidate results
    candidate_results = []
    total_votes_cast = 0
    
    for candidate in candidates:
        vote_count = vote_counts.get(candidate.id, 0)
        total_votes_cast += vote_count
        
        candidate_results.append({
            'id': candidate.id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'photo': candidate.photo,
            'position': candidate.position.name if candidate.position else "N/A",
            'position_id': candidate.position_id,
            'department': candidate.department.name if candidate.department else "All Departments",
            'vote_count': vote_count,
            'voter_percentage': 0,  # Calculate after
            'is_tallied': is_tallied
        })
    
    # Calculate percentages based on UNIQUE VOTERS
    if unique_voters > 0:
        for candidate in candidate_results:
            candidate['voter_percentage'] = round((candidate['vote_count'] / unique_voters) * 100, 2)
    
    # Group candidates by position for winner determination
    candidates_by_position = {}
    for candidate in candidate_results:
        position = candidate['position']
        if position not in candidates_by_position:
            candidates_by_position[position] = []
        candidates_by_position[position].append(candidate)
    
    # Sort candidates within each position by vote count
    for position in candidates_by_position:
        candidates_by_position[position].sort(key=lambda x: x['vote_count'], reverse=True)
    
    # Determine winners for each position
    winners_by_position = {}
    for position_name, candidates_in_pos in candidates_by_position.items():
        if candidates_in_pos:
            position_id = candidates_in_pos[0]['position_id']
            max_winners = position_limits.get(position_id, 1)
            
            winners = []
            for i, candidate in enumerate(candidates_in_pos):
                if i < max_winners and candidate['vote_count'] > 0:
                    winners.append(candidate)
                else:
                    break
            
            if winners:
                winners_by_position[position_name] = winners
    
    # Sort winners_by_position by position_id
    position_order = []
    for position_name, candidates_in_pos in candidates_by_position.items():
        if candidates_in_pos:
            position_id = candidates_in_pos[0]['position_id']
            position_order.append((position_id, position_name))
    
    position_order.sort(key=lambda x: x[0])
    
    sorted_winners_by_position = {}
    for position_id, position_name in position_order:
        if position_name in winners_by_position:
            sorted_winners_by_position[position_name] = winners_by_position[position_name]
    
    # Sort candidate_results by position_id first, then by vote count
    candidates_by_pos_id = {}
    for candidate in candidate_results:
        pos_id = candidate['position_id']
        if pos_id not in candidates_by_pos_id:
            candidates_by_pos_id[pos_id] = []
        candidates_by_pos_id[pos_id].append(candidate)
    
    for pos_id in candidates_by_pos_id:
        candidates_by_pos_id[pos_id].sort(key=lambda x: x['vote_count'], reverse=True)
    
    sorted_candidate_results = []
    for pos_id in sorted(candidates_by_pos_id.keys()):
        sorted_candidate_results.extend(candidates_by_pos_id[pos_id])
    
    # Calculate voter statistics
    if election.department_id:
        total_eligible_voters = Student.query.filter_by(department_id=election.department_id).count()
    else:
        total_eligible_voters = Student.query.count()
    
    voter_turnout = round((unique_voters / total_eligible_voters * 100), 2) if total_eligible_voters > 0 else 0
    students_not_voted = total_eligible_voters - unique_voters
    
    # AUDIT LOG
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='ELECTION_RESULTS_VIEW',
        description=f"Admin user '{username}' viewed results for election: '{election.title}' (ID: {election_id}) from IP: {ip} | Status: {status}, Tallied: {is_tallied}, Voter turnout: {voter_turnout}%, Unique voters: {unique_voters}/{total_eligible_voters}"
    )
    
    return render_template(
        'election_results_detail.html',
        election=election,
        candidate_results=sorted_candidate_results,
        winners_by_position=sorted_winners_by_position,
        total_voters=unique_voters,
        total_votes_cast=total_votes_cast,
        total_eligible_voters=total_eligible_voters,
        voter_turnout=voter_turnout,
        students_not_voted=students_not_voted,
        status=status,
        now=now,
        is_tallied=is_tallied,
        tally_timestamp=tally_timestamp
    )


def get_admin_live_vote_counts(election_id):
    """
    ULTRA FAST: Get vote counts using finder_hashes for admin live results
    NO DECRYPTION! Takes 2-3 seconds even for thousands of voters
    """
    vote_counts = {}
    
    # Stream votes in chunks to avoid memory issues
    batch_size = 500
    offset = 0
    
    while True:
        batch = Vote.query.filter_by(election_id=election_id)\
                          .with_entities(Vote.finder_hash)\
                          .offset(offset)\
                          .limit(batch_size)\
                          .all()
        
        if not batch:
            break
        
        # Process each vote in the batch
        for vote in batch:
            if not vote.finder_hash:
                continue
                
            try:
                finder_data = json.loads(vote.finder_hash)
                
                # Extract candidate IDs based on format
                candidate_ids = []
                
                if isinstance(finder_data, dict):
                    # New format with 'hashes' array
                    if 'hashes' in finder_data and isinstance(finder_data['hashes'], list):
                        for item in finder_data['hashes']:
                            if isinstance(item, dict) and 'candidate_id' in item:
                                candidate_ids.append(item['candidate_id'])
                    
                    # Even better: if candidate_ids stored directly
                    elif 'candidate_ids' in finder_data and isinstance(finder_data['candidate_ids'], list):
                        candidate_ids = finder_data['candidate_ids']
                
                elif isinstance(finder_data, list):
                    # Old format
                    for item in finder_data:
                        if isinstance(item, dict) and 'candidate_id' in item:
                            candidate_ids.append(item['candidate_id'])
                
                # Count the votes
                for cid in candidate_ids:
                    vote_counts[cid] = vote_counts.get(cid, 0) + 1
                    
            except json.JSONDecodeError:
                continue
            except Exception:
                continue
        
        offset += batch_size
    
    return vote_counts
    


@admin_bp.route('/results/<int:election_id>/tally', methods=['POST'])
@admin_required
def tally_election_results(election_id):
    if not TALLY_VOTE_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Tally system not available. TallyVote model is missing.'
        }), 500
    
    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)
    
    election = Election.query.get_or_404(election_id)
    
    if election.end_date.tzinfo is None:
        election_end = tz.localize(election.end_date)
    else:
        election_end = election.end_date
    
    force_tally = request.json.get('force', False) if request.is_json else False
    if not force_tally and election_end > now:
        return jsonify({
            'success': False,
            'message': f'Election is active until {election_end.strftime("%b %d, %Y %I:%M %p")}.',
            'suggestion': 'Add "force": true to tally early.'
        }), 400
    
    try:
        candidates = Candidate.query.filter_by(election_id=election_id).all()
        if not candidates:
            return jsonify({
                'success': False,
                'message': 'No candidates found for this election.'
            }), 400
        
        candidate_results = []
        total_votes_counted = 0
        candidate_vote_map = {}
        
        for candidate in candidates:
            vote_count = count_votes_for_candidate(candidate.id, election_id)
            total_votes_counted += vote_count
            candidate_vote_map[candidate.id] = vote_count
            
            candidate_results.append({
                'candidate_id': candidate.id,
                'name': f"{candidate.first_name} {candidate.last_name}",
                'position': candidate.position.name if candidate.position else "N/A",
                'vote_count': vote_count
            })
        
        # Count unique voters
        unique_voters = db.session.query(Vote.student_id).filter_by(
            election_id=election_id
        ).distinct().count()
        
        total_votes_in_db = Vote.query.filter_by(election_id=election_id).count()
        
        tally_timestamp = datetime.utcnow()
        
        TallyVote.query.filter_by(election_id=election_id).delete()
        
        for candidate_id, vote_count in candidate_vote_map.items():
            tally = TallyVote(
                election_id=election_id,
                candidate_id=candidate_id,
                vote_count=vote_count,
                tally_timestamp=tally_timestamp
            )
            db.session.add(tally)
        
        db.session.commit()
        
        # ---------- AUDIT LOG: Tally election results ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        force_text = " (forced)" if force_tally else ""
        
        log_audit(
            action='TALLY_ELECTION',
            description=f"Admin user '{username}' tallied results for election: '{election.title}' (ID: {election_id}) from IP: {ip}{force_text} | Candidates: {len(candidates)}, Unique voters: {unique_voters}, Total votes: {total_votes_counted}"
        )
        
        return jsonify({
            'success': True,
            'message': f'Tally completed: {unique_voters} voters, {total_votes_counted} votes for {len(candidates)} candidates.',
            'data': {
                'unique_voters': unique_voters,
                'total_votes': total_votes_counted,
                'votes_in_db': total_votes_in_db,
                'candidates_tallied': len(candidates),
                'tally_timestamp': tally_timestamp.isoformat(),
                'election_title': election.title,
                'results': candidate_results
            }
        })
        
    except Exception as e:
        db.session.rollback()
        
        # ---------- AUDIT LOG: Tally election failed ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        log_audit(
            action='TALLY_ELECTION_FAILED',
            description=f"Admin user '{username}' failed to tally results for election: '{election.title}' (ID: {election_id}) from IP: {ip} | Error: {str(e)[:200]}"
        )
        
        return jsonify({
            'success': False,
            'message': f'Tally failed: {str(e)}'
        }), 500


@admin_bp.route('/results/<int:election_id>/tally', methods=['DELETE'])
@admin_required
def clear_tally_results(election_id):
    if not TALLY_VOTE_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Tally system not available.'
        }), 500
    
    election = Election.query.get_or_404(election_id)
    
    try:
        count = TallyVote.query.filter_by(election_id=election_id).count()
        TallyVote.query.filter_by(election_id=election_id).delete()
        db.session.commit()
        
        # ---------- AUDIT LOG: Clear tally results ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        log_audit(
            action='CLEAR_TALLY',
            description=f"Admin user '{username}' cleared tally results for election: '{election.title}' (ID: {election_id}) from IP: {ip} | Records deleted: {count}"
        )
        
        return jsonify({
            'success': True,
            'message': f'Removed {count} tally records for {election.title}.',
            'data': {
                'records_deleted': count,
                'election_id': election_id,
                'election_title': election.title
            }
        })
        
    except Exception as e:
        db.session.rollback()
        
        # ---------- AUDIT LOG: Clear tally failed ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        log_audit(
            action='CLEAR_TALLY_FAILED',
            description=f"Admin user '{username}' failed to clear tally results for election: '{election.title}' (ID: {election_id}) from IP: {ip} | Error: {str(e)[:200]}"
        )
        
        return jsonify({
            'success': False,
            'message': f'Failed to clear tally: {str(e)}'
        }), 500


@admin_bp.route('/results/<int:election_id>/tally')
@admin_required
def get_tally_results(election_id):
    if not TALLY_VOTE_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Tally system not available.'
        }), 500
    
    election = Election.query.get_or_404(election_id)
    
    tally_records = TallyVote.query.filter_by(election_id=election_id).all()
    if not tally_records:
        # ---------- AUDIT LOG: Get tally results - none found ----------
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        log_audit(
            action='GET_TALLY_NO_RESULTS',
            description=f"Admin user '{username}' attempted to fetch tally results for election: '{election.title}' (ID: {election_id}) from IP: {ip} | No tally records found"
        )
        
        return jsonify({
            'success': False,
            'message': 'No official tally results found.',
            'suggestion': 'Use the Tally Votes button to create official results.'
        }), 404
    
    results = []
    total_votes = 0
    
    for tally in tally_records:
        candidate = Candidate.query.get(tally.candidate_id)
        if candidate:
            results.append({
                'candidate_id': candidate.id,
                'name': f"{candidate.first_name} {candidate.last_name}",
                'position': candidate.position.name if candidate.position else "N/A",
                'vote_count': tally.vote_count,
                'tally_timestamp': tally.tally_timestamp.isoformat()
            })
            total_votes += tally.vote_count
    
    last_tally = max(tally_records, key=lambda x: x.tally_timestamp)
    
    # ---------- AUDIT LOG: Get tally results ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='GET_TALLY_RESULTS',
        description=f"Admin user '{username}' fetched tally results for election: '{election.title}' (ID: {election_id}) from IP: {ip} | Candidates tallied: {len(results)}, Total votes: {total_votes}"
    )
    
    return jsonify({
        'success': True,
        'data': {
            'election_id': election.id,
            'election_title': election.title,
            'total_candidates_tallied': len(results),
            'total_votes_tallied': total_votes,
            'last_tally_timestamp': last_tally.tally_timestamp.isoformat(),
            'results': sorted(results, key=lambda x: x['vote_count'], reverse=True)
        }
    })



@admin_bp.route('/results/<int:election_id>/pdf')
@admin_required
def election_results_pdf(election_id):
    """Generate PDF - ONLY AVAILABLE AFTER OFFICIAL TALLY"""
    election = Election.query.get_or_404(election_id)
    
    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)
    
    # Get election status
    if election.start_date.tzinfo is None:
        election.start_date = tz.localize(election.start_date)
    if election.end_date.tzinfo is None:
        election.end_date = tz.localize(election.end_date)
    
    if election.end_date < now:
        status = "Completed"
    elif election.start_date <= now <= election.end_date:
        status = "Active"
    else:
        status = "Upcoming"
    
    # ===== CRITICAL: CHECK IF TALLIED FIRST =====
    is_tallied = False
    tally_timestamp = None
    
    if TALLY_VOTE_AVAILABLE:
        tally_record = TallyVote.query.filter_by(election_id=election_id).first()
        is_tallied = tally_record is not None
        if is_tallied:
            latest_tally = TallyVote.query.filter_by(
                election_id=election_id
            ).order_by(TallyVote.tally_timestamp.desc()).first()
            tally_timestamp = latest_tally.tally_timestamp if latest_tally else None
    
    # ===== BLOCK PDF IF NOT TALLIED =====
    if not is_tallied:
        # Return error message (can be JSON for AJAX or flash for redirect)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'PDF results are only available after official tally. Please tally the votes first.'
            }), 403
        else:
            flash('PDF results are only available after official tally. Please tally the votes first.', 'warning')
            return redirect(url_for('admin.election_results', election_id=election_id))
    
    # ===== ONLY GET HERE IF TALLIED =====
    print(f"📊 Generating PDF for election {election_id} using official tally results")
    
    # Get candidates
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    candidate_results = []
    total_votes_cast = 0
    
    # COUNT UNIQUE VOTERS
    unique_voters = db.session.query(Vote.student_id).filter_by(
        election_id=election_id
    ).distinct().count()
    
    # GET POSITION LIMITS
    position_limits = {}
    election_positions = ElectionPosition.query.filter_by(election_id=election_id).all()
    for ep in election_positions:
        position_limits[ep.position_id] = ep.max_votes
    
    # ===== USE TALLY TABLE ONLY (NO DECRYPTION, NO FALLBACK) =====
    tally_records = TallyVote.query.filter_by(election_id=election_id).all()
    tally_dict = {t.candidate_id: t.vote_count for t in tally_records}
    
    for candidate in candidates:
        vote_count = tally_dict.get(candidate.id, 0)
        
        candidate_results.append({
            'id': candidate.id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'photo': candidate.photo,
            'position': candidate.position.name if candidate.position else "N/A",
            'position_id': candidate.position_id,
            'department': candidate.department.name if candidate.department else "All Departments",
            'vote_count': vote_count,
            'voter_percentage': 0,
            'is_tallied': True
        })
        total_votes_cast += vote_count
    
    # Calculate percentages based on UNIQUE VOTERS
    if unique_voters > 0:
        for candidate in candidate_results:
            candidate['voter_percentage'] = round((candidate['vote_count'] / unique_voters) * 100, 2)
    
    # ===== WINNER DETERMINATION =====
    # Group candidates by position
    candidates_by_position = {}
    for candidate in candidate_results:
        position = candidate['position']
        if position not in candidates_by_position:
            candidates_by_position[position] = []
        candidates_by_position[position].append(candidate)
    
    # Sort candidates within each position by vote count
    for position in candidates_by_position:
        candidates_by_position[position].sort(key=lambda x: x['vote_count'], reverse=True)
    
    # Determine winners
    winners_by_position = {}
    
    for position_name, candidates_in_pos in candidates_by_position.items():
        if candidates_in_pos:
            position_id = candidates_in_pos[0]['position_id']
            max_winners = position_limits.get(position_id, 1)
            
            winners = []
            for i, candidate in enumerate(candidates_in_pos):
                if i < max_winners and candidate['vote_count'] > 0:
                    winners.append(candidate)
                else:
                    break
            
            if winners:
                winners_by_position[position_name] = winners
    
    # Sort winners_by_position by position_id
    position_order = []
    for position_name, candidates_in_pos in candidates_by_position.items():
        if candidates_in_pos:
            position_id = candidates_in_pos[0]['position_id']
            position_order.append((position_id, position_name))
    
    position_order.sort(key=lambda x: x[0])
    
    sorted_winners_by_position = {}
    for position_id, position_name in position_order:
        if position_name in winners_by_position:
            sorted_winners_by_position[position_name] = winners_by_position[position_name]
    
    # Sort candidate_results by position_id
    candidates_by_pos_id = {}
    for candidate in candidate_results:
        pos_id = candidate['position_id']
        if pos_id not in candidates_by_pos_id:
            candidates_by_pos_id[pos_id] = []
        candidates_by_pos_id[pos_id].append(candidate)
    
    for pos_id in candidates_by_pos_id:
        candidates_by_pos_id[pos_id].sort(key=lambda x: x['vote_count'], reverse=True)
    
    sorted_candidate_results = []
    for pos_id in sorted(candidates_by_pos_id.keys()):
        sorted_candidate_results.extend(candidates_by_pos_id[pos_id])
    
    # Get total eligible voters
    if election.department_id:
        total_eligible_voters = Student.query.filter_by(department_id=election.department_id).count()
    else:
        total_eligible_voters = Student.query.count()
    
    voter_turnout = round((unique_voters / total_eligible_voters * 100), 2) if total_eligible_voters > 0 else 0
    students_not_voted = total_eligible_voters - unique_voters
    
    # Render HTML template for PDF
    html = render_template(
        'election_results_pdf.html',
        election=election,
        candidate_results=sorted_candidate_results,
        winners_by_position=sorted_winners_by_position,
        total_voters=unique_voters,
        total_votes_cast=total_votes_cast,
        total_eligible_voters=total_eligible_voters,
        voter_turnout=voter_turnout,
        students_not_voted=students_not_voted,
        status=status,
        now=now,
        is_tallied=is_tallied,
        tally_timestamp=tally_timestamp,
        position_limits=position_limits
    )
    
    try:
        # Generate PDF using WeasyPrint
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        
        font_config = FontConfiguration()
        
        pdf = HTML(string=html, base_url=request.host_url).write_pdf(
            stylesheets=[CSS(string='''
                @page {
                    size: letter;
                    margin: 0.75in;
                    @bottom-center {
                        content: "Page " counter(page) " of " counter(pages);
                        font-family: Arial, sans-serif;
                        font-size: 9pt;
                        color: #666;
                    }
                }
            ''')],
            font_config=font_config
        )
        
        # Generate filename
        filename = f"{election.title}_Official_Results_{now.strftime('%Y%m%d_%H%M')}.pdf"
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Log PDF generation
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        log_audit(
            action='ELECTION_RESULTS_PDF_EXPORT',
            description=f"Admin user '{username}' exported OFFICIAL PDF results for election: '{election.title}' (ID: {election_id}) from IP: {ip} | Source: TallyVote table"
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"PDF Generation Error: {str(e)}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'error': 'PDF generation failed. Please try again or contact support.',
                'details': str(e)
            }), 500
        else:
            flash(f'PDF generation failed: {str(e)}', 'danger')
            return redirect(url_for('admin.election_results', election_id=election_id))



@admin_bp.route('/results/<int:election_id>/test-tally')
@admin_required
def test_tally_calculation(election_id):
    election = Election.query.get_or_404(election_id)
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    
    if not candidates:
        return jsonify({
            'success': False,
            'message': 'No candidates found'
        }), 400
    
    results = []
    total_votes = 0
    
    for candidate in candidates:
        vote_count = count_votes_for_candidate(candidate.id, election_id)
        total_votes += vote_count
        
        results.append({
            'candidate_id': candidate.id,
            'name': f"{candidate.first_name} {candidate.last_name}",
            'position': candidate.position.name if candidate.position else "N/A",
            'vote_count': vote_count
        })
    
    results.sort(key=lambda x: x['vote_count'], reverse=True)
    
    winners_by_position = {}
    for result in results:
        position = result['position']
        if position not in winners_by_position:
            winners_by_position[position] = result
        elif result['vote_count'] > winners_by_position[position]['vote_count']:
            winners_by_position[position] = result
    
    return jsonify({
        'success': True,
        'data': {
            'election': {
                'id': election.id,
                'title': election.title,
                'status': election.status
            },
            'total_votes_calculated': total_votes,
            'candidates_count': len(results),
            'winners': list(winners_by_position.values()),
            'results': results,
            'note': 'This is a test calculation. Results are NOT saved.'
        }
    })


@admin_bp.route('/profile')
@login_required
def admin_profile():
    # Check if user is admin using role
    if current_user.role != 'Admin':
        return "Unauthorized", 403

    # Get the admin data
    admin = Admin.query.get(current_user.id)

    # Simple stats (replace with actual queries later)
    total_elections = 12
    total_votes = 340

    return render_template('admin_profile.html', 
                           admin=admin,
                           total_elections=total_elections,
                           total_votes=total_votes)




@admin_bp.route('/statistics')
@admin_required
def statistics():
    import pytz
    tz = pytz.timezone('Asia/Manila')

    # Get all ended elections
    all_elections = Election.query.all()
    past_elections = [e for e in all_elections if e.status == "Ended"]
    past_elections.sort(key=lambda x: x.end_date, reverse=True)

    election_stats = []

    # Global metrics
    total_voted_students_all = 0
    all_margins = []
    candidate_counts = []
    month_count = {}
    largest_election = None
    largest_voters = 0

    for election in past_elections:
        votes_per_candidate = {}
        candidate_roles = {}  # Store the role/position name
        candidate_roles_with_id = {}  # Store position details with ID and color
        voter_ids = set()
        total_votes = 0

        for candidate in election.candidates:
            full_name = f"{candidate.first_name} {candidate.last_name}"
            # FIXED: Use PHE-compatible vote counting
            vote_count = count_votes_for_candidate(candidate.id, election.id)
            votes_per_candidate[full_name] = vote_count
            total_votes += vote_count

            # Store role/position as string (JSON serializable)
            position_name = candidate.position.name if candidate.position else 'Other'
            candidate_roles[full_name] = position_name
            
            # Store position details with ID and color for sorting
            if candidate.position:
                candidate_roles_with_id[full_name] = {
                    'position_id': candidate.position.id,
                    'name': candidate.position.name,
                    'color': candidate.position.color or '#adb5bd'
                }
            else:
                candidate_roles_with_id[full_name] = {
                    'position_id': 999,  # Default high number for 'Other'
                    'name': 'Other',
                    'color': '#adb5bd'
                }

        # Get all unique voters for this election
        voter_ids = get_all_voters_for_election(election.id)
        total_voted_students = len(voter_ids)
        total_voted_students_all += total_voted_students

        # Determine winner (for info)
        if votes_per_candidate and total_votes > 0:
            winner = max(votes_per_candidate, key=votes_per_candidate.get)
            winning_votes = votes_per_candidate[winner]
            winning_percentage = round((winning_votes / total_votes) * 100, 1)
        else:
            winner = "No votes"
            winning_percentage = 0

        election_stats.append({
            'title': election.title,
            'election_type': election.election_type,
            'department': election.department,
            'course': getattr(election.course_rel, 'course_name', None) if election.course_rel else None,
            'start_date': election.start_date.astimezone(tz).strftime('%Y-%m-%d %H:%M'),
            'end_date': election.end_date.astimezone(tz).strftime('%Y-%m-%d %H:%M'),
            'votes': votes_per_candidate,
            'candidate_roles': candidate_roles,
            'candidate_roles_with_id': candidate_roles_with_id,  # New: includes position_id and color
            'winner': winner,
            'total_voters': total_voted_students,
            'winning_percentage': winning_percentage
        })

        candidate_counts.append(len(votes_per_candidate))

        # Margin (top 2 candidates)
        if len(votes_per_candidate) > 1 and total_votes > 0:
            sorted_votes = sorted(votes_per_candidate.values(), reverse=True)
            margin = ((sorted_votes[0] - sorted_votes[1]) / total_votes) * 100
            all_margins.append(round(margin, 1))

        # Most active month
        month = election.end_date.strftime('%Y-%m')
        month_count[month] = month_count.get(month, 0) + 1

        # Largest election
        if total_voted_students > largest_voters:
            largest_voters = total_voted_students
            largest_election = election.title

    # Final KPIs
    avg_participation = round(total_voted_students_all / len(past_elections), 1) if past_elections else 0
    closest_margin = round(min(all_margins), 1) if all_margins else 0
    avg_candidates = round(sum(candidate_counts) / len(candidate_counts), 1) if candidate_counts else 0
    most_active_month = max(month_count.items(), key=lambda x: x[1])[0] if month_count else '--'
    largest_election = largest_election or '--'

    # Departments for filter
    departments = Department.query.order_by(Department.name).all()

    # Courses (colleges) for dependent dropdown
    colleges = Course.query.all()
    college_data = [{
        'id': c.id,
        'course_name': c.course_name,
        'department': {
            'id': c.department.id,
            'name': c.department.name
        } if c.department else None
    } for c in colleges]
    
    # ---------- AUDIT LOG: Statistics page viewed ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='STATISTICS_VIEW',
        description=f"Admin user '{username}' viewed the election statistics page from IP: {ip} | Total past elections: {len(past_elections)}, Average participation: {avg_participation}, Average candidates: {avg_candidates}, Closest margin: {closest_margin}%, Most active month: {most_active_month}, Largest election: '{largest_election}' ({largest_voters} voters)"
    )

    return render_template(
        'statistics.html',
        election_stats=election_stats,
        departments=departments,
        collegeData=college_data,
        avg_participation=avg_participation,
        closest_margin=closest_margin,
        avg_candidates=avg_candidates,
        most_active_month=most_active_month,
        largest_election=largest_election
    )


@admin_bp.route("/audit-logs", methods=["GET"])
def audit_logs():
    import pytz  # Add this import
    
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    export = request.args.get("export")

    query = AuditLog.query

    # 🔎 SEARCH FILTER
    if search:
        query = query.filter(
            or_(
                AuditLog.action.ilike(f"%{search}%"),
                AuditLog.role.ilike(f"%{search}%"),
                AuditLog.description.ilike(f"%{search}%")
            )
        )

    # 📅 DATE FILTER (FIXED PROPERLY)
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(AuditLog.timestamp >= start_date_obj)
        except ValueError:
            pass

    if end_date:
        try:
            # Add 1 day to include full end date
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
            query = query.filter(AuditLog.timestamp <= end_date_obj)
        except ValueError:
            pass

    # ORDER BY LATEST FIRST
    query = query.order_by(desc(AuditLog.timestamp))

    # 📥 EXPORT CSV
    if export == "csv":
        logs = query.all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["ID", "User ID", "Role", "Action", "Description", "IP Address", "Timestamp (Manila Time)"])

        tz = pytz.timezone('Asia/Manila')
        
        for log in logs:
            # Convert UTC to Manila time for CSV export
            if log.timestamp:
                manila_time = log.timestamp.replace(tzinfo=pytz.UTC).astimezone(tz)
                timestamp_str = manila_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp_str = ""
                
            writer.writerow([
                log.id,
                log.user_id,
                log.role,
                log.action,
                log.description,
                log.ip_address,
                timestamp_str
            ])

        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name="audit_logs.csv"
        )

    # 📄 PAGINATION
    logs = query.paginate(page=page, per_page=20)
    
    # Pass pytz to template
    return render_template(
        "audit_logs.html",
        logs=logs,
        search=search,
        start_date=start_date,
        end_date=end_date,
        pytz=pytz  # Add this
    )


@admin_bp.route("/audit-logs-ajax", methods=["GET"])
def audit_logs_ajax():
    """AJAX endpoint for audit logs pagination"""
    import pytz
    
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    query = AuditLog.query

    # 🔎 SEARCH FILTER
    if search:
        query = query.filter(
            or_(
                AuditLog.action.ilike(f"%{search}%"),
                AuditLog.role.ilike(f"%{search}%"),
                AuditLog.description.ilike(f"%{search}%")
            )
        )

    # 📅 DATE FILTER
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(AuditLog.timestamp >= start_date_obj)
        except ValueError:
            pass

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
            query = query.filter(AuditLog.timestamp <= end_date_obj)
        except ValueError:
            pass

    # ORDER BY LATEST FIRST
    query = query.order_by(desc(AuditLog.timestamp))

    # 📄 PAGINATION
    logs = query.paginate(page=page, per_page=20)
    
    # Return just the table partial
    return render_template(
        "partials/audit_logs_table.html",
        logs=logs,
        search=search,
        start_date=start_date,
        end_date=end_date,
        pytz=pytz
    )



    
# ---------------------- Logout ---------------------- #
@admin_bp.route('/logout')
@admin_required
def logout():
    # ---------- AUDIT LOG: Logout ----------
    if current_user.is_authenticated:
        username = getattr(current_user, 'username', 'Unknown')
        ip = request.remote_addr
        
        log_audit(
            action='LOGOUT',
            description=f"Admin user '{username}' logged out from IP: {ip}"
        )
    
    logout_user()
    flash('Admin has been logged out.', 'info')
    return redirect(url_for('admin.login'))