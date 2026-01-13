# student/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from student.models import Student, Vote
from admin.models import Candidate, Election, Course, Department, Announcement, YearLevel
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

# ==================== REGISTER ====================
@student_bp.route('/register', methods=['GET', 'POST'])
def register():
    from admin.models import Department, Course

    # ✅ Clear form session only if not coming from failed POST
    if request.method == 'GET':
        if not session.pop('keep_form', False):
            session.pop('registration_data', None)
            session.pop('error_fields', None)

    if request.method == 'POST':
        session['registration_data'] = request.form.to_dict()
        session['error_fields'] = []
        session['keep_form'] = True   # ⭐ Keep form values if errors

        email = request.form.get('email').strip()
        id_number = request.form.get('id_number')
        username = request.form.get('username')

        # Check duplicates
        if Student.query.filter(func.trim(Student.id_number) == id_number).first():
            flash("ID Number already registered!", "danger")
            session['error_fields'].append('id_number')

        if Student.query.filter_by(email=email).first():
            flash("Email already registered!", "danger")
            session['error_fields'].append('email')

        if Student.query.filter_by(username=username).first():
            flash("Username already taken!", "danger")
            session['error_fields'].append('username')

        if session['error_fields']:
            return redirect(url_for('student.register'))

        # ✅ Course validation
        course_id = request.form.get('course')
        course_obj = Course.query.get(course_id)
        if not course_obj:
            flash("Selected course is invalid.", "danger")
            session['error_fields'].append('course')
            return redirect(url_for('student.register'))

        registration_data = session['registration_data']
        registration_data.update({
            "course": course_obj.course_name,
            "course_id": course_obj.id,
            "department_id": course_obj.department_id
        })

        # Generate OTP
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

            # ✅ Do NOT clear session yet — keep registration_data for OTP verification & resend
            flash("OTP has been sent to your email.", "info")
            return redirect(url_for('student.verify_otp'))

        except Exception as e:
            flash(f"Failed to send OTP email: {str(e)}", "danger")

    # Load departments & courses
    departments = Department.query.order_by(Department.name).all()
    courses_by_department = {
        dept.name: Course.query.filter_by(department_id=dept.id).all()
        for dept in departments
    }

    year_levels = YearLevel.query.order_by(YearLevel.id).all()

    return render_template(
        'student_register.html',
        courses_by_department=courses_by_department,
        year_levels=year_levels
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




#=======================STOP HERE WHEN UNDO===========================
# ==================== LOGIN (merged traditional + WebAuthn page) ====================
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
                    flash('Login successful!', 'success')
                    return redirect(url_for('student.dashboard', trust_prompt=True))

            # 🔐 =======================================================

            # ✅ Trusted device → proceed with normal login
            login_user(student)
            flash('Login successful!', 'success')
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
from student.utils import generate_device_fingerprint, is_device_trusted
from student.models import TrustedDevice

@student_bp.route('/dashboard')
@login_required
def dashboard():
    # ---------------- Existing logic ----------------
    total_students = Student.query.count()
    total_votes = Vote.query.count()

    has_voted = Vote.query.filter_by(student_id=current_user.id).first() is not None

    announcements = Announcement.query.filter(
        (Announcement.department_id == current_user.department_id) | 
        (Announcement.department_id == None)  # None means "All"
    ).order_by(Announcement.date.desc()).all()

    leading_candidates = (
        db.session.query(Candidate, func.count(Vote.id).label("vote_count"))
        .outerjoin(Vote, Candidate.id == Vote.candidate_id)
        .group_by(Candidate.id)
        .order_by(func.count(Vote.id).desc())
        .limit(5)
        .all()
    )

    # ---------------- New: trust-device prompt ----------------
    fingerprint = generate_device_fingerprint()

    device = TrustedDevice.query.filter_by(
        student_id=current_user.id,
        device_fingerprint=fingerprint
    ).first()

    trust_prompt = False
    if device is None:
        # No device recorded yet → show prompt in dashboard
        trust_prompt = True

    # ---------------- Render template ----------------
    return render_template(
        'student_dashboard.html',
        total_students=total_students,
        total_votes=total_votes,
        has_voted=has_voted,
        announcements=announcements,
        leading_candidates=leading_candidates,
        trust_prompt=trust_prompt  # <-- new variable
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
    # Fetch all announcements relevant to the student
    announcements = Announcement.query.filter(
        (Announcement.department_id == current_user.department_id) | 
        (Announcement.department_id == None)
    ).order_by(Announcement.date.desc()).all()

    return render_template(
        'student_announcements.html',
        announcements=announcements
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

    # Fetch candidates and group by position
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    candidates_by_position = defaultdict(list)
    for c in candidates:
        if c.position:
            candidates_by_position[c.position.name].append(c)

    return render_template(
        'vote_page.html',
        election=election,
        candidates_by_position=candidates_by_position
    )

@student_bp.route('/vote/<int:election_id>/submit', methods=['POST'])
@login_required
def submit_vote(election_id):
    # Get all selected candidates from the form
    selected_candidates = {
        key: value for key, value in request.form.items() if key.startswith('candidate_')
    }

    if not selected_candidates:
        flash("Please select at least one candidate before submitting.", "warning")
        return redirect(url_for('student.vote_page', election_id=election_id))

    # Prevent duplicate voting
    existing_vote = Vote.query.filter_by(student_id=current_user.id, election_id=election_id).first()
    if existing_vote:
        flash("You have already voted in this election.", "info")
        return redirect(url_for('student.available_elections'))

    # Record votes for each position
    for position_name, candidate_id in selected_candidates.items():
        vote = Vote(student_id=current_user.id, candidate_id=int(candidate_id), election_id=election_id)
        db.session.add(vote)

    db.session.commit()
    flash("Your vote has been submitted successfully!", "success")
    return redirect(url_for('student.available_elections'))



from sqlalchemy import or_

from flask import flash, redirect, url_for
from sqlalchemy import or_

@student_bp.route('/available_elections')
@login_required
def available_elections():
    # Philippines timezone
    local_tz = pytz.timezone("Asia/Manila")
    now = datetime.now(local_tz)

    student_department_id = current_user.department_id

    # Filter elections student can vote in
    elections = Election.query.filter(
        Election.start_date <= now,
        Election.end_date >= now,
        or_(
            Election.department_id == student_department_id,  # department-specific
            Election.department_id == None  # SSG/general
        )
    ).order_by(Election.start_date.asc()).all()

    return render_template('elections_available.html', elections=elections)




# ------------------- CANDIDATES -------------------
@student_bp.route('/candidates')
@login_required
def candidates():
    candidates = Candidate.query.order_by(Candidate.last_name).all()
    return render_template('candidates.html', candidates=candidates)

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

# ------------------- RECEIPT -------------------
@student_bp.route('/receipt')
@login_required
def receipt():
    vote = Vote.query.filter_by(student_id=current_user.id).first()
    if not vote:
        flash('No voting record found. You have not voted yet.', 'info')
        return redirect(url_for('student.dashboard'))

    raw = f"{vote.id}-{current_user.id}-{int(time.time())}"
    receipt_code = hashlib.sha256(raw.encode()).hexdigest()[:12].upper()
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    return render_template('receipt.html', vote=vote, receipt_code=receipt_code, timestamp=timestamp)

# ==================== PROFILE ====================

@student_bp.route('/profile')
@login_required
def profile():
    device = is_device_trusted(current_user.id)

    return render_template(
        'profile.html',
        student=current_user,
        device_trusted=bool(device)
    )





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
