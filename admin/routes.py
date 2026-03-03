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
from admin.models import AuditLog
from admin.utils import log_audit
import pandas as pd





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
    if 'pre_2fa_admin_id' not in session:
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
        
        # ---------- AUDIT LOG: 2FA in cooldown ----------
        log_audit(
            action='2FA_COOLDOWN',
            description=f"Admin user '{admin.username}' 2FA verification in cooldown. Remaining: {remaining}s from IP: {ip}"
        )
        
        return render_template('admin_2fa_verify.html', error=error)

    error = None
    success_message = session.pop('2fa_success', None)  # Check for existing success message
    
    if request.method == 'POST':
        # ✅ Ensure totp_secret is generated
        totp_secret = generate_2fa_secret(admin)
        totp = pyotp.TOTP(totp_secret)

        code = request.form.get('code')
        if totp.verify(code):
            # Success: log in the user
            login_user(admin)
            session.permanent = True

            # ---------- AUDIT LOG: 2FA verification successful ----------
            log_audit(
                action='2FA_SUCCESS',
                description=f"Admin user '{admin.username}' successfully verified 2FA code from IP: {ip}"
            )

            # Cleanup session keys
            session.pop('pre_2fa_admin_id', None)
            session.pop(f'2fa_attempts_{ip}', None)
            session.pop(f'2fa_cooldown_{ip}', None)

            # Set success message in session for this page only
            session['2fa_success'] = "2FA verified. Welcome, Admin."
            
            return redirect(url_for('admin.verify_2fa'))  # Redirect to same page to show success

        else:
            # Increment failed 2FA attempts
            attempts += 1
            session[f'2fa_attempts_{ip}'] = attempts

            # ---------- AUDIT LOG: Failed 2FA attempt ----------
            log_audit(
                action='2FA_FAILED',
                description=f"Admin user '{admin.username}' failed 2FA verification. Attempt {attempts} of {MAX_2FA_ATTEMPTS} from IP: {ip}"
            )

            if attempts >= MAX_2FA_ATTEMPTS:
                session[f'2fa_cooldown_{ip}'] = time.time() + TWO_FA_COOLDOWN
                session[f'2fa_attempts_{ip}'] = 0
                error = "Too many invalid codes. 2FA temporarily locked."
                
                # ---------- AUDIT LOG: 2FA locked ----------
                log_audit(
                    action='2FA_LOCKED',
                    description=f"Admin user '{admin.username}' 2FA temporarily locked for IP: {ip} due to {MAX_2FA_ATTEMPTS} failed attempts. Cooldown: {TWO_FA_COOLDOWN}s"
                )
            else:
                error = f"Invalid code. Attempt {attempts} of {MAX_2FA_ATTEMPTS}."

    return render_template('admin_2fa_verify.html', error=error, success=success_message)



# ------------------- 2FA Secret Generation ------------------- #
def generate_2fa_secret(admin):
    if not getattr(admin, 'totp_secret', None):
        admin.totp_secret = pyotp.random_base32()
        db.session.commit()
        
        # ---------- AUDIT LOG: 2FA secret generated ----------
        log_audit(
            action='2FA_SECRET_GENERATED',
            description=f"2FA secret generated for admin user '{admin.username}'"
        )
        
    return admin.totp_secret


# ------------------- Admin 2FA Setup ------------------- #
@admin_bp.route('/2fa/setup', methods=['GET', 'POST'])
@admin_required
def setup_2fa():
    admin = current_user
    secret = generate_2fa_secret(admin)
    totp = pyotp.TOTP(secret)

    # ---------- AUDIT LOG: 2FA setup page viewed ----------
    log_audit(
        action='2FA_SETUP_VIEW',
        description=f"Admin user '{admin.username}' viewed 2FA setup page"
    )

    if request.method == 'POST':
        code = request.form.get('code')
        if totp.verify(code):
            admin.is_2fa_enabled = True
            db.session.commit()
            
            # ---------- AUDIT LOG: 2FA successfully enabled ----------
            log_audit(
                action='2FA_ENABLED',
                description=f"Admin user '{admin.username}' successfully enabled 2FA"
            )
            
            flash("Two-factor authentication enabled!", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            # ---------- AUDIT LOG: 2FA setup failed ----------
            log_audit(
                action='2FA_SETUP_FAILED',
                description=f"Admin user '{admin.username}' failed to verify 2FA code during setup"
            )
            
            flash("Invalid code. Try again.", "error")

    totp_uri = totp.provisioning_uri(
        name=admin.email,
        issuer_name="CTU-COMELEC Admin"
    )
    return render_template('admin_2fa_setup.html', totp_uri=totp_uri, secret=secret)



# ---------------------- DASHBOARD ---------------------- #
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)

    # ================================
    # KPI counts
    # ================================
    total_students = Student.query.count()
    total_candidates = Candidate.query.count()
    total_elections = Election.query.count()
    total_votes = Vote.query.count()

    # ================================
    # Recent elections table
    # ================================
    elections = Election.query.order_by(Election.start_date.desc()).all()
    recent_elections_all = elections

    # Localize timezone if naive
    for election in recent_elections_all:
        if election.start_date.tzinfo is None:
            election.start_date = tz.localize(election.start_date)
        if election.end_date.tzinfo is None:
            election.end_date = tz.localize(election.end_date)

    recent_elections = recent_elections_all[:5]
    ongoing_elections = sum(1 for e in recent_elections_all if e.status == 'Open')

    # Calculate voter turnout
    voter_turnout = "0%"
    if total_students > 0:
        turnout_percentage = (total_votes / total_students) * 100
        voter_turnout = f"{turnout_percentage:.1f}%"

    # ================================
    # Convert elections to JSON-serializable format for calendar
    # ================================
    elections_for_calendar = []
    for election in recent_elections_all:
        elections_for_calendar.append({
            'id': election.id,
            'title': election.title,
            'description': election.description,
            'election_type': election.election_type,
            'scope': election.scope,
            'department': election.department,  # department name
            'department_id': election.department_id,
            'start_date': election.start_date.isoformat() if election.start_date else None,
            'end_date': election.end_date.isoformat() if election.end_date else None,
            'status': election.status,  # This calls the property method
            'year_levels': election.year_levels,
            'year_levels_list': election.year_levels_list,
        })

    # ---------- AUDIT LOG: Dashboard viewed ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='DASHBOARD_VIEW',
        description=f"Admin user '{username}' viewed the dashboard from IP: {ip} | Stats: {total_students} students, {total_candidates} candidates, {total_elections} elections, {total_votes} votes"
    )

    return render_template(
        'admin_dashboard.html',
        admin=current_user,
        total_students=total_students,
        total_candidates=total_candidates,
        total_elections=total_elections,
        ongoing_elections=ongoing_elections,
        total_votes=total_votes,
        voter_turnout=voter_turnout,
        recent_elections=recent_elections,
        recent_elections_all=recent_elections_all,
        elections_for_calendar=elections_for_calendar,  # This is the serializable version
        now=now
    )


# Add these imports at the top of your admin/routes.py if not already present
from datetime import datetime, timedelta
from sqlalchemy import func
from flask import jsonify
import pytz

# ===================== VOTING TRENDS API =====================
@admin_bp.route('/api/voting-trends')
@admin_required
def get_voting_trends():
    """API endpoint to get voting trends data for charts"""
    try:
        # Get parameters
        election_id = request.args.get('election_id', 'all')
        
        # Get timezone
        tz = pytz.timezone('Asia/Manila')
        
        # Get last 24 hours
        end_date = datetime.now(tz)
        start_date = end_date - timedelta(hours=24)
        
        # Create a list of all hours in the last 24 hours
        hours = []
        current = start_date
        while current <= end_date:
            hours.append(current.strftime('%Y-%m-%d %H:00'))
            current += timedelta(hours=1)
        
        # Base query for votes
        if election_id != 'all':
            # Filter by specific election
            votes = Vote.query.filter(
                Vote.election_id == election_id,
                Vote.cast_timestamp >= start_date,
                Vote.cast_timestamp <= end_date
            ).all()
        else:
            # All elections
            votes = Vote.query.filter(
                Vote.cast_timestamp >= start_date,
                Vote.cast_timestamp <= end_date
            ).all()
        
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
        
        # Get all elections for the filter buttons
        elections = Election.query.order_by(Election.start_date.desc()).all()
        election_list = []
        
        # Add "All Elections" option
        all_votes_count = Vote.query.count()
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
            
            # Count votes for this election
            vote_count = Vote.query.filter_by(election_id=e.id).count()
            
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
            'current_election': election_id
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
        if election_id == 'all':
            # All elections combined
            total_votes = Vote.query.count()
            total_eligible = Student.query.count()
            
            # Get ongoing elections count
            ongoing = Election.query.filter(Election.start_date <= datetime.now(pytz.timezone('Asia/Manila')),
                                          Election.end_date >= datetime.now(pytz.timezone('Asia/Manila'))).count()
            
            # Calculate turnout
            if total_eligible > 0:
                turnout = f"{(total_votes/total_eligible*100):.1f}%"
            else:
                turnout = "0%"
            
            return jsonify({
                'success': True,
                'total_votes': total_votes,
                'total_eligible': total_eligible,
                'turnout': turnout,
                'election_title': 'All Elections',
                'election_scope': 'Combined',
                'ongoing_elections': ongoing
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
            
            # Get votes for this election
            total_votes = Vote.query.filter_by(election_id=election.id).count()
            
            # Calculate turnout
            if eligible_students > 0:
                turnout = f"{(total_votes/eligible_students*100):.1f}%"
            else:
                turnout = "0%"
            
            return jsonify({
                'success': True,
                'total_votes': total_votes,
                'total_eligible': eligible_students,
                'turnout': turnout,
                'election_title': election.title,
                'election_scope': 'Campus-wide' if election.scope == 'campus' else 'Departmental',
                'election_status': election.status,
                'start_date': election.start_date.strftime('%Y-%m-%d %H:%M') if election.start_date else 'N/A',
                'end_date': election.end_date.strftime('%Y-%m-%d %H:%M') if election.end_date else 'N/A'
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

from student.models import TrustedDevice 
# ---------------------- IMPORT STUDENTS ---------------------- #
@admin_bp.route("/import_students", methods=["GET", "POST"])
def import_students():

    if request.method == "POST":
        file = request.files.get("excel_file")

        if not file or file.filename == "":
            flash("No file selected.", "import-danger")
            return redirect(url_for("admin.import_students"))

        try:
            # STEP 1: Read Excel (force StudentNo as string)
            df = pd.read_excel(file, dtype={"StudentNo": str})

            # STEP 2: Clean column names
            df.columns = (
                df.columns
                .astype(str)
                .str.strip()
                .str.replace("\u00a0", "", regex=False)
                .str.replace("\t", "", regex=False)
            )

            # STEP 3: Validate columns
            required_columns = ["StudentNo", "LastName", "FirstName"]
            for col in required_columns:
                if col not in df.columns:
                    flash(f"Missing required column: {col}", "import-danger")
                    return redirect(url_for("admin.import_students"))

            # STEP 4: Build set of StudentNos from Excel
            excel_student_nos = set()
            excel_students_data = {}  # Store full data for later use

            imported = 0
            updated = 0

            for _, row in df.iterrows():
                student_number = str(row["StudentNo"]).strip()

                # Remove trailing .0 if Excel casted it
                if student_number.endswith(".0"):
                    student_number = student_number[:-2]

                first_name = str(row["FirstName"]).strip()
                last_name  = str(row["LastName"]).strip()

                if not student_number or student_number.lower() == "nan":
                    continue

                excel_student_nos.add(student_number)
                excel_students_data[student_number] = {
                    'first_name': first_name,
                    'last_name': last_name
                }

                exists = CtuStudent.query.filter_by(
                    student_number=student_number
                ).first()

                if exists:
                    # Update existing record
                    exists.first_name = first_name
                    exists.last_name = last_name
                    db.session.add(exists)
                    updated += 1
                else:
                    # Insert new record
                    s = CtuStudent(
                        student_number=student_number,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    db.session.add(s)
                    imported += 1

            # STEP 5: Get all current CTU students
            db_students = CtuStudent.query.all()
            
            deleted_from_ctu = 0
            deleted_from_registration = 0
            kept_with_votes = 0

            # STEP 6: Check each student in CTU list
            for s in db_students:
                if s.student_number not in excel_student_nos:
                    # This student is NOT in the new Excel file
                    
                    # Check if this student is registered in students table
                    registered_student = Student.query.filter_by(id_number=s.student_number).first()
                    
                    if registered_student:
                        # Check if this student has any votes
                        votes = Vote.query.filter_by(student_id=registered_student.id).count()
                        
                        if votes > 0:
                            # Student has votes - keep for audit
                            kept_with_votes += 1
                            print(f"Student {registered_student.id_number} has {votes} votes - keeping record")
                            
                            # OPTIONAL: You can mark them as inactive if you have a status field
                            # registered_student.status = 'graduated'
                            # db.session.add(registered_student)
                        else:
                            # NO votes - SAFE TO DELETE from students table
                            # First, manually delete related trusted devices
                            from student.models import TrustedDevice
                            TrustedDevice.query.filter_by(student_id=registered_student.id).delete()
                            
                            # Also delete any other related records if needed
                            # (votes are already checked and are 0, so no need to delete votes)
                            
                            # Now delete the student
                            db.session.delete(registered_student)
                            deleted_from_registration += 1
                            print(f"Deleted registered student: {registered_student.id_number}")
                    
                    # ALWAYS delete from ctu_students table
                    db.session.delete(s)
                    deleted_from_ctu += 1
                    print(f"Deleted from CTU list: {s.student_number}")

            # STEP 7: Commit all changes
            db.session.commit()

            # ---------- AUDIT LOG: Student import completed ----------
            username = getattr(current_user, 'username', 'Unknown') if current_user.is_authenticated else 'Unknown'
            ip = request.remote_addr
            filename = file.filename if file else 'Unknown'
            
            log_audit(
                action='IMPORT_STUDENTS',
                description=f"Admin user '{username}' imported students from '{filename}' from IP: {ip} | Imported: {imported}, Updated: {updated}, Deleted from CTU: {deleted_from_ctu}, Deleted registered: {deleted_from_registration}, Kept with votes: {kept_with_votes}"
            )

            # Create appropriate flash message
            if deleted_from_registration > 0:
                flash(
                    f"✅ Sync complete!\n"
                    f"📥 Imported: {imported}\n"
                    f"🔄 Updated: {updated}\n"
                    f"🗑️ Removed from CTU list: {deleted_from_ctu}\n"
                    f"🚫 Removed registered students: {deleted_from_registration}\n"
                    f"⚠️ Kept (with votes): {kept_with_votes}",
                    "import-success"
                )
            else:
                flash(
                    f"Sync complete. Imported: {imported}, Updated: {updated}, "
                    f"Removed from CTU list: {deleted_from_ctu}",
                    "import-success"
                )
                
            return redirect(url_for("admin.import_students"))

        except Exception as e:
            db.session.rollback()
            print(f"ERROR: {str(e)}")  # For debugging
            
            # ---------- AUDIT LOG: Student import failed ----------
            username = getattr(current_user, 'username', 'Unknown') if current_user.is_authenticated else 'Unknown'
            ip = request.remote_addr
            filename = file.filename if file else 'Unknown'
            
            log_audit(
                action='IMPORT_STUDENTS_FAILED',
                description=f"Admin user '{username}' failed to import students from '{filename}' from IP: {ip} | Error: {str(e)}"
            )
            
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
    # -------------------- Fetch Departments & Courses -------------------- #
    departments = Department.query.order_by(Department.name).all()
    courses = Course.query.order_by(Course.course_name).all()

    departments_data = [{"id": d.id, "name": d.name} for d in departments]
    courses_data = [{"id": c.id, "name": c.course_name} for c in courses]

    # -------------------- Fetch Elections with scope -------------------- #
    elections = Election.query.order_by(Election.start_date.desc()).all()
    elections_data = [{
        "id": e.id, 
        "title": e.title,
        "scope": e.scope  # Make sure to include scope!
    } for e in elections]

    # ---------- AUDIT LOG: Manage Students page viewed ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='MANAGE_STUDENTS_VIEW',
        description=f"Admin user '{username}' viewed the manage students page from IP: {ip}"
    )

    # -------------------- Render Template -------------------- #
    return render_template(
        'manage_students.html',
        departments=departments_data,
        courses=courses_data,
        elections=elections_data
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
        
        # 🎯 NEW: Filter students based on election's year levels
        if election and election.scope == 'campus' and election.year_levels:
            # Join with year_level to filter by year
            if election.year_levels != 'all':
                # Get list of allowed year levels
                allowed_years = election.year_levels.split(',')
                
                # Filter students whose year_level_id matches allowed years
                # Assuming year_level_id corresponds to year (1,2,3,4)
                query = query.filter(Student.year_level_id.in_(allowed_years))
            
            # For department elections, we might also want to filter by department
            # But that's usually handled by the election.department_id field
            
        # 🎯 NEW: For department elections, filter by department
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
            "year_level_id": s.year_level_id,  # Add this for debugging if needed
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



@admin_bp.route('/candidates', methods=['GET', 'POST'])
@admin_required
def manage_candidates():
    positions = Position.query.all()
    departments = Department.query.order_by(Department.name).all()
    elections = Election.query.order_by(Election.start_date.desc()).all()

    # ================= FILTER =================
    selected_scope = request.args.get('scope', default=None)
    department_id = request.args.get('department_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 10
    selected_department = None

    query = Candidate.query

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
        department_id_form = request.form.get('department_id', type=int)
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

        # Validate department based on scope
        if scope == 'department':
            if not department_id_form:
                if is_ajax:
                    return jsonify({'success': False, 'message': 'Department is required for Department Elections.'})
                flash('Department is required for Department Elections.', 'danger')
                return redirect(url_for('admin.manage_candidates'))
            
            # Verify department matches election
            if election.department_id and election.department_id != department_id_form:
                if is_ajax:
                    return jsonify({'success': False, 'message': f'This candidate must belong to {election.department} department.'})
                flash(f'This candidate must belong to {election.department} department.', 'danger')
                return redirect(url_for('admin.manage_candidates'))
        else:
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

        # Create candidate with scope
        new_candidate = Candidate(
            first_name=first_name,
            last_name=last_name,
            party_list=party_list if party_list else None,
            department_id=department_id_form,
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
        
        log_audit(
            action='CREATE_CANDIDATE',
            description=f"Added candidate: {first_name} {last_name} | Party: {party_list_name} | Position: {position_name} | Department: {department_name} | Election: {election_title} ({scope})"
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
                'department': new_candidate.department.name if new_candidate.department else '',
                'department_id': new_candidate.department_id,
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
        selected_scope=selected_scope
    )


@admin_bp.route('/candidates/filter', methods=['GET'])
@admin_required
def filter_candidates():
    """AJAX endpoint for filtering candidates"""
    selected_scope = request.args.get('scope', default=None)
    department_id = request.args.get('department_id', type=int)
    search = request.args.get('search', default='')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = Candidate.query

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
            'department': c.department.name if c.department else '',
            'department_id': c.department_id,
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
        }
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
    old_position = candidate.position.name if candidate.position else 'N/A'
    old_department = candidate.department.name if candidate.department else 'N/A'
    old_scope = candidate.scope

    # Get form data
    candidate.first_name = request.form.get('first_name')
    candidate.last_name = request.form.get('last_name')
    
    party_list = request.form.get('party_list')
    candidate.party_list = party_list if party_list else None
    
    candidate.position_id = request.form.get('position_id')
    candidate.election_id = request.form.get('election_id')
    
    scope = request.form.get('scope')
    candidate.scope = scope  # Update scope
    
    department_id = request.form.get('department_id', type=int)
    
    # Get election to verify
    election = Election.query.get(candidate.election_id)
    
    # Handle department based on scope
    if scope == 'department':
        if not department_id:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Department is required.'})
            flash('Department is required.', 'danger')
            return redirect(url_for('admin.manage_candidates'))
        
        if election and election.department_id and election.department_id != department_id:
            if is_ajax:
                return jsonify({'success': False, 'message': f'Must belong to {election.department}.'})
            flash(f'Must belong to {election.department}.', 'danger')
            return redirect(url_for('admin.manage_candidates'))
        
        candidate.department_id = department_id
    else:
        candidate.department_id = None

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
            'department': candidate.department.name if candidate.department else '',
            'department_id': candidate.department_id,
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
    
    # Get currently configured positions for this election
    configured_positions = ElectionPosition.query.filter_by(election_id=election_id).all()
    configured_position_ids = [ep.position_id for ep in configured_positions]
    configured_positions_dict = {ep.position_id: ep.max_votes for ep in configured_positions}
    
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
            
            ep = ElectionPosition(
                election_id=election_id,
                position_id=position_id,
                max_votes=max_votes,
                min_votes=1,  # Default minimum
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
        return redirect(url_for('admin.create_election'))
    
    # For GET request, pass ALL needed variables to template
    return render_template(
        'configure_election_positions.html',
        election=election,  # This is the key line that was missing
        all_positions=all_positions,
        configured_position_ids=configured_position_ids,
        configured_positions=configured_positions_dict
    )

# admin/routes.py - REPLACE your existing create_department_election route
@admin_bp.route('/create-election', methods=['GET', 'POST'])
@admin_required
def create_election():
    """
    IMPROVED CREATE ELECTION ROUTE
    - Handles both campus and department elections
    - Adds year level filtering for campus elections
    - Redirects to position configuration after creation
    """
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
            flash('All required fields must be filled.', 'election')
            return redirect(url_for('admin.create_election'))

        if scope not in ['campus', 'department']:
            flash('Invalid election scope. Must be campus or department.', 'election')
            return redirect(url_for('admin.create_election'))

        # Parse dates
        try:
            start_date = tz.localize(datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M'))
            end_date = tz.localize(datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M'))
        except ValueError:
            flash('Invalid date format.', 'election')
            return redirect(url_for('admin.create_election'))

        if end_date <= start_date:
            flash('End date must be later than start date.', 'election')
            return redirect(url_for('admin.create_election'))

        # Handle department based on scope
        department_id = None
        department_name = None
        
        if scope == 'department':
            if not department_id_str:
                flash('Department is required for Department Elections.', 'election')
                return redirect(url_for('admin.create_election'))
            
            department_id = int(department_id_str)
            dept_obj = Department.query.get(department_id)
            if not dept_obj:
                flash('Selected department does not exist.', 'election')
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
        flash('Election created successfully! Now configure positions and vote limits.', 'success')
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


    # ----------- GET ANNOUNCEMENT FOR EDIT -----------
@admin_bp.route('/get-announcement/<int:announcement_id>')
@login_required
def get_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    
    return jsonify({
        'success': True,
        'announcement': {
            'id': announcement.id,
            'title': announcement.title,
            'content': announcement.content,
            'date': announcement.date.strftime('%Y-%m-%d'),
            'department_id': announcement.department_id
        }
    })

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
    
    flash('Announcement updated successfully!', 'success')
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
    
    flash('Announcement deleted successfully!', 'success')
    return redirect(url_for('admin.announcements'))



@admin_bp.route('/results')
@admin_required
def results_page():
    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)
    
    elections = Election.query.order_by(Election.end_date.desc()).all()
    
    upcoming, active, completed = [], [], []
    
    for election in elections:
        # Create timezone-aware copies for comparison
        start_date = election.start_date
        end_date = election.end_date
        
        # Convert to timezone-aware if naive
        if start_date.tzinfo is None:
            start_date = tz.localize(start_date)
        if end_date.tzinfo is None:
            end_date = tz.localize(end_date)
        
        # Add timezone-aware attributes to election object for template use
        election.tz_start = start_date
        election.tz_end = end_date
        
        # Categorize based on the dates
        if end_date < now:
            completed.append(election)
        elif start_date <= now <= end_date:
            active.append(election)
        else:
            upcoming.append(election)
    
    # ---------- AUDIT LOG: Results page viewed ----------
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='RESULTS_PAGE_VIEW',
        description=f"Admin user '{username}' viewed the results page from IP: {ip} | Total elections: {len(elections)}, Active: {len(active)}, Completed: {len(completed)}, Upcoming: {len(upcoming)}"
    )
    
    return render_template(
        'admin_results.html',
        upcoming_elections=upcoming,
        active_elections=active,
        completed_elections=completed,
        now=now
    )


@admin_bp.route('/results/<int:election_id>')
@admin_required
def election_results(election_id):
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
    else:
        is_tallied = check_if_tallied(election_id)
        if is_tallied:
            tally_timestamp = get_tally_timestamp(election_id)
    
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    candidate_results = []
    total_votes_cast = 0
    
    # COUNT UNIQUE VOTERS (students who have voted in this election)
    unique_voters = db.session.query(Vote.student_id).filter_by(
        election_id=election_id
    ).distinct().count()
    
    # GET POSITION LIMITS FROM ElectionPosition TABLE
    position_limits = {}
    election_positions = ElectionPosition.query.filter_by(election_id=election_id).all()
    for ep in election_positions:
        position_limits[ep.position_id] = ep.max_votes
    
    # FIRST PASS: Get vote counts for all candidates
    if is_tallied and TALLY_VOTE_AVAILABLE:
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
                'voter_percentage': 0,  # Percentage based on voters
                'is_tallied': True
            })
            total_votes_cast += vote_count
    else:
        for candidate in candidates:
            vote_count = count_votes_for_candidate(candidate.id, election_id)
            
            candidate_results.append({
                'id': candidate.id,
                'first_name': candidate.first_name,
                'last_name': candidate.last_name,
                'photo': candidate.photo,
                'position': candidate.position.name if candidate.position else "N/A",
                'position_id': candidate.position_id,
                'department': candidate.department.name if candidate.department else "All Departments",
                'vote_count': vote_count,
                'voter_percentage': 0,  # Percentage based on voters
                'is_tallied': is_tallied
            })
            total_votes_cast += vote_count
    
    # ===== CORRECTED: Calculate percentages based on UNIQUE VOTERS =====
    # This works the same for both single and multi-winner positions
    if unique_voters > 0:
        for candidate in candidate_results:
            # Percentage of voters who voted for this candidate
            candidate['voter_percentage'] = round((candidate['vote_count'] / unique_voters) * 100, 2)
    
    # Group candidates by position for winner determination
    candidates_by_position = {}
    for candidate in candidate_results:
        position = candidate['position']
        if position not in candidates_by_position:
            candidates_by_position[position] = []
        candidates_by_position[position].append(candidate)
    
    # Sort candidates within each position by vote count (descending)
    for position in candidates_by_position:
        candidates_by_position[position].sort(key=lambda x: x['vote_count'], reverse=True)
    
    # Determine winners for each position based on max_votes
    winners_by_position = {}
    
    for position_name, candidates_in_pos in candidates_by_position.items():
        if candidates_in_pos:
            position_id = candidates_in_pos[0]['position_id']
            max_winners = position_limits.get(position_id, 1)
            
            # Take the top N candidates where N = max_winners
            winners = []
            for i, candidate in enumerate(candidates_in_pos):
                if i < max_winners and candidate['vote_count'] > 0:
                    winners.append(candidate)
                else:
                    break
            
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
    
    if election.department_id:
        total_eligible_voters = Student.query.filter_by(department_id=election.department_id).count()
    else:
        total_eligible_voters = Student.query.count()
    
    voter_turnout = round((unique_voters / total_eligible_voters * 100), 2) if total_eligible_voters > 0 else 0
    students_not_voted = total_eligible_voters - unique_voters
    
    # ---------- AUDIT LOG ----------
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
        total_voters=unique_voters,  # Renamed for clarity
        total_votes_cast=total_votes_cast,
        total_eligible_voters=total_eligible_voters,
        voter_turnout=voter_turnout,
        students_not_voted=students_not_voted,
        status=status,
        now=now,
        is_tallied=is_tallied,
        tally_timestamp=tally_timestamp
    )

    
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


# Add this import at the top of your admin/routes.py
from weasyprint import HTML
from io import BytesIO
from flask import make_response

@admin_bp.route('/results/<int:election_id>/export-pdf')
@admin_required
def export_results_pdf(election_id):
    """Export election results as PDF using WeasyPrint"""
    
    # ========== YOUR EXISTING DATA FETCHING CODE (EXACTLY THE SAME) ==========
    election = Election.query.get_or_404(election_id)
    
    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)
    
    if election.start_date.tzinfo is None:
        election.start_date = tz.localize(election.start_date)
    if election.end_date.tzinfo is None:
        election.end_date = tz.localize(election.end_date)
    
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
    
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    candidate_results = []
    total_votes_cast = 0
    
    unique_voters = db.session.query(Vote.student_id).filter_by(
        election_id=election_id
    ).distinct().count()
    
    if is_tallied and TALLY_VOTE_AVAILABLE:
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
                'department': candidate.department.name if candidate.department else "All Departments",
                'vote_count': vote_count,
                'vote_percentage': 0,
                'is_tallied': True
            })
            total_votes_cast += vote_count
    else:
        for candidate in candidates:
            vote_count = count_votes_for_candidate(candidate.id, election_id)
            
            candidate_results.append({
                'id': candidate.id,
                'first_name': candidate.first_name,
                'last_name': candidate.last_name,
                'photo': candidate.photo,
                'position': candidate.position.name if candidate.position else "N/A",
                'department': candidate.department.name if candidate.department else "All Departments",
                'vote_count': vote_count,
                'vote_percentage': 0,
                'is_tallied': is_tallied
            })
            total_votes_cast += vote_count
    
    if total_votes_cast > 0:
        for candidate in candidate_results:
            candidate['vote_percentage'] = round((candidate['vote_count'] / total_votes_cast) * 100, 2)
    
    candidate_results.sort(key=lambda x: x['vote_count'], reverse=True)
    
    winners_by_position = {}
    for candidate in candidate_results:
        position = candidate['position']
        if position not in winners_by_position:
            winners_by_position[position] = candidate
        elif candidate['vote_count'] > winners_by_position[position]['vote_count']:
            winners_by_position[position] = candidate
    
    if election.department_id:
        total_eligible_voters = Student.query.filter_by(department_id=election.department_id).count()
    else:
        total_eligible_voters = Student.query.count()
    
    voter_turnout = round((unique_voters / total_eligible_voters * 100), 2) if total_eligible_voters > 0 else 0
    students_not_voted = total_eligible_voters - unique_voters
    
    # ========== RENDER THE HTML TEMPLATE ==========
    html = render_template(
        'election_results_pdf.html',
        election=election,
        candidate_results=candidate_results,
        winners_by_position=winners_by_position,
        total_votes_cast=unique_voters,
        total_votes_for_positions=total_votes_cast,
        total_eligible_voters=total_eligible_voters,
        voter_turnout=voter_turnout,
        students_not_voted=students_not_voted,
        now=now,
        is_tallied=is_tallied,
        tally_timestamp=tally_timestamp
    )
    
    # ========== GENERATE PDF USING WEASYPRINT ==========
    # Create a buffer for the PDF
    pdf_buffer = BytesIO()
    
    try:
        # Convert HTML to PDF using WeasyPrint
        HTML(string=html).write_pdf(pdf_buffer)
    except Exception as e:
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500
    
    # Get the PDF from the buffer
    pdf_buffer.seek(0)
    
    # Create response
    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={election.title.replace(" ", "_")}_results.pdf'
    
    # ========== AUDIT LOG ==========
    username = getattr(current_user, 'username', 'Unknown')
    ip = request.remote_addr
    
    log_audit(
        action='EXPORT_RESULTS_PDF',
        description=f"Admin user '{username}' exported PDF results for election: '{election.title}' (ID: {election_id}) from IP: {ip}"
    )
    
    return response


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