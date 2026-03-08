# student/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from student.models import Student, Vote, DeletionRequest
from admin.models import Candidate, Election, Course, Department, Announcement, YearLevel, Position, ElectionPosition
from extensions import db, bcrypt, mail
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func, or_
from flask_mail import Message
import hashlib, time, random
from datetime import datetime
import pytz
from student.utils import is_device_trusted
from student.models import TrustedDevice
from student.utils import generate_device_fingerprint
import json
from phe import paillier
import pickle
import os

# WebAuthn imports
from webauthn import (
    generate_registration_options,
    options_to_json,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response
)
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType,
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    AuthenticatorAttachment,
    AttestationConveyancePreference,
    AuthenticatorTransport,
    ResidentKeyRequirement
)

student_bp = Blueprint('student', __name__, template_folder='templates', static_folder='static')

# ==================== HELPER FUNCTIONS ====================
def generate_otp():
    return str(random.randint(100000, 999999))

def get_origin_and_rp_id():
    origin = request.headers.get("Origin")
    if origin is None:
        origin = request.url_root[:-1]
    rp_id = origin.split("://")[1].split(":")[0]
    return origin, rp_id

# Paillier encryption setup
def get_encryption_keys():
    """Get or generate Paillier encryption keys"""
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

def encrypt_vote_for_candidates(candidate_ids, selected_candidate_id):
    """Create one-hot encrypted vote vector for all candidates"""
    # Create one-hot vector: 1 for selected candidate, 0 for others
    vote_vector = [1 if candidate_id == selected_candidate_id else 0 
                  for candidate_id in candidate_ids]
    
    # Encrypt each element using Paillier
    enc_vote = [public_key.encrypt(x) for x in vote_vector]
    
    # Serialize for storage
    vote_json = json.dumps([
        {"ciphertext": str(e.ciphertext()), "exponent": e.exponent} 
        for e in enc_vote
    ])
    
    return vote_json

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

def count_votes_for_candidates(election_id, candidate_ids):
    """Count votes for candidates in an election using homomorphic addition"""
    votes = Vote.query.filter_by(election_id=election_id).all()
    
    if not votes:
        return {candidate_id: 0 for candidate_id in candidate_ids}
    
    # Initialize with encrypted zeros
    total_encrypted = [public_key.encrypt(0) for _ in candidate_ids]
    
    # Add all votes homomorphically
    for vote in votes:
        enc_votes = deserialize_encrypted_vote(vote.encrypted_vote)
        for i in range(len(total_encrypted)):
            total_encrypted[i] = total_encrypted[i] + enc_votes[i]
    
    # Decrypt final totals
    decrypted_totals = [private_key.decrypt(x) for x in total_encrypted]
    
    # Map to candidate IDs
    return dict(zip(candidate_ids, decrypted_totals))

# ============= ADD THE NEW HELPER FUNCTIONS HERE =============
def decrypt_ballot(encrypted_vote_json, private_key):
    """Decrypt a ballot that was encrypted with the new method"""
    try:
        vote_data = json.loads(encrypted_vote_json)
        
        if vote_data.get('method') == 'ballot_encrypt_v1':
            # Reconstruct encrypted number
            from phe import EncryptedNumber
            
            ciphertext = int(vote_data['ciphertext'])
            exponent = vote_data['exponent']
            
            # Create encrypted number and decrypt
            encrypted_ballot = EncryptedNumber(public_key, ciphertext, exponent)
            ballot_json = private_key.decrypt(encrypted_ballot)
            
            # Parse ballot data
            ballot_data = json.loads(ballot_json)
            
            return ballot_data
        else:
            # Handle old format if needed
            print("WARNING: Unknown encryption method")
            return None
    except Exception as e:
        print(f"ERROR: Failed to decrypt vote: {str(e)}")
        return None

def count_votes_for_election(election_id):
    """Count votes for an election using the new single-vector format"""
    votes = Vote.query.filter_by(election_id=election_id).all()
    
    # Get all candidates for this election
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    candidate_ids = [c.id for c in candidates]
    
    if not votes:
        return {candidate_id: 0 for candidate_id in candidate_ids}
    
    # Initialize with encrypted zeros
    total_encrypted = [public_key.encrypt(0) for _ in candidate_ids]
    
    # Add all votes homomorphically
    vote_count = 0
    for vote in votes:
        try:
            enc_votes = deserialize_encrypted_vote(vote.encrypted_vote)
            # Ensure we have the right length
            if len(enc_votes) == len(total_encrypted):
                for i in range(len(total_encrypted)):
                    total_encrypted[i] = total_encrypted[i] + enc_votes[i]
                vote_count += 1
            else:
                print(f"WARNING: Vote {vote.id} has wrong length: {len(enc_votes)} vs {len(total_encrypted)}")
        except Exception as e:
            print(f"ERROR: Failed to process vote {vote.id}: {str(e)}")
            continue
    
    print(f"DEBUG: Processed {vote_count} votes homomorphically")
    
    # Decrypt final totals
    decrypted_totals = [private_key.decrypt(x) for x in total_encrypted]
    
    # Map to candidate IDs
    result = dict(zip(candidate_ids, decrypted_totals))
    
    # Print results
    print("DEBUG: Vote counts:")
    for candidate_id, count in result.items():
        if count > 0:
            print(f"   Candidate {candidate_id}: {count} votes")
    
    return result


def send_email_change_notification(student, old_email, new_email):
    """Send notification to old email about email change"""
    try:
        msg = Message(
            'Your Email Has Been Changed',
            recipients=[old_email]
        )
        msg.body = f"""
        Your email address for your voting account has been changed.
        
        Old email: {old_email}
        New email: {new_email}
        
        If you did not make this change, please contact support immediately.
        """
        msg.html = f"""
        <div style="font-family: Arial, sans-serif;">
            <h2>Cebu Technological University Moalboal Campus</h2>
            <p>Hello <strong>{student.first_name}</strong>,</p>
            <p>Your email address for your voting account has been changed.</p>
            <p><strong>Old email:</strong> {old_email}<br>
            <strong>New email:</strong> {new_email}</p>
            <p>If you did not make this change, please contact support immediately.</p>
        </div>
        """
        
        mail.send(msg)
        print(f"Email change notification sent to {old_email}")
    except Exception as e:
        print(f"Failed to send email change notification: {e}")


def get_all_school_years():
    """Helper function to get all school years from elections"""
    elections = Election.query.all()
    school_years = []
    
    for election in elections:
        if election.start_date and election.candidates:  # Only include if has candidates
            year = election.start_date.year
            next_year = year + 1
            school_year_str = f"{year}-{next_year}"
            if school_year_str not in school_years:
                school_years.append(school_year_str)
    
    school_years.sort(reverse=True)
    return school_years


# ============= END OF NEW HELPER FUNCTIONS =============


from admin.models import CtuStudent  # the table where admin imported students
from sqlalchemy import func  # needed for case-insensitive comparison

# ==================== REGISTER ====================
@student_bp.route('/register', methods=['GET', 'POST'])
def register():
    from admin.models import Department, Course, CtuStudent  # added CtuStudent
    from sqlalchemy import func  # needed for case-insensitive comparison

    # ✅ Clear form session only if not coming from failed POST
    if request.method == 'GET':
        if not session.pop('keep_form', False):
            session.pop('registration_data', None)
            session.pop('error_fields', None)

    if request.method == 'POST':
        session['registration_data'] = request.form.to_dict()
        session['error_fields'] = []
        session['keep_form'] = True   # ⭐ Keep form values if errors

        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        id_number = request.form.get('id_number', '').strip()
        username = request.form.get('username', '').strip()

        # ---------------- DUPLICATE CHECKS ----------------
        if Student.query.filter(func.trim(Student.id_number) == id_number).first():
            flash("ID Number already registered!", "danger")
            session['error_fields'].append('id_number')

        if Student.query.filter_by(email=email).first():
            flash("Email already registered!", "danger")
            session['error_fields'].append('email')

        if Student.query.filter_by(username=username).first():
            flash("Username already taken!", "danger")
            session['error_fields'].append('username')

        # ---------------- YEAR LEVEL VALIDATION ----------------
        year_level = request.form.get('year_level')
        if not year_level or int(year_level) not in [1, 2, 3, 4]:
            flash("Please select a valid year level.", "danger")
            session['error_fields'].append('year_level')
        else:
            session['registration_data']['year_level'] = int(year_level)
            session['registration_data']['year_level_id'] = int(year_level)

        # ---------------- COURSE VALIDATION ----------------
        course_id = request.form.get('course')
        course_obj = Course.query.get(course_id)
        if not course_obj:
            flash("Selected course is invalid.", "danger")
            session['error_fields'].append('course')
        else:
            session['registration_data'].update({
                "course": course_obj.course_name,
                "course_id": course_obj.id,
                "department_id": course_obj.department_id
            })

        # ---------------- CTU DATABASE VERIFICATION ----------------
        ctu_match = CtuStudent.query.filter(
            func.lower(CtuStudent.first_name) == first_name.lower(),
            func.lower(CtuStudent.last_name) == last_name.lower(),
            func.lower(CtuStudent.student_number) == id_number.lower(),
            CtuStudent.is_active == True
        ).first()

        if not ctu_match:
            flash("You are not registered in the CTU database. Please contact the admin.", "danger")
            session['error_fields'].append('ctu_verification')

        # ---------------- HANDLE ERRORS ----------------
        if session['error_fields']:
            return redirect(url_for('student.register'))

        # ---------------- OTP GENERATION ----------------
        registration_data = session['registration_data']
        otp = generate_otp()
        session['otp'] = otp

        try:
            # Send OTP email
            msg = Message(
                subject="CTU Registration OTP",
                recipients=[email]
            )
            msg.html = f"""
            <div style="font-family: Arial; text-align:center;">
                <h2>CTU Moalboal Campus</h2>
                <p>Hello <strong>{registration_data['first_name']}</strong></p>
                <h3>Your OTP: {otp}</h3>
            </div>
            """
            mail.send(msg)

            # ✅ Keep session for OTP verification
            flash("OTP has been sent to your email.", "info")
            return redirect(url_for('student.verify_otp'))

        except Exception as e:
            flash(f"Failed to send OTP email: {str(e)}", "danger")

    # ---------------- LOAD COURSES ----------------
    departments = Department.query.order_by(Department.name).all()
    courses_by_department = {
        dept.name: Course.query.filter_by(department_id=dept.id).all()
        for dept in departments
    }

    return render_template(
        'student_register.html',
        courses_by_department=courses_by_department
    )


# ==================== AJAX VALIDATION ====================
@student_bp.route('/register/validate', methods=['POST'])
def ajax_validate_register():
    errors = {}

    email = request.form.get('email', '').strip()
    id_number = request.form.get('id_number')
    username = request.form.get('username')

    if Student.query.filter(func.trim(Student.id_number) == id_number).first():
        errors['id_number'] = 'ID Number already registered'

    if Student.query.filter_by(email=email).first():
        errors['email'] = 'Email already registered'

    if Student.query.filter_by(username=username).first():
        errors['username'] = 'Username already taken'

    return jsonify(errors)


# ==================== OTP VERIFICATION ====================
@student_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        if entered_otp == session.get('otp'):
            data = session.get('registration_data')
            password_hash = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')

            new_student = Student(
                first_name=data.get('first_name'),
                middle_name=data.get('middle_name'),
                last_name=data.get('last_name'),
                suffix=data.get('suffix'),
                username=data.get('username'),
                email=data.get('email'),
                password=password_hash,
                course=data.get('course'),
                course_id=data.get('course_id'),
                department_id=data.get('department_id'),
                year_level_id=data.get('year_level_id'),  # added year_level saving
                birth_date=data.get('birth_date'),
                id_number=data.get('id_number')
            )

            db.session.add(new_student)
            db.session.commit()

            # ✅ Clear session only after registration is successful
            session.pop('otp', None)
            session.pop('registration_data', None)
            session.pop('error_fields', None)
            session.pop('keep_form', None)

            flash('Registration successful! You may now log in.', 'success')
            return redirect(url_for('student.login'))
        else:
            flash('Invalid OTP.', 'danger')

    return render_template('verify_otp.html')


# ==================== RESEND OTP ====================
@student_bp.route('/resend-otp', methods=['GET'])
def resend_otp():
    registration_data = session.get('registration_data')
    if not registration_data:
        flash("No registration data found. Please register first.", "danger")
        return redirect(url_for('student.register'))

    # Generate new OTP
    otp = generate_otp()
    session['otp'] = otp

    try:
        msg = Message(
            subject="CTU Registration OTP",
            recipients=[registration_data['email']]
        )
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; text-align: center;">
            <h2>Cebu Technological University Moalboal Campus</h2>
            <p>Hello <strong>{registration_data['first_name']}</strong>,</p>
            <p>Your <strong>OTP code</strong> is:</p>
            <h3>{otp}</h3>
        </div>
        """
        mail.send(msg)
        flash("A new OTP has been sent to your email.", "info")
    except Exception as e:
        flash(f"Failed to send OTP email. Error: {str(e)}", "danger")

    return redirect(url_for('student.verify_otp'))



# ==================== LOGIN (merged traditional + WebAuthn page) ====================
@student_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        id_number = request.form.get('id_number', '').strip()
        password = request.form.get('password', '').strip()
        device_fp = request.form.get('device_fingerprint')
        print("DEVICE FINGERPRINT:", device_fp)

        student = Student.query.filter(
            func.lower(Student.email) == email,
            func.trim(Student.id_number) == id_number
        ).first()

        if not student:
            flash("Mismatched Credentials", "danger")
            return render_template('student_login.html')

        if bcrypt.check_password_hash(student.password, password):

            # 🔐 ================= DEVICE TRUST CHECK =================

            # Check if THIS EXACT device is trusted
            trusted_device = TrustedDevice.query.filter_by(
                student_id=student.id,
                device_fingerprint=device_fp,
                trusted=True
            ).first()

            # Check if ANY trusted device exists
            any_trusted_device = TrustedDevice.query.filter_by(
                student_id=student.id,
                trusted=True
            ).first()

            if not trusted_device:
                # New / untrusted device
                if any_trusted_device:
                    # There are already trusted devices → trigger email verification
                    from student.utils import send_new_device_email

                    # 1️⃣ Save new device in DB as untrusted
                    new_device = TrustedDevice(
                        student_id=student.id,
                        device_fingerprint=device_fp,
                        ip_address=request.remote_addr,
                        browser=request.headers.get('User-Agent'),
                        device_name=request.headers.get('User-Agent')[:100],
                        trusted=False
                    )
                    db.session.add(new_device)
                    db.session.commit()

                    # 2️⃣ Send verification email
                    send_new_device_email(student, new_device)

                    # 3️⃣ Store info in session for resend / verify page
                    session['pending_login_student'] = student.id
                    session['pending_device_fp'] = device_fp

                    # ❌ Removed this flash
                    # flash(
                    #     "New device detected. A verification email has been sent. Please check your inbox.",
                    #     "warning"
                    # )

                    return redirect(url_for('student.verify_device'))
                else:
                    # FIRST login, no trusted devices yet → normal login
                    login_user(student)
                    flash('Login successful!', 'success')  # This will show as floating notification
                    return redirect(url_for('student.dashboard', trust_prompt=True))

            # 🔐 =======================================================

            # ✅ Trusted device → proceed with normal login
            login_user(student)
            flash('Login successful!', 'success')  # This will show as floating notification
            return redirect(url_for('student.dashboard'))

        else:
            flash('Incorrect password', 'danger')
            return render_template('student_login.html')

    return render_template('student_login.html')

    


@student_bp.route('/trust-device', methods=['POST'])
@login_required
def toggle_trust_device():
    fingerprint = generate_device_fingerprint()

    device = TrustedDevice.query.filter_by(
        student_id=current_user.id,
        device_fingerprint=fingerprint
    ).first()

    if device:
        # Untrust this device
        db.session.delete(device)
        flash("This device is no longer trusted.", "info")
    else:
        # Trust this device
        device = TrustedDevice(
            student_id=current_user.id,
            device_fingerprint=fingerprint,
            ip_address=request.remote_addr,
            browser=request.headers.get('User-Agent'),
            device_name=request.headers.get('User-Agent')[:100],
            trusted=True,
            last_login=datetime.utcnow()
        )
        db.session.add(device)
        flash("This device is now trusted.", "success")

    db.session.commit()
    return redirect(url_for('student.profile'))



@student_bp.route('/verify-device', methods=['GET'])
def verify_device():
    student_id = session.get('pending_login_student')
    fingerprint = session.get('pending_device_fp')

    if not student_id or not fingerprint:
        flash("No pending device verification.", "danger")
        return redirect(url_for('student.login'))

    student = Student.query.get(student_id)

    device = TrustedDevice.query.filter_by(
        student_id=student.id,
        device_fingerprint=fingerprint
    ).first()

    if not device:
        device = TrustedDevice(
            student_id=student.id,
            device_fingerprint=fingerprint,
            ip_address=request.remote_addr,
            browser=request.headers.get('User-Agent'),
            device_name=request.headers.get('User-Agent')[:100],
            trusted=False
        )
        db.session.add(device)
        db.session.commit()

    # ✅ NO EMAIL HERE
    return render_template('verify_device.html', student=student)



@student_bp.route('/verify-device/resend', methods=['POST'])
def resend_verify_device():
    student_id = session.get('pending_login_student')
    fingerprint = session.get('pending_device_fp')

    if not student_id or not fingerprint:
        flash("No pending verification to resend.", "danger")
        return redirect(url_for('student.login'))

    student = Student.query.get(student_id)

    device = TrustedDevice.query.filter_by(
        student_id=student.id,
        device_fingerprint=fingerprint,
        trusted=False
    ).first()

    if not device:
        flash("Device already verified or missing.", "info")
        return redirect(url_for('student.login'))

    from student.utils import send_new_device_email
    send_new_device_email(student, device)

    flash("Verification email resent. Please check your inbox.", "success")
    return redirect(url_for('student.verify_device'))



from datetime import datetime, timedelta
from flask import jsonify

@student_bp.route('/verify-device/<token>', methods=['GET'])
def verify_device_email(token):
    device = TrustedDevice.query.filter_by(verification_token=token).first()
    if not device:
        flash("Invalid or expired verification link.", "danger")
        return redirect(url_for('student.login'))

    # Check if token expired (5 minutes)
    if device.verification_sent_at and datetime.utcnow() > device.verification_sent_at + timedelta(minutes=5):
        db.session.delete(device)  # remove unverified device
        db.session.commit()
        flash("Verification link expired.", "danger")
        return redirect(url_for('student.login'))

    # ✅ Mark device as trusted
    device.trusted = True
    device.verification_token = None
    db.session.commit()

    student = device.student

    # Render the verify_device.html page again with a success message
    return render_template(
        'verify_device.html',
        student=student,
        message="Device verified successfully! Redirecting to dashboard...",
        redirect_after=3  # seconds
    )



@student_bp.route('/verify-device/confirm/<token>')
def confirm_device(token):
    from datetime import datetime, timedelta

    device = TrustedDevice.query.filter_by(verification_token=token).first()

    if not device:
        return "Invalid or expired link", 400

    # Check expiry (5 minutes)
    if device.verification_sent_at and datetime.utcnow() > device.verification_sent_at + timedelta(minutes=5):
        db.session.delete(device)
        db.session.commit()
        return "Link expired"

    # Mark device as trusted
    device.trusted = True
    device.verification_token = None
    device.verification_sent_at = None
    db.session.commit()

    # Return a styled confirmation page
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Device Verified</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f4f6fb;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .card {
            background: #ffffff;
            padding: 30px 25px;
            border-radius: 16px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.12);
            text-align: center;
            max-width: 400px;
        }
        .icon {
            font-size: 50px;
            color: #16a34a;
            margin-bottom: 15px;
        }
        h2 {
            margin: 0 0 12px 0;
            color: #111827;
            font-size: 1.5rem;
        }
        p {
            color: #4b5563;
            font-size: 1rem;
            line-height: 1.5;
        }
        a {
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background: #2563eb;
            color: white;
            text-decoration: none;
            border-radius: 10px;
            font-weight: 600;
            transition: background 0.2s ease;
        }
        a:hover {
            background: #1d4ed8;
        }
    </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">✅</div>
            <h2>Device Verified!</h2>
            <p>Your device has been successfully confirmed.<br>
            You can now return to your browser to complete login.</p>
            <a href="#" onclick="window.close()">Close Window</a>
        </div>
    </body>
    </html>
    """



@student_bp.route('/verify-device/status')
def verify_device_status():
    from flask_login import login_user
    student_id = session.get('pending_login_student')
    fingerprint = session.get('pending_device_fp')

    if not student_id or not fingerprint:
        return jsonify({"status": "no_session"})

    # Check trusted
    device = TrustedDevice.query.filter_by(
        student_id=student_id,
        device_fingerprint=fingerprint,
        trusted=True
    ).first()
    if device:
        student = device.student
        login_user(student)
        return jsonify({"status": "verified"})

    # Check if device record exists at all
    device_any = TrustedDevice.query.filter_by(
        student_id=student_id,
        device_fingerprint=fingerprint
    ).first()
    if device_any is None:
        return jsonify({"status": "rejected"})  # deleted = rejected

    return jsonify({"status": "pending"})






@student_bp.route('/verify-device/reject/<token>')
def reject_device(token):
    from datetime import datetime
    device = TrustedDevice.query.filter_by(verification_token=token).first()
    if device:
        db.session.delete(device)
        db.session.commit()

    # Return a small notification page (optional)
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Device Rejected</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: #f4f6fb;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
            .card {
                background: #ffffff;
                padding: 30px 25px;
                border-radius: 16px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.12);
                text-align: center;
                max-width: 400px;
            }
            .icon {
                font-size: 50px;
                color: #e53935; /* red */
                margin-bottom: 15px;
            }
            h2 {
                margin: 0 0 12px 0;
                color: #111827;
                font-size: 1.5rem;
            }
            p {
                color: #4b5563;
                font-size: 1rem;
                line-height: 1.5;
            }
            a {
                display: inline-block;
                margin-top: 20px;
                padding: 10px 20px;
                background: #2563eb;
                color: white;
                text-decoration: none;
                border-radius: 10px;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">❌</div>
            <h2>Device Rejected</h2>
            <p>No device info was saved. Please return to your browser.</p>
            <a href="#" onclick="window.close()">Close Window</a>
        </div>
    </body>
    </html>
    """



# ------------------- FORGOT PASSWORD -------------------
import secrets
@student_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = (data.get('email') or "").strip().lower()
    id_number = (data.get('id_number') or "").strip()

    student = Student.query.filter_by(email=email, id_number=id_number).first()
    if not student:
        return jsonify({"message": "No student found with this Gmail and Student ID"}), 404

    # Generate reset token
    token = secrets.token_urlsafe(32)
    student.reset_token = token
    db.session.commit()

    # Create reset link
    reset_url = url_for('student.reset_password', token=token, _external=True)

    # Send email using Flask-Mail
    subject = "Reset Your Student Account Password"
    body = f"""
    Hello {student.first_name},

    You requested to reset your password. Click the link below to reset it:

    {reset_url}

    If you did not request a password reset, you can ignore this email.
    """

    try:
        msg = Message(subject=subject, recipients=[student.email], body=body)
        mail.send(msg)
        return jsonify({"message": "Reset link sent to your Gmail."}), 200
    except Exception as e:
        print("Failed to send email:", e)
        return jsonify({"message": "Failed to send email. Try again later."}), 500

@student_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    student = Student.query.filter_by(reset_token=token).first()
    if not student:
        flash("Invalid or expired token", "danger")
        return redirect(url_for('student.login'))

    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        if not new_password:
            flash("Password cannot be empty", "danger")
            return render_template('student_reset_password.html', token=token)

        student.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        student.reset_token = None
        db.session.commit()
        flash("Password successfully reset! You can now login.", "success")
        return redirect(url_for('student.login'))

    return render_template('student_reset_password.html', token=token)




# ==================== DASHBOARD ====================
from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from collections import defaultdict
from datetime import datetime
import pytz
from sqlalchemy import func

from student.utils import generate_device_fingerprint

@student_bp.route('/dashboard')
@login_required
def dashboard():
    # ---------------- School Year Filter ----------------
    # FIRST: Check URL parameter (when user clicks from hamburger menu)
    school_year = request.args.get('school_year')
    
    # SECOND: If no URL parameter, try to get from session
    if not school_year:
        school_year = session.get('current_school_year')
    
    # Get all elections to extract school years
    elections = Election.query.all()
    
    # Extract unique school years
    school_years = []
    for election in elections:
        if election.start_date:
            year = election.start_date.year
            # Only include if there are candidates for this election
            if election.candidates:
                next_year = year + 1
                school_year_str = f"{year}-{next_year}"
                if school_year_str not in school_years:
                    school_years.append(school_year_str)
    
    # Sort school years (latest first)
    school_years.sort(reverse=True)
    
    # If no school year selected, use the latest
    if not school_year and school_years:
        school_year = school_years[0]
    
    # Save to session for other pages
    if school_year:
        session['current_school_year'] = school_year
    
    # ---------------- Filter data by school year ----------------
    from datetime import datetime
    
    # Parse school year to date range
    start_date = None
    end_date = None
    if school_year and school_years:
        try:
            start_year = int(school_year.split('-')[0])
            end_year = int(school_year.split('-')[1])
            
            # Create datetime range
            start_date = datetime(start_year, 1, 1)
            end_date = datetime(end_year, 12, 31)
        except (ValueError, IndexError):
            start_date = None
            end_date = None
    
    # ---------------- Existing logic with filters ----------------
    total_students = Student.query.count()
    
    # Filter votes by school year if selected
    if start_date and end_date:
        # Get votes from elections within the school year
        votes_query = Vote.query.join(Election).filter(
            Election.start_date >= start_date,
            Election.start_date <= end_date
        )
        total_votes = votes_query.count()
        
        # Check if current user has voted in any election within this school year
        has_voted = votes_query.filter(Vote.student_id == current_user.id).first() is not None
        
        # Filter elections for leading candidates
        elections = Election.query.filter(
            Election.start_date >= start_date,
            Election.start_date <= end_date
        ).all()
    else:
        total_votes = Vote.query.count()
        has_voted = Vote.query.filter_by(student_id=current_user.id).first() is not None
        elections = Election.query.all()

    # ---------------- FIXED: Filter announcements by school year ----------------
    announcements_query = Announcement.query.filter(
        (Announcement.department_id == current_user.department_id) | 
        (Announcement.department_id == None)
    )
    
    # Apply school year filter to announcements
    if start_date and end_date:
        announcements_query = announcements_query.filter(
            Announcement.date >= start_date,
            Announcement.date <= end_date
        )
    
    announcements = announcements_query.order_by(Announcement.date.desc()).all()

    # ---------------- Updated leading_candidates logic with school year filter ----------------
    leading_candidates = []
    
    if elections:
        # Use the most recent election from filtered elections
        if elections:
            # Sort elections by start_date to get the most recent
            elections.sort(key=lambda x: x.start_date, reverse=True)
            recent_election = elections[0]
            
            # Get all candidates for this election
            candidates = Candidate.query.filter_by(election_id=recent_election.id).all()
            candidate_ids = [c.id for c in candidates]
            
            # Count votes using homomorphic encryption
            vote_counts = count_votes_for_candidates(recent_election.id, candidate_ids)
            
            # Create list of (candidate, vote_count)
            candidate_votes = []
            for candidate in candidates:
                vote_count = vote_counts.get(candidate.id, 0)
                candidate_votes.append((candidate, vote_count))
            
            # Sort by vote count and get top 5
            candidate_votes.sort(key=lambda x: x[1], reverse=True)
            leading_candidates = candidate_votes[:5]

    # ---------------- Trust-device prompt ----------------
    fingerprint = generate_device_fingerprint()
    device = TrustedDevice.query.filter_by(
        student_id=current_user.id,
        device_fingerprint=fingerprint
    ).first()

    trust_prompt = False
    if device is None:
        trust_prompt = True

    # ---------------- Active election (filtered by school year) ----------------
    local_tz = pytz.timezone("Asia/Manila")
    now = datetime.now(local_tz).replace(tzinfo=None)
    
    if start_date and end_date:
        active_election = Election.query.filter(
            Election.start_date <= now,
            Election.end_date >= now,
            Election.start_date >= start_date,
            Election.start_date <= end_date
        ).first()
    else:
        active_election = Election.query.filter(
            Election.start_date <= now,
            Election.end_date >= now
        ).first()

    # ---------------- Calculate days remaining for active election ----------------
    days_remaining = 0
    if active_election:
        days_remaining = (active_election.end_date - now).days
        if days_remaining < 0:
            days_remaining = 0

    # ---------------- Total voters ----------------
    total_voters = total_students

    # ---------------- Render template ----------------
    return render_template(
        'student_dashboard.html',
        total_students=total_students,
        total_votes=total_votes,
        has_voted=has_voted,
        announcements=announcements,
        leading_candidates=leading_candidates,
        trust_prompt=trust_prompt,
        current_time=now,
        days_remaining=days_remaining,
        total_voters=total_voters,
        active_election=active_election,
        school_years=school_years,  # Pass to template for header
        current_sy=school_year  # Pass current selection
    )

@student_bp.route('/trust-current-device', methods=['POST'])
@login_required
def trust_current_device():
    # Generate fingerprint for this device
    fingerprint = generate_device_fingerprint()

    # Check if the device already exists (safety check)
    existing_device = TrustedDevice.query.filter_by(
        student_id=current_user.id,
        device_fingerprint=fingerprint
    ).first()

    if existing_device:
        flash("This device is already trusted.", "info")
    else:
        # Create new trusted device record
        new_device = TrustedDevice(
            student_id=current_user.id,
            device_fingerprint=fingerprint,
            ip_address=request.headers.get('X-Forwarded-For', request.remote_addr),
            browser=request.headers.get('User-Agent'),
            device_name="Unknown",  # Optional: you can capture actual device name later
            trusted=True,
            last_login=datetime.utcnow()
        )
        db.session.add(new_device)
        db.session.commit()
        flash("This device is now trusted!", "success")

    return redirect(url_for('student.dashboard'))



@student_bp.route('/announcements')
@login_required
def student_announcements():
    # FIRST: Check URL parameter (when user clicks from hamburger menu)
    school_year = request.args.get('school_year')
    
    # SECOND: If no URL parameter, try to get from session
    if not school_year:
        school_year = session.get('current_school_year')
    
    # Save to session for other pages
    if school_year:
        session['current_school_year'] = school_year
    
    # Parse school year to date range (if you want to filter announcements by date)
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
    
    # Base query for announcements
    query = Announcement.query.filter(
        (Announcement.department_id == current_user.department_id) | 
        (Announcement.department_id == None)
    )
    
    # OPTIONAL: Filter announcements by school year (if announcements have dates)
    # Uncomment this if you want announcements to be filtered by school year too
    if start_date and end_date:
        query = query.filter(
            Announcement.date >= start_date,
            Announcement.date <= end_date
        )
    
    announcements = query.order_by(Announcement.date.desc()).all()

    return render_template(
        'student_announcements.html',
        announcements=announcements,
        school_years=get_all_school_years(),
        current_sy=school_year
    )

# ------------------- HELP -------------------
@student_bp.route('/help')
@login_required
def help_page():
    faqs = [
        {"q": "How do I vote?", "a": "Go to Available Elections, select candidates, and submit."},
        {"q": "Can I change my vote?", "a": "No — once submitted, votes are final."},
        {"q": "Who to contact for issues?", "a": "Election Committee: comelec@example.edu"}
    ]
    return render_template('help_page.html', faqs=faqs)


# ------------------- VOTING -------------------
from flask import flash, redirect, url_for, render_template, request
from flask_login import login_required, current_user
from datetime import datetime
import pytz
from student.models import Vote
from admin.models import Election, Candidate
from collections import defaultdict

@student_bp.route('/vote/<int:election_id>', methods=['GET'])
@login_required
def vote_page(election_id):
    local_tz = pytz.timezone("Asia/Manila")
    now = datetime.now(local_tz).replace(tzinfo=None)

    election = Election.query.filter_by(id=election_id).first()
    if not election:
        flash("Election not found.", "danger")
        return redirect(url_for('student.available_elections'))

    if not (election.start_date <= now <= election.end_date):
        flash("This election is not currently open.", "warning")
        return redirect(url_for('student.available_elections'))

    existing_vote = Vote.query.filter_by(student_id=current_user.id, election_id=election.id).first()
    if existing_vote:
        flash("You have already voted in this election.", "info")
        return redirect(url_for('student.available_elections'))

    # Fetch position limits for this election
    election_positions = ElectionPosition.query.filter_by(election_id=election_id).all()
    position_limits = {ep.position_id: ep.max_votes for ep in election_positions}
    
    # Fetch candidates and group by position with limits
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    candidates_by_position = {}
    all_candidate_ids = []
    
    for c in candidates:
        if c.position:
            position_name = c.position.name
            if position_name not in candidates_by_position:
                candidates_by_position[position_name] = {
                    'candidates': [],
                    'position_id': c.position_id,
                    'max_votes': position_limits.get(c.position_id, 1)  # Default to 1 if not set
                }
            candidates_by_position[position_name]['candidates'].append(c)
        all_candidate_ids.append(c.id)
    
    # ✅ SORT BY POSITION ID (lowest ID first = President, VP, etc.)
    sorted_positions = sorted(
        candidates_by_position.items(),
        key=lambda item: item[1]['position_id']  # Sort by position_id
    )
    
    # Convert back to dictionary (Python 3.7+ preserves insertion order)
    candidates_by_position = dict(sorted_positions)

    return render_template(
        'vote_page.html',
        election=election,
        candidates_by_position=candidates_by_position,
        all_candidate_ids=all_candidate_ids
    )

@student_bp.route('/vote/<int:election_id>/submit', methods=['POST'])
@login_required
def submit_vote(election_id):
    import time
    import pytz
    import json
    import hashlib
    import secrets
    from datetime import datetime
    
    start_time = time.time()
    
    # Set timezone
    local_tz = pytz.timezone("Asia/Manila")
    
    # Record the moment when "Cast Vote" was clicked (client-side)
    cast_timestamp_str = request.form.get('cast_timestamp')
    cast_timestamp = None
    
    if cast_timestamp_str:
        try:
            cast_timestamp = datetime.fromisoformat(cast_timestamp_str)
            print(f"DEBUG: Received Manila time: {cast_timestamp}")
        except Exception as e:
            print(f"DEBUG: Error parsing timestamp: {e}")
            cast_timestamp = datetime.utcnow()
    else:
        cast_timestamp = datetime.utcnow()
    
    # GET ALL CANDIDATE IDs FROM HIDDEN INPUT FIRST!
    all_candidate_ids_str = request.form.get('all_candidate_ids', '')
    if not all_candidate_ids_str:
        flash("Voting data error. Please try again.", "danger")
        return redirect(url_for('student.vote_page', election_id=election_id))
    
    # Convert string to list of integers
    all_candidate_ids = [int(id_str) for id_str in all_candidate_ids_str.split(',') if id_str.strip()]
    
    # Get selected candidates - Use getlist() for checkboxes
    selected_candidates = {}
    
    # First, get all form keys that start with 'position_'
    for key in request.form.keys():
        if key.startswith('position_'):
            position_id = key.replace('position_', '')
            
            # Use getlist() to get ALL values for this key (for checkboxes)
            values = request.form.getlist(key)
            
            # Convert each value to integer
            candidate_ids = []
            for val in values:
                try:
                    candidate_ids.append(int(val))
                except ValueError:
                    continue
            
            if candidate_ids:
                selected_candidates[position_id] = candidate_ids

    if not selected_candidates:
        flash("Please select at least one candidate before submitting.", "warning")
        return redirect(url_for('student.vote_page', election_id=election_id))

    # Prevent duplicate voting
    existing_vote = Vote.query.filter_by(
        student_id=current_user.id, 
        election_id=election_id
    ).first()
    
    if existing_vote:
        flash("You have already voted in this election.", "info")
        return redirect(url_for('student.available_elections'))

    # Record timestamp
    recorded_timestamp = datetime.utcnow()
    
    # ===== GENERATE SECRET NONCE FOR VERIFICATION =====
    secret_nonce = secrets.token_hex(8)
    print(f"🔐 DEBUG: Generated secret nonce for voter: {secret_nonce}")
    
    # ===== CREATE FINDER HASHES FOR EACH SELECTED CANDIDATE =====
    finder_hashes = []
    finder_hash_strings = []  # Keep separate list for easy searching
    
    # Create a mapping of candidate_id to its index in all_candidate_ids
    candidate_index_map = {candidate_id: idx for idx, candidate_id in enumerate(all_candidate_ids)}
    
    # For each selected candidate, create a finder_hash
    for position_id, candidate_ids in selected_candidates.items():
        for candidate_id in candidate_ids:
            # Create hash: SHA256(candidate_id + secret_nonce)
            hash_string = f"{candidate_id}{secret_nonce}"
            finder_hash = hashlib.sha256(hash_string.encode()).hexdigest()
            finder_hashes.append({
                'candidate_id': candidate_id,
                'hash': finder_hash
            })
            finder_hash_strings.append(finder_hash)  # Store just the hash string
            print(f"🔑 DEBUG: Created finder_hash for candidate {candidate_id}: {finder_hash[:16]}...")
    
    # ===== OPTIMIZED: SINGLE VOTE VECTOR FOR ALL POSITIONS =====
    encrypt_start = time.time()
    
    # Create a single vote vector for ALL candidates
    vote_vector = [0] * len(all_candidate_ids)
    
    # Mark selected candidates with 1
    selected_count = 0
    for position_id, candidate_ids in selected_candidates.items():
        for candidate_id in candidate_ids:
            if candidate_id in candidate_index_map:
                idx = candidate_index_map[candidate_id]
                vote_vector[idx] = 1
                selected_count += 1
    
    print(f"DEBUG: Created vote vector with {selected_count} selected candidates out of {len(all_candidate_ids)} total")
    
    # Encrypt the SINGLE vector
    enc_vote = [public_key.encrypt(x) for x in vote_vector]
    
    # Serialize for storage
    encrypted_vote_json = json.dumps([
        {"ciphertext": str(e.ciphertext()), "exponent": e.exponent} 
        for e in enc_vote
    ])
    
    encrypt_time = time.time() - encrypt_start
    print(f"🔥 DEBUG: Encrypted {len(vote_vector)} candidates in {encrypt_time:.2f} seconds")
    
    # Validate it's proper JSON
    try:
        json.loads(encrypted_vote_json)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in encrypted vote: {e}")
        flash("Voting encryption error. Please try again.", "danger")
        return redirect(url_for('student.vote_page', election_id=election_id))
    
    # ===== FIXED: STORE FINDER HASHES PROPERLY =====
    # Store as JSON in a TEXT field
    finder_data = {
        'nonce': secret_nonce,
        'hashes': finder_hashes,
        'hash_strings': finder_hash_strings
    }
    finder_json = json.dumps(finder_data)
    
    # Create vote object with ALL finder data
    vote = Vote(
        student_id=current_user.id, 
        election_id=election_id,
        encrypted_vote=encrypted_vote_json,
        finder_hash=finder_json,  # Store ALL data as JSON
        cast_timestamp=cast_timestamp,
        recorded_timestamp=recorded_timestamp
    )
    
    # Add single vote
    db.session.add(vote)
    print(f"DEBUG: Added 1 vote record with {len(finder_hashes)} finder hashes")

    try:
        db.session.commit()
        total_time = time.time() - start_time
        print(f"🎉 DEBUG: Vote successfully committed in {total_time:.2f} seconds")
        
        # Store the secret nonce in session
        session['last_vote_secret'] = secret_nonce
        session['last_vote_election'] = election_id
        
        flash(f"Your vote has been submitted and encrypted successfully! Your secret verification code is: {secret_nonce}", "success")
        
        return redirect(url_for('student.receipt', election_id=election_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Database commit failed: {str(e)}")
        flash(f"Error saving your vote: {str(e)}", "danger")
        return redirect(url_for('student.vote_page', election_id=election_id))

@student_bp.route('/receipt')
@login_required
def receipt():
    """Show all voting receipts for the student"""
    
    # FIRST: Check URL parameter (when user clicks from hamburger menu)
    school_year = request.args.get('school_year')
    
    # SECOND: If no URL parameter, try to get from session
    if not school_year:
        school_year = session.get('current_school_year')
    
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
    
    # Save to session for other pages
    if school_year:
        session['current_school_year'] = school_year
    
    # Get all votes for this student
    votes_query = Vote.query.filter_by(student_id=current_user.id)
    
    # Filter votes by school year if selected
    if start_date and end_date:
        # Join with Election to filter by election date
        votes_query = votes_query.join(Election).filter(
            Election.start_date >= start_date,
            Election.start_date <= end_date
        )
    
    # Order by most recent first
    votes = votes_query.order_by(Vote.created_at.desc()).all()
    
    if not votes:
        return render_template('receipt.html', 
                             votes=[],
                             school_years=get_all_school_years(),
                             current_sy=school_year)
    
    # Prepare data for each vote
    votes_data = []
    for vote in votes:
        # Extract the secret nonce from the finder_hash
        secret_nonce = 'N/A'
        candidate_details = []
        
        if vote.finder_hash:
            try:
                # Try to parse as JSON first
                finder_data = json.loads(vote.finder_hash)
                print(f"DEBUG - Finder data for vote {vote.id}: {finder_data}")  # Debug print
                
                # Check if it's the new format with 'nonce' field
                if isinstance(finder_data, dict):
                    # Extract the nonce
                    if 'nonce' in finder_data:
                        secret_nonce = finder_data['nonce']
                        print(f"DEBUG - Found nonce: {secret_nonce}")  # Debug print
                    
                    # Get candidate hashes and details
                    if 'hashes' in finder_data:
                        for hash_item in finder_data['hashes']:
                            candidate_id = hash_item.get('candidate_id')
                            if candidate_id:
                                candidate = Candidate.query.get(candidate_id)
                                if candidate:
                                    position_name = candidate.position.name if candidate.position else "Unknown Position"
                                    # Store full hash for verification, but display truncated
                                    full_hash = hash_item.get('hash', '')
                                    truncated_hash = full_hash[:16] + '...' if full_hash else 'N/A'
                                    
                                    candidate_details.append({
                                        'id': candidate_id,
                                        'name': f"{candidate.first_name} {candidate.last_name}",
                                        'position': position_name,
                                        'hash': truncated_hash,
                                        'full_hash': full_hash  # Store full hash for PDF/download
                                    })
                else:
                    # If it's not a dict, use as is
                    secret_nonce = str(finder_data)
                    
            except json.JSONDecodeError as e:
                print(f"DEBUG - JSON decode error for vote {vote.id}: {e}")
                # If it's not JSON, use the raw string
                secret_nonce = vote.finder_hash
        else:
            print(f"DEBUG - No finder_hash for vote {vote.id}")
        
        # Get election details
        election = Election.query.get(vote.election_id)
        
        # Create the vote item data
        vote_item = {
            'vote': vote,
            'election': election,
            'secret_nonce': secret_nonce,
            'candidate_details': candidate_details
        }
        
        votes_data.append(vote_item)
        print(f"DEBUG - Vote {vote.id} processed: nonce={secret_nonce}, candidates={len(candidate_details)}")  # Debug print
    
    print(f"DEBUG - Total votes processed: {len(votes_data)}")  # Debug print
    
    return render_template('receipt.html',
                         votes=votes_data,
                         now=datetime.now(pytz.timezone("Asia/Manila")),
                         school_years=get_all_school_years(),
                         current_sy=school_year)

from sqlalchemy import or_

from flask import flash, redirect, url_for
from sqlalchemy import or_

# student/routes.py - UPDATE your available_elections route

@student_bp.route('/available_elections')
@login_required
def available_elections():
    # FIRST: Check URL parameter (when user clicks from hamburger menu)
    school_year = request.args.get('school_year')
    
    # SECOND: If no URL parameter, try to get from session
    if not school_year:
        school_year = session.get('current_school_year')
    
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
    
    # Save to session for other pages
    if school_year:
        session['current_school_year'] = school_year
    
    # Philippines timezone
    local_tz = pytz.timezone("Asia/Manila")
    utc_tz = pytz.UTC
    now_ph = datetime.now(local_tz)
    
    # Convert to timezone-naive for database comparison
    now_naive = now_ph.replace(tzinfo=None)

    student_department_id = current_user.department_id
    
    # Get student year level
    student_year = None
    if current_user.year_level:
        # Extract the numeric part from year_name (e.g., "1st Year" -> "1")
        year_name = current_user.year_level.year_name
        # Extract first number from the string
        import re
        match = re.search(r'\d+', year_name)
        if match:
            student_year = match.group()  # Returns the first number found
        else:
            student_year = year_name  # Fallback to full string
    else:
        student_year = "0"  # Default value if no year level set
    
    # Convert to string for JSON serialization and database comparison
    student_year_str = str(student_year)
    
    student_id = current_user.id

    # Base query with school year filter
    query = Election.query
    
    if start_date and end_date:
        query = query.filter(
            Election.start_date >= start_date,
            Election.start_date <= end_date
        )
    
    # ROBUST FILTERING - Works with both old and new data
    # Uses multiple conditions for maximum compatibility
    elections = query.filter(
        Election.start_date <= now_naive,
        Election.end_date >= now_naive,
        # Campus-wide: either scope='campus' OR election_type='SSG' OR department_id IS NULL
        # Department: either scope='department' OR election_type='Department' with matching department
        db.or_(
            # Campus-wide conditions
            db.and_(
                db.or_(
                    Election.scope == 'campus',
                    Election.election_type == 'SSG',
                    Election.department_id.is_(None)
                ),
                # For campus elections, check year level filtering
                db.or_(
                    Election.year_levels == 'all',  # All years allowed
                    Election.year_levels.is_(None),  # No year filter (treat as all)
                    db.and_(
                        Election.year_levels.isnot(None),
                        Election.year_levels != 'all',
                        db.func.find_in_set(student_year_str, Election.year_levels) > 0  # Student's year is in the list
                    )
                )
            ),
            # Department-specific conditions
            db.and_(
                db.or_(
                    Election.scope == 'department',
                    Election.election_type == 'Department'
                ),
                Election.department_id == student_department_id
            )
        )
    ).order_by(Election.start_date.asc()).all()

    # Calculate voting progress for each election
    election_data = []
    for election in elections:
        # Count UNIQUE voters
        unique_voters_count = db.session.query(func.count(func.distinct(Vote.student_id)))\
            .filter(Vote.election_id == election.id)\
            .scalar() or 0
        
        # Check if current student has already voted
        student_vote = Vote.query.filter(
            Vote.election_id == election.id, 
            Vote.student_id == student_id
        ).first()
        
        student_has_voted = student_vote is not None
        
        # Get vote timestamps if student has voted
        vote_timestamps = None
        if student_has_voted and student_vote:
            # Handle cast_timestamp (stored as Manila time)
            cast_time = student_vote.cast_timestamp
            if cast_time:
                if cast_time.tzinfo is None:
                    # If naive, assume it's Manila time (from your submit route)
                    cast_time_manila = local_tz.localize(cast_time)
                else:
                    cast_time_manila = cast_time.astimezone(local_tz)
            else:
                cast_time_manila = None
            
            # Handle recorded_timestamp (stored as UTC)
            recorded_time = student_vote.recorded_timestamp
            if recorded_time:
                if recorded_time.tzinfo is None:
                    # Convert UTC to Manila
                    recorded_time_utc = utc_tz.localize(recorded_time)
                    recorded_time_manila = recorded_time_utc.astimezone(local_tz)
                else:
                    recorded_time_manila = recorded_time.astimezone(local_tz)
            else:
                # Fallback to created_at if recorded_timestamp is None
                recorded_time = student_vote.created_at
                if recorded_time:
                    if recorded_time.tzinfo is None:
                        recorded_time_utc = utc_tz.localize(recorded_time)
                        recorded_time_manila = recorded_time_utc.astimezone(local_tz)
                    else:
                        recorded_time_manila = recorded_time.astimezone(local_tz)
                else:
                    recorded_time_manila = None
            
            # Format for display
            vote_timestamps = {
                'cast_time': cast_time,
                'cast_time_manila': cast_time_manila,
                'cast_time_formatted': cast_time_manila.strftime('%I:%M:%S %p') if cast_time_manila else None,
                'cast_date_formatted': cast_time_manila.strftime('%Y-%m-%d %I:%M:%S %p') if cast_time_manila else None,
                'recorded_time': recorded_time,
                'recorded_time_manila': recorded_time_manila,
                'recorded_time_formatted': recorded_time_manila.strftime('%I:%M:%S %p') if recorded_time_manila else None,
                'recorded_date_formatted': recorded_time_manila.strftime('%Y-%m-%d %I:%M:%S %p') if recorded_time_manila else None,
            }
        
        # Determine eligible voters count
        if election.department_id is None:
            # Campus-wide election - all students (but filter by year level if specified)
            if election.year_levels and election.year_levels != 'all':
                # Filter students by year level
                year_levels_list = election.year_levels.split(',')
                
                # Get all students with their year level relationships
                students = Student.query.options(db.joinedload(Student.year_level)).all()
                
                # Filter by year level in Python
                filtered_count = 0
                for student in students:
                    if student.year_level:
                        # Extract numeric part from year_name
                        year_name = student.year_level.year_name
                        match = re.search(r'\d+', year_name)
                        if match:
                            student_year_val = match.group()
                            if student_year_val in year_levels_list:
                                filtered_count += 1
                
                eligible_voters = filtered_count
            else:
                # All students
                eligible_voters = Student.query.count()
        else:
            # Department election
            if election.year_levels and election.year_levels != 'all':
                # Filter by both department and year level
                year_levels_list = election.year_levels.split(',')
                
                # Get students in the department with their year level
                students = Student.query.options(db.joinedload(Student.year_level)).filter_by(
                    department_id=election.department_id
                ).all()
                
                # Filter by year level in Python
                filtered_count = 0
                for student in students:
                    if student.year_level:
                        # Extract numeric part from year_name
                        year_name = student.year_level.year_name
                        match = re.search(r'\d+', year_name)
                        if match:
                            student_year_val = match.group()
                            if student_year_val in year_levels_list:
                                filtered_count += 1
                
                eligible_voters = filtered_count
            else:
                # Department only
                eligible_voters = Student.query.filter_by(
                    department_id=election.department_id
                ).count()
        
        # Calculate percentage
        if eligible_voters > 0:
            vote_percentage = (unique_voters_count / eligible_voters) * 100
        else:
            vote_percentage = 0
        
        # Determine if this student is eligible based on year level
        is_eligible_by_year = True
        if election.scope == 'campus' or election.election_type == 'SSG':
            if election.year_levels and election.year_levels != 'all':
                year_levels_list = election.year_levels.split(',')
                is_eligible_by_year = student_year_str in year_levels_list
        
        # Format target years for display
        target_years_display = 'all'
        if election.year_levels and election.year_levels != 'all':
            year_numbers = election.year_levels.split(',')
            # Convert to ordinal format (1 -> 1st, 2 -> 2nd, etc.)
            ordinal_years = []
            for year in year_numbers:
                year_int = int(year)
                if year_int == 1:
                    ordinal_years.append('1st Year')
                elif year_int == 2:
                    ordinal_years.append('2nd Year')
                elif year_int == 3:
                    ordinal_years.append('3rd Year')
                else:
                    ordinal_years.append(f'{year_int}th Year')
            target_years_display = ', '.join(ordinal_years)
        
        election_data.append({
            'election': election,
            'unique_voters': unique_voters_count,
            'eligible_voters': eligible_voters,
            'vote_percentage': round(vote_percentage, 1),
            'vote_percentage_int': int(vote_percentage),
            'student_has_voted': student_has_voted,
            'vote_timestamps': vote_timestamps,
            'is_eligible_by_year': is_eligible_by_year,
            'target_years': target_years_display,
            'target_years_raw': election.year_levels if election.year_levels and election.year_levels != 'all' else 'all'
        })

    return render_template('elections_available.html', 
                         election_data=election_data,
                         current_time=now_ph,
                         student_year=student_year_str,
                         student_year_display=current_user.year_level.year_name if current_user.year_level else 'Not Set',
                         school_years=get_all_school_years(),
                         current_sy=school_year)

# In your student/routes.py

# In student/routes.py - Full updated route

from datetime import datetime
from flask import session

@student_bp.route('/candidates')
@login_required
def candidates():
    # Get school year from request, session, or default
    school_year = request.args.get('school_year')
    
    # If no school year in URL, try to get from session
    if not school_year:
        school_year = session.get('current_school_year')
    
    # Get all elections to extract school years
    elections = Election.query.all()
    
    # Extract unique school years
    school_years = []
    for election in elections:
        if election.start_date:
            year = election.start_date.year
            # Only include if there are candidates for this election
            if election.candidates:
                next_year = year + 1
                school_year_str = f"{year}-{next_year}"
                if school_year_str not in school_years:
                    school_years.append(school_year_str)
    
    # Sort school years (latest first)
    school_years.sort(reverse=True)
    
    # If no school year selected, use the latest
    if not school_year and school_years:
        school_year = school_years[0]
    
    # Save to session
    if school_year:
        session['current_school_year'] = school_year
    
    # Get all candidates
    all_candidates = Candidate.query.order_by(Candidate.last_name).all()
    
    # Filter candidates by school year if selected
    filtered_candidates = []
    if school_year and school_years:
        try:
            start_year = int(school_year.split('-')[0])
            end_year = int(school_year.split('-')[1])
            
            # Create datetime range
            start_date = datetime(start_year, 1, 1)
            end_date = datetime(end_year, 12, 31)
            
            for candidate in all_candidates:
                if candidate.election and candidate.election.start_date:
                    if start_date <= candidate.election.start_date <= end_date:
                        filtered_candidates.append(candidate)
        except (ValueError, IndexError):
            # If school year format is invalid, show all
            filtered_candidates = all_candidates
    else:
        filtered_candidates = all_candidates
    
    return render_template('candidates.html', 
                         candidates=filtered_candidates,
                         school_years=school_years,
                         current_sy=school_year)


from datetime import datetime
from sqlalchemy import func


@student_bp.route('/results')
@login_required
def results():
    """Show elections that the current student has voted in"""
    # FIRST: Check URL parameter (when user clicks from hamburger menu)
    school_year = request.args.get('school_year')
    
    # SECOND: If no URL parameter, try to get from session
    if not school_year:
        school_year = session.get('current_school_year')
    
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
    
    # Save to session for other pages
    if school_year:
        session['current_school_year'] = school_year
    
    student_id = current_user.id
    now = datetime.now()
    
    # Get all elections the student has voted in
    voted_elections_ids = db.session.query(Vote.election_id).filter_by(
        student_id=student_id
    ).distinct().subquery()
    
    # Base query
    query = Election.query.filter(
        Election.id.in_(voted_elections_ids),
        Election.start_date <= now  # Only show elections that have started
    )
    
    # Apply school year filter if selected
    if start_date and end_date:
        query = query.filter(
            Election.start_date >= start_date,
            Election.start_date <= end_date
        )
    
    voted_elections = query.order_by(Election.end_date.desc()).all()
    
    return render_template('results.html',
                         voted_elections=voted_elections,
                         now=now,
                         school_years=get_all_school_years(),
                         current_sy=school_year)



    

@student_bp.route('/results/<int:election_id>')
@login_required
def results_detail(election_id):
    """Show detailed results for a specific election (only if student voted in it)"""
    student_id = current_user.id
    
    # Check if student voted in this election
    has_voted = Vote.query.filter_by(
        student_id=student_id,
        election_id=election_id
    ).first() is not None
    
    if not has_voted:
        flash('You can only view results for elections you have participated in.', 'warning')
        return redirect(url_for('student.results'))  # Fixed: changed from 'student.my_results' to 'student.results'
    
    # Get the election
    election = Election.query.get_or_404(election_id)
    
    local_tz = pytz.timezone("Asia/Manila")
    now = datetime.now(local_tz)
    now_naive = now.replace(tzinfo=None)
    
    # Determine results status
    if election.end_date < now_naive:
        results_status = "FINAL RESULTS"
    elif election.start_date <= now_naive <= election.end_date:
        results_status = "LIVE RESULTS - Ongoing Election"
    else:
        results_status = "UPCOMING ELECTION"
    
    # Calculate total registered voters
    if election.scope == 'department' and election.department_id:
        total_voters = Student.query.filter_by(
            department_id=election.department_id
        ).count()
    else:
        total_voters = Student.query.count()
    
    # Calculate UNIQUE voters
    unique_voters = db.session.query(Vote.student_id).filter_by(
        election_id=election.id
    ).distinct().count()
    
    # Calculate voter turnout
    voter_turnout = (unique_voters / total_voters * 100) if total_voters > 0 else 0
    
    # Get all candidates for this election
    all_candidates = Candidate.query.filter_by(election_id=election.id).all()
    
    # Get position limits
    position_limits = {}
    election_positions = ElectionPosition.query.filter_by(election_id=election.id).all()
    for ep in election_positions:
        position_limits[ep.position_id] = ep.max_votes
    
    # Get all votes for this election
    all_votes = Vote.query.filter_by(election_id=election.id).all()
    
    # Create candidate ID list
    all_candidate_ids = [c.id for c in all_candidates]
    
    # Initialize vote counts
    vote_counts = {candidate.id: 0 for candidate in all_candidates}
    
    # Decrypt votes
    if all_votes and all_candidate_ids:
        try:
            private_key = get_private_key()
            
            if private_key:
                total_vector = [0] * len(all_candidate_ids)
                
                for vote in all_votes:
                    try:
                        vote_list = json.loads(vote.encrypted_vote)
                        
                        for i, enc_dict in enumerate(vote_list):
                            try:
                                from phe import paillier
                                enc_num = paillier.EncryptedNumber(
                                    private_key.public_key,
                                    int(enc_dict["ciphertext"]),
                                    int(enc_dict["exponent"])
                                )
                                decrypted_value = private_key.decrypt(enc_num)
                                total_vector[i] += decrypted_value
                            except Exception:
                                continue
                    except Exception:
                        continue
                
                for i, candidate_id in enumerate(all_candidate_ids):
                    vote_counts[candidate_id] = total_vector[i]
        except Exception:
            pass
    
    # Group candidates by position
    candidates_by_position = {}
    for candidate in all_candidates:
        position_name = candidate.position.name if candidate.position else "Unknown Position"
        position_id = candidate.position_id
        
        if position_name not in candidates_by_position:
            candidates_by_position[position_name] = {
                'id': position_id,
                'name': position_name,
                'description': candidate.position.description if candidate.position else None,
                'candidates': []
            }
        
        department_name = candidate.department.name if candidate.department else None
        
        candidates_by_position[position_name]['candidates'].append({
            'id': candidate.id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'photo': candidate.photo,
            'party_list': candidate.party_list,
            'department': department_name,
            'vote_count': vote_counts.get(candidate.id, 0),
            'vote_percentage': 0,
            'is_winner': False
        })
    
    # Calculate percentages
    positions_data = []
    
    for position_name, position_data in candidates_by_position.items():
        candidates_list = position_data['candidates']
        position_total = sum(c['vote_count'] for c in candidates_list)
        max_votes_per_voter = position_limits.get(position_data['id'], 1)
        total_voters_count = unique_voters if unique_voters > 0 else 1
        
        if total_voters_count > 0:
            for candidate in candidates_list:
                if max_votes_per_voter > 1:
                    candidate['vote_percentage'] = round((candidate['vote_count'] / total_voters_count) * 100, 1)
                    if candidate['vote_percentage'] > 100:
                        candidate['vote_percentage'] = 100
                else:
                    if position_total > 0:
                        candidate['vote_percentage'] = round((candidate['vote_count'] / position_total) * 100, 1)
                    else:
                        candidate['vote_percentage'] = 0
        else:
            for candidate in candidates_list:
                candidate['vote_percentage'] = 0
        
        candidates_list.sort(key=lambda x: x['vote_count'], reverse=True)
        max_winners = position_limits.get(position_data['id'], 1)
        
        if election.end_date < now_naive and position_total > 0:
            for i, candidate in enumerate(candidates_list):
                if i < max_winners and candidate['vote_count'] > 0:
                    candidate['is_winner'] = True
        
        positions_data.append({
            'id': position_data['id'],
            'name': position_name,
            'description': position_data['description'],
            'candidates': candidates_list,
            'total_votes': position_total,
            'max_votes': max_winners
        })
    
    positions_data.sort(key=lambda x: x['id'])
    
    return render_template('student_results_detail.html',
                         election=election,
                         positions_data=positions_data,
                         total_voters=total_voters,
                         total_votes=unique_voters,
                         voter_turnout=round(voter_turnout, 1),
                         results_date=now,
                         results_status=results_status,
                         now=now_naive,
                         results_published=election.results_published)


                         
def get_private_key():
    """Get the Paillier private key for decryption"""
    try:
        import pickle
        import os
        # Try to load private key from file
        key_path = os.path.join(os.path.dirname(__file__), '..', 'paillier_private.key')
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                return pickle.load(f)
        else:
            # Try alternative path
            key_path = os.path.join(os.path.dirname(__file__), '..', 'keys', 'private_key.pkl')
            if os.path.exists(key_path):
                with open(key_path, 'rb') as f:
                    return pickle.load(f)
            else:
                # Silently return None if key not found
                return None
    except Exception:
        # Silently return None on error
        return None
    

@student_bp.route('/verify-my-vote', methods=['POST'])
@login_required
def verify_my_vote():
    """Verify a vote using the secret receipt code"""
    try:
        data = request.get_json()
        election_id = data.get('election_id')
        candidate_id = data.get('candidate_id')
        secret_code = data.get('secret_code')
        
        if not all([election_id, candidate_id, secret_code]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
        
        # Get the election
        election = Election.query.get(election_id)
        if not election:
            return jsonify({
                'success': False,
                'message': 'Election not found'
            }), 404
        
        # Get the candidate
        candidate = Candidate.query.get(candidate_id)
        if not candidate:
            return jsonify({
                'success': False,
                'message': 'Candidate not found'
            }), 404
        
        # Generate the finder hash to look for
        import hashlib
        import json
        search_hash = hashlib.sha256(f"{candidate_id}{secret_code}".encode()).hexdigest()
        
        print(f"🔍 Looking for hash: {search_hash[:16]}...")
        
        # Get ALL votes for this election
        votes = Vote.query.filter_by(election_id=election_id).all()
        print(f"📊 Found {len(votes)} total votes in this election")
        
        # Search through each vote's finder_hash JSON
        for vote in votes:
            try:
                if not vote.finder_hash:
                    continue
                    
                # Parse the JSON data
                finder_data = json.loads(vote.finder_hash)
                
                # Check if it's the new format with hash_strings list
                if isinstance(finder_data, dict) and 'hash_strings' in finder_data:
                    if search_hash in finder_data['hash_strings']:
                        print(f"✅ Found matching vote! Vote ID: {vote.id}")
                        
                        candidate_name = f"{candidate.first_name} {candidate.last_name}"
                        position_name = candidate.position.name if candidate.position else 'N/A'
                        
                        return jsonify({
                            'success': True,
                            'message': 'Vote verified successfully! Your vote has been counted.',
                            'hash': search_hash[:16] + '...',
                            'timestamp': vote.recorded_timestamp.strftime('%Y-%m-%d %H:%M:%S') if vote.recorded_timestamp else None,
                            'candidate_name': candidate_name,
                            'position': position_name
                        })
                
                # Check if it's the new format with hashes list
                elif isinstance(finder_data, dict) and 'hashes' in finder_data:
                    for item in finder_data['hashes']:
                        if item.get('hash') == search_hash:
                            print(f"✅ Found matching vote! Vote ID: {vote.id}")
                            
                            candidate_name = f"{candidate.first_name} {candidate.last_name}"
                            position_name = candidate.position.name if candidate.position else 'N/A'
                            
                            return jsonify({
                                'success': True,
                                'message': 'Vote verified successfully! Your vote has been counted.',
                                'hash': search_hash[:16] + '...',
                                'timestamp': vote.recorded_timestamp.strftime('%Y-%m-%d %H:%M:%S') if vote.recorded_timestamp else None,
                                'candidate_name': candidate_name,
                                'position': position_name
                            })
                
                # Check if it's a list of hashes
                elif isinstance(finder_data, list):
                    for item in finder_data:
                        if isinstance(item, dict) and item.get('hash') == search_hash:
                            print(f"✅ Found matching vote! Vote ID: {vote.id}")
                            
                            candidate_name = f"{candidate.first_name} {candidate.last_name}"
                            position_name = candidate.position.name if candidate.position else 'N/A'
                            
                            return jsonify({
                                'success': True,
                                'message': 'Vote verified successfully! Your vote has been counted.',
                                'hash': search_hash[:16] + '...',
                                'timestamp': vote.recorded_timestamp.strftime('%Y-%m-%d %H:%M:%S') if vote.recorded_timestamp else None,
                                'candidate_name': candidate_name,
                                'position': position_name
                            })
                
                # Check if it's a direct hash string (old format)
                elif isinstance(finder_data, str) and finder_data == search_hash:
                    print(f"✅ Found matching vote (old format)! Vote ID: {vote.id}")
                    
                    candidate_name = f"{candidate.first_name} {candidate.last_name}"
                    position_name = candidate.position.name if candidate.position else 'N/A'
                    
                    return jsonify({
                        'success': True,
                        'message': 'Vote verified successfully! Your vote has been counted.',
                        'hash': search_hash[:16] + '...',
                        'timestamp': vote.recorded_timestamp.strftime('%Y-%m-%d %H:%M:%S') if vote.recorded_timestamp else None,
                        'candidate_name': candidate_name,
                        'position': position_name
                    })
                    
            except json.JSONDecodeError:
                # If not JSON, check if it's a direct hash string
                if vote.finder_hash == search_hash:
                    print(f"✅ Found matching vote (plain text)! Vote ID: {vote.id}")
                    
                    candidate_name = f"{candidate.first_name} {candidate.last_name}"
                    position_name = candidate.position.name if candidate.position else 'N/A'
                    
                    return jsonify({
                        'success': True,
                        'message': 'Vote verified successfully! Your vote has been counted.',
                        'hash': search_hash[:16] + '...',
                        'timestamp': vote.recorded_timestamp.strftime('%Y-%m-%d %H:%M:%S') if vote.recorded_timestamp else None,
                        'candidate_name': candidate_name,
                        'position': position_name
                    })
                continue
            except Exception as e:
                print(f"Error processing vote {vote.id}: {e}")
                continue
        
        # If we get here, no match found
        print(f"❌ No matching vote found for hash: {search_hash[:16]}...")
        return jsonify({
            'success': False,
            'message': 'No vote found with this secret code. Please check your code and try again.'
        })
            
    except Exception as e:
        print(f"Verification error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Verification error: {str(e)}'
        }), 500


@student_bp.route('/api/refresh-results/<int:election_id>')
@login_required
def refresh_results_api(election_id):
    """API endpoint to refresh results via AJAX"""
    try:
        # Get the election
        election = Election.query.get(election_id)
        if not election:
            return jsonify({'success': False, 'message': 'Election not found'}), 404
        
        # Get all candidates
        all_candidates = Candidate.query.filter_by(election_id=election_id).all()
        
        # Get position limits
        position_limits = {}
        election_positions = ElectionPosition.query.filter_by(election_id=election_id).all()
        for ep in election_positions:
            position_limits[ep.position_id] = ep.max_votes
        
        # Get all votes
        all_votes = Vote.query.filter_by(election_id=election_id).all()
        all_candidate_ids = [c.id for c in all_candidates]
        
        # Initialize vote counts
        vote_counts = {candidate.id: 0 for candidate in all_candidates}
        
        # Decrypt votes (use your actual decryption logic here)
        if all_votes and all_candidate_ids:
            try:
                private_key = get_private_key()
                if private_key:
                    total_vector = [0] * len(all_candidate_ids)
                    
                    for vote in all_votes:
                        try:
                            vote_list = json.loads(vote.encrypted_vote)
                            for i, enc_dict in enumerate(vote_list):
                                from phe import paillier
                                enc_num = paillier.EncryptedNumber(
                                    private_key.public_key,
                                    int(enc_dict["ciphertext"]),
                                    int(enc_dict["exponent"])
                                )
                                total_vector[i] += private_key.decrypt(enc_num)
                        except:
                            continue
                    
                    for i, candidate_id in enumerate(all_candidate_ids):
                        vote_counts[candidate_id] = total_vector[i]
            except:
                pass
        
        # Group by position
        candidates_by_position = {}
        for candidate in all_candidates:
            position_name = candidate.position.name if candidate.position else "Unknown"
            position_id = candidate.position_id
            
            if position_name not in candidates_by_position:
                candidates_by_position[position_name] = {
                    'id': position_id,
                    'name': position_name,
                    'description': candidate.position.description if candidate.position else None,
                    'candidates': []
                }
            
            candidates_by_position[position_name]['candidates'].append({
                'id': candidate.id,
                'first_name': candidate.first_name,
                'last_name': candidate.last_name,
                'photo': candidate.photo,
                'party_list': candidate.party_list,
                'department': candidate.department.name if candidate.department else None,
                'vote_count': vote_counts.get(candidate.id, 0),
                'vote_percentage': 0,
                'is_winner': False
            })
        
        # Prepare positions data
        positions_data = []
        local_tz = pytz.timezone("Asia/Manila")
        now = datetime.now(local_tz).replace(tzinfo=None)
        
        for pos_name, pos_data in candidates_by_position.items():
            candidates_list = pos_data['candidates']
            position_total = sum(c['vote_count'] for c in candidates_list)
            
            if position_total > 0:
                for c in candidates_list:
                    c['vote_percentage'] = round((c['vote_count'] / position_total) * 100, 1)
            
            candidates_list.sort(key=lambda x: x['vote_count'], reverse=True)
            
            max_winners = position_limits.get(pos_data['id'], 1)
            
            if election.end_date < now and position_total > 0:
                for i, c in enumerate(candidates_list):
                    if i < max_winners and c['vote_count'] > 0:
                        c['is_winner'] = True
            
            positions_data.append({
                'id': pos_data['id'],
                'name': pos_name,
                'description': pos_data['description'],
                'candidates': candidates_list,
                'total_votes': position_total
            })
        
        positions_data.sort(key=lambda x: x['id'])
        
        # Render the HTML for results
        html = render_template('partials/results_partial.html', positions_data=positions_data)
        
        # Calculate summary stats
        total_votes = len(all_votes)
        if election.department_id:
            total_voters = Student.query.filter_by(department_id=election.department_id).count()
        else:
            total_voters = Student.query.count()
        
        voter_turnout = round((total_votes / total_voters * 100), 1) if total_voters > 0 else 0
        
        return jsonify({
            'success': True,
            'html': html,
            'summary': {
                'total_votes': total_votes,
                'voter_turnout': voter_turnout
            }
        })
        
    except Exception as e:
        print(f"Refresh error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ------------------- GUIDELINES -------------------
@student_bp.route('/guidelines')
@login_required
def guidelines():
    rules = [
        {"title": "Eligibility", "body": "All enrolled students with an active ID number are eligible."},
        {"title": "Voting Period", "body": "Voting opens Nov 25 and closes Nov 30, 5:00 PM."},
        {"title": "Prohibited Acts", "body": "Sharing of ballots, buying/selling votes, multiple submissions are prohibited."},
        {"title": "Privacy", "body": "Ballot choices are private and not displayed in public records."}
    ]
    return render_template('guidelines.html', rules=rules)

# ------------------- ANNOUNCEMENTS -------------------
@student_bp.route('/announcements')
@login_required
def announcements_page():
    announcements = [
        {"title": "Election Kickoff", "date": "2025-11-25", "body": "Welcome! Voting starts today."},
        {"title": "Last Day Reminder", "date": "2025-11-30", "body": "Last day to vote. Closes at 5 PM."}
    ]
    return render_template('announcements.html', announcements=announcements)




# ==================== PROFILE ====================
# Add these imports at the top
import random
import string
import uuid
from flask_mail import Message
from datetime import datetime, timedelta
import json
from flask import current_app

# Store verification codes temporarily (in production, use Redis or database)
verification_codes = {}
# Store email change requests
email_change_requests = {}

@student_bp.route('/profile')
@login_required
def profile():
    # FIRST: Check URL parameter (when user clicks from hamburger menu)
    school_year = request.args.get('school_year')
    
    # SECOND: If no URL parameter, try to get from session
    if not school_year:
        school_year = session.get('current_school_year')
    
    # Save to session for other pages
    if school_year:
        session['current_school_year'] = school_year
    
    device = is_device_trusted(current_user.id)
    
    # Fetch courses and year levels from database
    courses = Course.query.all()
    year_levels = YearLevel.query.all()
    
    # Check if user has pending deletion request
    has_pending_deletion = DeletionRequest.query.filter_by(
        student_id=current_user.id,
        status='pending'
    ).first() is not None

    return render_template('profile.html',
        student=current_user,
        device_trusted=bool(device),
        has_fingerprint=False,
        voting_history=[],
        has_voted_current=False,
        courses=courses,
        year_levels=year_levels,
        has_pending_deletion=has_pending_deletion,
        school_years=get_all_school_years(),
        current_sy=school_year
    )

@student_bp.route('/profile/edit', methods=['POST'])
@login_required
def edit_profile():
    try:
        student = current_user
        
        # Get form data
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        course_id = request.form.get('course_id')
        year_level_id = request.form.get('year_level_id')
        old_email_verified = request.form.get('old_email_verified')
        new_email_verified = request.form.get('new_email_verified')
        
        changes = {}
        
        # Update username if changed
        if new_username and new_username != student.username:
            # Check if username is already taken
            from student.models import Student
            existing_student = Student.query.filter_by(username=new_username).first()
            if existing_student and existing_student.id != student.id:
                return jsonify({
                    'success': False,
                    'error': 'Username already taken'
                }), 400
            
            student.username = new_username
            changes['username'] = new_username
        
        # Check if email is being changed
        if new_email and new_email != student.email:
            # Verify both old and new email verifications
            if old_email_verified != 'true' or new_email_verified != 'true':
                return jsonify({
                    'success': False,
                    'error': 'Email change requires verification of both old and new emails'
                }), 400
            
            # Check if new email is already taken
            from student.models import Student
            existing_student = Student.query.filter_by(email=new_email).first()
            if existing_student and existing_student.id != student.id:
                return jsonify({
                    'success': False,
                    'error': 'Email already in use'
                }), 400
            
            # Update email
            old_email = student.email
            student.email = new_email
            changes['email'] = {'old': old_email, 'new': new_email}
            
            # Send notification to old email
            send_email_change_notification(student, old_email, new_email)
        
        # Update course if changed
        if course_id and str(student.course_id) != course_id:
            from admin.models import Course
            course = Course.query.get(course_id)
            if course:
                student.course_id = int(course_id)
                student.course = course.course_name
                changes['course'] = course.course_name
        
        # Update year level if changed
        if year_level_id and str(student.year_level_id) != year_level_id:
            from admin.models import YearLevel
            year = YearLevel.query.get(year_level_id)
            if year:
                student.year_level_id = int(year_level_id)
                changes['year'] = year.year_name
        
        db.session.commit()
        
        # Get updated values for response
        new_course = student.course_rel.course_name if student.course_rel else student.course
        new_year = student.year_level.year_name if student.year_level else 'Not set'
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'changes': changes,
            'new_username': student.username,
            'new_email': student.email,
            'new_course': new_course,
            'new_year': new_year
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@student_bp.route('/send-email-change-verification', methods=['POST'])
@login_required
def send_email_change_verification():
    data = request.get_json()
    old_email = data.get('old_email')
    new_email = data.get('new_email')
    
    if not old_email or not new_email:
        return jsonify({'error': 'Emails are required'}), 400
    
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    
    # Store request
    email_change_requests[request_id] = {
        'student_id': current_user.id,
        'old_email': old_email,
        'new_email': new_email,
        'status': 'pending',
        'created_at': datetime.now(),
        'expiry': datetime.now() + timedelta(minutes=15)
    }
    
    try:
        # Mask email for display
        masked_new_email = mask_email(new_email)
        
        # Generate confirm and reject URLs
        confirm_url = url_for('student.confirm_email_change', 
                            request_id=request_id, 
                            action='confirm', 
                            _external=True)
        reject_url = url_for('student.confirm_email_change', 
                           request_id=request_id, 
                           action='reject', 
                           _external=True)
        
        # Render the email template
        email_html = render_template('verify_email_change.html',
                                   masked_email=masked_new_email,
                                   confirm_url=confirm_url,
                                   reject_url=reject_url)
        
        # Send verification email to OLD email
        msg = Message(
            'Confirm Email Change Request',
            recipients=[old_email]
        )
        msg.html = email_html
        
        mail.send(msg)
        
        return jsonify({
            'success': True,
            'request_id': request_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@student_bp.route('/confirm-email-change/<request_id>/<action>')
def confirm_email_change(request_id, action):
    if request_id not in email_change_requests:
        return "Invalid or expired request", 404
    
    request_data = email_change_requests[request_id]
    
    if datetime.now() > request_data['expiry']:
        return "This request has expired", 400
    
    if action == 'confirm':
        request_data['status'] = 'confirmed'
        return """
        <html>
        <head>
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; background: #f4f6fb; }
                .card { background: white; max-width: 400px; margin: 0 auto; padding: 30px; border-radius: 18px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }
                .icon { font-size: 64px; margin-bottom: 20px; }
                h2 { color: #1f2937; }
                p { color: #4b5563; }
            </style>
        </head>
        <body>
            <div class="card">
                <div class="icon">✅</div>
                <h2>Email Change Confirmed!</h2>
                <p>You can now return to the application and enter the OTP code.</p>
                <p>This window can be closed.</p>
            </div>
        </body>
        </html>
        """
    elif action == 'reject':
        request_data['status'] = 'rejected'
        return """
        <html>
        <head>
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; background: #f4f6fb; }
                .card { background: white; max-width: 400px; margin: 0 auto; padding: 30px; border-radius: 18px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }
                .icon { font-size: 64px; margin-bottom: 20px; }
                h2 { color: #1f2937; }
                p { color: #4b5563; }
            </style>
        </head>
        <body>
            <div class="card">
                <div class="icon">❌</div>
                <h2>Email Change Rejected</h2>
                <p>The email change request has been cancelled.</p>
                <p>This window can be closed.</p>
            </div>
        </body>
        </html>
        """
    
    return "Invalid action", 400

@student_bp.route('/email-change-status/<request_id>')
@login_required
def email_change_status(request_id):
    if request_id not in email_change_requests:
        return jsonify({'status': 'unknown'})
    
    request_data = email_change_requests[request_id]
    
    # Clean up expired requests
    if datetime.now() > request_data['expiry']:
        return jsonify({'status': 'expired'})
    
    return jsonify({'status': request_data['status']})

@student_bp.route('/send-otp-to-new-email', methods=['POST'])
@login_required
def send_otp_to_new_email():
    data = request.get_json()
    email = data.get('email')
    request_id = data.get('request_id')
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    # Generate 6-digit OTP
    otp = ''.join(random.choices(string.digits, k=6))
    
    # Store OTP
    session['new_email_otp'] = otp
    session['new_email_otp_expiry'] = (datetime.now() + timedelta(minutes=10)).timestamp()
    session['pending_new_email'] = email
    session['change_request_id'] = request_id
    
    try:
        msg = Message(
            'Verify Your New Email Address',
            recipients=[email]
        )
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 30px;">
            <h2>Cebu Technological University Moalboal Campus</h2>
            <p>Your verification code for your new email address is:</p>
            <h1 style="font-size: 36px; letter-spacing: 5px; color: #2563eb;">{otp}</h1>
            <p>This code will expire in 10 minutes.</p>
        </div>
        """
        
        mail.send(msg)
        
        # In development, return code for testing
        if current_app.config.get('DEBUG'):
            return jsonify({'success': True, 'code': otp})
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@student_bp.route('/send-verification-code', methods=['POST'])
@login_required
def send_verification_code():
    data = request.get_json()
    email = data.get('email')
    verification_type = data.get('type', 'new')  # 'old' or 'new'
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    # Generate 6-digit code
    code = ''.join(random.choices(string.digits, k=6))
    
    # Store code with expiry (10 minutes)
    verification_codes[f"{email}_{verification_type}"] = {
        'code': code,
        'expiry': datetime.now() + timedelta(minutes=10),
        'user_id': current_user.id,
        'type': verification_type
    }
    
    try:
        # Customize email based on verification type
        if verification_type == 'old':
            subject = "Verify Your Identity - Email Change Request"
            email_body = f"""
            <div style="font-family: Arial, sans-serif; text-align: center;">
                <h2>Cebu Technological University Moalboal Campus</h2>
                <p>Hello <strong>{current_user.first_name}</strong>,</p>
                <p>We received a request to change your email address.</p>
                <p>Your <strong>verification code</strong> is:</p>
                <h1 style="font-size: 32px; letter-spacing: 5px;">{code}</h1>
                <p>This code will expire in 10 minutes.</p>
                <p>If you did not request this change, please ignore this email or contact support.</p>
            </div>
            """
        else:
            subject = "Verify Your New Email Address"
            email_body = f"""
            <div style="font-family: Arial, sans-serif; text-align: center;">
                <h2>Cebu Technological University Moalboal Campus</h2>
                <p>Hello <strong>{current_user.first_name}</strong>,</p>
                <p>Please verify your new email address.</p>
                <p>Your <strong>verification code</strong> is:</p>
                <h1 style="font-size: 32px; letter-spacing: 5px;">{code}</h1>
                <p>This code will expire in 10 minutes.</p>
            </div>
            """
        
        msg = Message(
            subject=subject,
            recipients=[email]
        )
        msg.html = email_body
        
        mail.send(msg)
        
        # In development, return code for testing
        if current_app.config.get('DEBUG'):
            return jsonify({'success': True, 'code': code})
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def send_email_change_notification(student, old_email, new_email):
    """Send notification to old email about email change"""
    try:
        msg = Message(
            'Your Email Has Been Changed',
            recipients=[old_email]
        )
        msg.body = f"""
        Your email address for your voting account has been changed.
        
        Old email: {old_email}
        New email: {new_email}
        
        If you did not make this change, please contact support immediately.
        """
        msg.html = f"""
        <div style="font-family: Arial, sans-serif;">
            <h2>Cebu Technological University Moalboal Campus</h2>
            <p>Hello <strong>{student.first_name}</strong>,</p>
            <p>Your email address for your voting account has been changed.</p>
            <p><strong>Old email:</strong> {old_email}<br>
            <strong>New email:</strong> {new_email}</p>
            <p>If you did not make this change, please contact support immediately.</p>
        </div>
        """
        
        mail.send(msg)
        print(f"Email change notification sent to {old_email}")
    except Exception as e:
        print(f"Failed to send email change notification: {e}")

def mask_email(email):
    if not email or '@' not in email:
        return email
    name, domain = email.split('@')
    if len(name) > 2:
        return name[0] + '*' * (len(name) - 2) + name[-1] + '@' + domain
    elif len(name) == 2:
        return name[0] + '*@' + domain
    return email


def send_deletion_request_notification(student, reason):
    """Send notification to admin about deletion request"""
    try:
        # Get admin emails
        from admin.models import Admin
        admins = Admin.query.filter_by(is_active=True).all()
        admin_emails = [admin.email for admin in admins]
        
        if admin_emails:
            msg = Message(
                'New Account Deletion Request',
                recipients=admin_emails
            )
            msg.html = f"""
            <div style="font-family: Arial, sans-serif;">
                <h2>New Deletion Request</h2>
                <p><strong>Student:</strong> {student.first_name} {student.last_name}</p>
                <p><strong>ID Number:</strong> {student.id_number}</p>
                <p><strong>Email:</strong> {student.email}</p>
                <p><strong>Reason:</strong> {reason}</p>
                <p><strong>Request Date:</strong> {datetime.now().strftime('%B %d, %Y %I:%M %p')}</p>
                <p>Please review this request in the admin panel.</p>
            </div>
            """
            mail.send(msg)
    except Exception as e:
        print(f"Failed to send admin notification: {e}")



def send_deletion_confirmation_email(student, reason):
    """Send confirmation email to student about deletion request"""
    try:
        msg = Message(
            'Account Deletion Request Received',
            recipients=[student.email]
        )
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1f2937;">Account Deletion Request</h2>
            <p>Hello <strong>{student.first_name}</strong>,</p>
            <p>We have received your request to delete your account. Here are the details:</p>
            
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Reason provided:</strong></p>
                <p style="font-style: italic;">{reason[:200]}{'...' if len(reason) > 200 else ''}</p>
                <p><small>Total characters: {len(reason)}</small></p>
            </div>
            
            <p><strong>What happens next?</strong></p>
            <ul>
                <li>Your request has been submitted to our administrators for review.</li>
                <li>You will receive another email once your request has been processed.</li>
                <li>If approved, your account will be deactivated and data will be scheduled for deletion.</li>
            </ul>
            
            <p style="color: #6b7280; font-size: 0.9rem; margin-top: 30px;">
                If you did not request this deletion, please contact support immediately.
            </p>
            
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
            
            <p style="color: #9ca3af; font-size: 0.8rem; text-align: center;">
                Cebu Technological University Moalboal Campus<br>
                This is an automated message, please do not reply.
            </p>
        </div>
        """
        
        mail.send(msg)
        print(f"Deletion confirmation email sent to {student.email}")
        
    except Exception as e:
        print(f"Failed to send deletion confirmation email: {e}")
        # Don't raise the exception - we don't want to block the request if email fails


@student_bp.route('/request-deletion', methods=['POST'])
@login_required
def request_deletion():
    try:
        data = request.get_json()
        reason = data.get('reason', '').strip()
        
        if not reason:
            return jsonify({'error': 'Please provide a reason for deletion'}), 400
        
        if len(reason) > 5000:
            return jsonify({'error': f'Maximum 5000 characters allowed (you provided {len(reason)})'}), 400
        
        if len(reason) < 10:
            return jsonify({'error': 'Please provide at least 10 characters'}), 400
        
        # Check if there's already a pending request
        existing_request = DeletionRequest.query.filter_by(
            student_id=current_user.id,
            status='pending'
        ).first()
        
        if existing_request:
            return jsonify({'error': 'You already have a pending deletion request'}), 400
        
        # Create new deletion request
        deletion_request = DeletionRequest(
            student_id=current_user.id,
            reason=reason,
            status='pending'
        )
        
        db.session.add(deletion_request)
        db.session.commit()
        
        # Send confirmation email to student
        send_deletion_confirmation_email(current_user, reason)
        
        return jsonify({
            'success': True,
            'message': 'Deletion request submitted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in request_deletion: {str(e)}")
        return jsonify({'error': 'An internal error occurred'}), 500



# ------------------- LOGOUT -------------------

@student_bp.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash("You have been logged out.", "success")

    return redirect(url_for('student.login'))


# ------------------- CONTEXT PROCESSOR -------------------
@student_bp.app_context_processor
def inject_student_status():
    try:
        if current_user and current_user.is_authenticated:
            has_voted = Vote.query.filter_by(student_id=current_user.id).first() is not None
            return {'has_voted': has_voted}
    except Exception:
        pass
    return {'has_voted': False}

# ------------------- SUPPORT -------------------
@student_bp.route('/support')
@login_required
def support():
    return render_template('support.html')


# ===================== WEBAUTHN / BIOMETRIC ROUTES =====================

# student/routes.py
# ==================== WEBAUTHN / BIOMETRIC ROUTES ====================
# ─── Registration ──────────────────────────
@student_bp.route("/webauthn/register/options")
def webauthn_register_options():
    username = request.args.get("username")
    if not username:
        return jsonify({"status": "Error", "message": "Username is required"}), 400

    user = Student.query.filter_by(username=username).first()
    if not user:
        return jsonify({"status": "Error", "message": "User not found"}), 404

    origin, rp_id = get_origin_and_rp_id()

    options = generate_registration_options(
        rp_name="Fingerprint Demo",
        rp_id=rp_id,
        user_id=str(user.id).encode("utf-8"),
        user_name=user.username,
        attestation=AttestationConveyancePreference.DIRECT,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.REQUIRED,
            require_resident_key=True,
            user_verification=UserVerificationRequirement.REQUIRED
        )
    )

    user.current_challenge = options.challenge
    db.session.commit()

    return options_to_json(options)

    user.current_challenge = options.challenge
    db.session.commit()

    return options_to_json(options)


@student_bp.route("/webauthn/register/verify", methods=["POST"])
def webauthn_register_verify():
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"status": "Error", "message": "Username is required"}), 400

    user = Student.query.filter_by(username=username).first()
    if not user:
        return jsonify({"status": "Error", "message": "User not found"}), 404

    origin, rp_id = get_origin_and_rp_id()
    try:
        verification = verify_registration_response(
            credential=data,
            expected_challenge=user.current_challenge,
            expected_rp_id=rp_id,
            expected_origin=origin
        )

        user.passkey_id = verification.credential_id
        user.public_key = verification.credential_public_key
        user.sign_count = verification.sign_count
        user.current_challenge = None
        db.session.commit()

        return jsonify({"status": "Fingerprint registered!"})
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)})



@student_bp.route("/webauthn/login/options")
def webauthn_login_options():
    """
    Phase 2: True one-click passkey login
    - No Student ID input needed
    - Browser selects resident key automatically
    """
    origin, rp_id = get_origin_and_rp_id()

    # Get all students who have registered a fingerprint
    users_with_passkey = Student.query.filter(Student.passkey_id != None).all()
    if not users_with_passkey:
        return jsonify({"status": "Error", "message": "No students have registered fingerprints"}), 400

    # allow_credentials is None → browser will automatically show resident keys
    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=None,  # Resident key login: browser picks automatically
        user_verification=UserVerificationRequirement.REQUIRED
    )

    # Save the challenge to all users with passkeys
    for u in users_with_passkey:
        u.current_challenge = options.challenge
    db.session.commit()

    return options_to_json(options)


from base64 import b64decode

from flask_login import login_user
@student_bp.route("/webauthn/login/verify", methods=["POST"])
def webauthn_login_verify():
    """
    Phase 2: True one-click passkey login
    - No Student ID needed
    - Identify user by credential.userHandle
    """
    data = request.get_json()
    
    # userHandle is base64url encoded, convert to bytes
    user_handle_b64 = data.get("response", {}).get("userHandle")
    if not user_handle_b64:
        return jsonify({"status": "Error", "message": "No userHandle provided"}), 400

    try:
        user_handle_bytes = b64decode(user_handle_b64 + "==")  # restore padding
        user_id = int(user_handle_bytes.decode("utf-8"))
    except Exception as e:
        return jsonify({"status": "Error", "message": f"Invalid userHandle: {str(e)}"}), 400

    # Lookup user by ID
    user = Student.query.filter_by(id=user_id).first()
    if not user or not user.passkey_id:
        return jsonify({"status": "Error", "message": "User not found or no fingerprint registered"}), 400

    origin, rp_id = get_origin_and_rp_id()

    try:
        verification = verify_authentication_response(
            credential=data,
            expected_challenge=user.current_challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=user.public_key,
            credential_current_sign_count=user.sign_count
        )

        # Update sign count and clear challenge
        user.sign_count = verification.new_sign_count
        user.current_challenge = None
        db.session.commit()

        # Log the user in for Flask-Login
        login_user(user)

        return jsonify({"status": "Login successful!"})

    except Exception as e:
        print("WebAuthn verification failed:", str(e))
        return jsonify({"status": "Error", "message": f"Biometric verification failed: {str(e)}"}), 400