# student/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from student.models import Student, Vote
from admin.models import Candidate, Election, Course, Department
from extensions import db, bcrypt, mail
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func
from flask_mail import Message
import hashlib, time, random
from flask_login import current_user
from admin.models import Election
from flask import render_template
from flask_login import login_required
from datetime import datetime
import pytz


# WebAuthn imports
from webauthn import (
    generate_registration_options,
    generate_authentication_options,
    options_to_json,
    verify_registration_response,
    verify_authentication_response
)

# helper conversions
try:
    from webauthn.helpers import bytes_to_base64url, base64url_to_bytes
except Exception:
    import base64
    def bytes_to_base64url(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).decode().rstrip("=")
    def base64url_to_bytes(s: str) -> bytes:
        padding = '=' * (-len(s) % 4)
        return base64.urlsafe_b64decode(s + padding)

student_bp = Blueprint('student', __name__, template_folder='templates', static_folder='static')

# IMPORTANT: change these when you deploy to production / use HTTPS
RP_ID = "localhost"
RP_NAME = "CTU Student Voting System"
RP_ORIGIN = f"http://{RP_ID}:5000"

# ------------------- HELPER -------------------
def generate_otp():
    return str(random.randint(100000, 999999))

# ------------------- REGISTER -------------------
@student_bp.route('/register', methods=['GET', 'POST'])
def register():
    from admin.models import Department, Course

    if request.method == 'POST':
        registration_data = {
            "first_name": request.form.get('first_name'),
            "middle_name": request.form.get('middle_name'),
            "last_name": request.form.get('last_name'),
            "suffix": request.form.get('suffix'),
            "username": request.form.get('username'),
            "email": request.form.get('email').strip(),
            "password": request.form.get('password'),

            # 🔹 this now receives course.id from the dropdown
            "course": request.form.get('course'),

            "birth_date": request.form.get('birth_date'),
            "id_number": request.form.get('id_number')
        }

        email = registration_data["email"]
        id_number = registration_data["id_number"]

        # ID number check (UNCHANGED)
        if Student.query.filter(func.trim(Student.id_number) == id_number).first():
            flash("ID Number already registered!", "danger")
            departments = Department.query.order_by(Department.name).all()
            courses_by_department = {
                dept.name: Course.query.filter_by(department_id=dept.id).all()
                for dept in departments
            }
            return render_template('student_register.html', courses_by_department=courses_by_department)

        # Email check (UNCHANGED)
        if Student.query.filter_by(email=email).first():
            flash("Email already registered!", "danger")
            departments = Department.query.order_by(Department.name).all()
            courses_by_department = {
                dept.name: Course.query.filter_by(department_id=dept.id).all()
                for dept in departments
            }
            return render_template('student_register.html', courses_by_department=courses_by_department)

        # ✅ FIXED PART (THIS IS THE IMPORTANT ONE)
        # course now contains course.id
        course_id = registration_data["course"]

        course_obj = Course.query.get(course_id)
        if not course_obj:
            flash("Selected course is invalid.", "danger")
            return redirect(url_for('student.register'))

        # ✅ STORE EVERYTHING OTP NEEDS
        registration_data["course"] = course_obj.course_name     # plain text
        registration_data["course_id"] = course_obj.id
        registration_data["department_id"] = course_obj.department_id

        # OTP logic (UNCHANGED)
        otp = generate_otp()
        session['otp'] = otp
        session['registration_data'] = registration_data

        try:
            msg = Message(
                subject="CTU Registration OTP",
                recipients=[email]
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

            flash('OTP has been sent to your email.', 'info')
            return redirect(url_for('student.verify_otp'))

        except Exception as e:
            flash(f"Failed to send OTP email. Error: {str(e)}", "danger")

    # GET request (UNCHANGED)
    departments = Department.query.order_by(Department.name).all()
    courses_by_department = {
        dept.name: Course.query.filter_by(department_id=dept.id).all()
        for dept in departments
    }
    return render_template('student_register.html', courses_by_department=courses_by_department)



# ------------------- OTP VERIFICATION -------------------
@student_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form.get('otp')

        if entered_otp == session.get('otp'):
            data = session.get('registration_data')

            password_hash = bcrypt.generate_password_hash(
                data.get('password')
            ).decode('utf-8')

            new_student = Student(
                first_name=data.get('first_name'),
                middle_name=data.get('middle_name'),
                last_name=data.get('last_name'),
                suffix=data.get('suffix'),
                username=data.get('username'),
                email=data.get('email'),
                password=password_hash,

                # ✅ NOW EVERYTHING IS STORED
                course=data.get('course'),               # TEXT
                course_id=data.get('course_id'),         # FK
                department_id=data.get('department_id'), # FK

                birth_date=data.get('birth_date'),
                id_number=data.get('id_number')
            )

            db.session.add(new_student)
            db.session.commit()

            session.pop('otp', None)
            session.pop('registration_data', None)

            flash('Registration successful! You may now log in.', 'success')
            return redirect(url_for('student.login'))

        else:
            flash('Invalid OTP.', 'danger')

    return render_template('verify_otp.html')

# ------------------- LOGIN -------------------
@student_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        id_number = request.form.get('id_number', '').strip()
        password = request.form.get('password', '').strip()

        student = Student.query.filter(
            func.lower(Student.email) == email,
            func.trim(Student.id_number) == id_number
        ).first()

        if not student:
            flash("Mismatched Credentials", "danger")
            return render_template('student_login.html')

        if bcrypt.check_password_hash(student.password, password):
            login_user(student)
            flash('Login successful!', 'success')
            return redirect(url_for('student.dashboard'))
        else:
            flash('Incorrect password', 'danger')
            return render_template('student_login.html')

    return render_template('student_login.html')

# ------------------- DASHBOARD -------------------
@student_bp.route('/dashboard')
@login_required
def dashboard():
    total_students = Student.query.count()
    total_votes = Vote.query.count()
    has_voted = Vote.query.filter_by(student_id=current_user.id).first() is not None

    announcements = [
        "Student government elections start on Nov 25.",
        "Voting closes on Nov 30 at 5:00 PM.",
        "Check the candidates' platforms on the voting page."
    ]

    leading_candidates = (
        db.session.query(
            Candidate,
            func.count(Vote.id).label("vote_count")
        )
        .outerjoin(Vote, Candidate.id == Vote.candidate_id)
        .group_by(Candidate.id)
        .order_by(func.count(Vote.id).desc())
        .limit(5)
        .all()
    )

    return render_template(
        'student_dashboard.html',
        total_students=total_students,
        total_votes=total_votes,
        has_voted=has_voted,
        announcements=announcements,
        leading_candidates=leading_candidates
    )

# ------------------- VOTING -------------------
@student_bp.route('/vote', methods=['GET', 'POST'])
@login_required
def vote():
    candidates = Candidate.query.all()
    existing_vote = Vote.query.filter_by(student_id=current_user.id).first()
    if existing_vote:
        flash('You have already voted!', 'info')
        return redirect(url_for('student.receipt'))

    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id')
        candidate = Candidate.query.get(candidate_id)
        if not candidate:
            flash('Please select a valid candidate.', 'danger')
            return redirect(url_for('student.vote'))

        vote = Vote(student_id=current_user.id, candidate_id=candidate.id)
        db.session.add(vote)
        db.session.commit()

        flash('Your vote has been cast! View your voting receipt for details.', 'success')
        return redirect(url_for('student.receipt'))

    return render_template('vote_page.html', candidates=candidates)

# ------------------- AVAILABLE ELECTIONS -------------------


@student_bp.route('/available_elections')
@login_required
def available_elections():
    # Set the timezone to Philippines (UTC+8)
    local_tz = pytz.timezone("Asia/Manila")
    now = datetime.now(local_tz)

    # Filter elections that are currently ongoing
    elections = Election.query.filter(
        Election.start_date <= now,
        Election.end_date >= now
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

# ------------------- PROFILE -------------------
@student_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', student=current_user)

# ------------------- HELP -------------------
@student_bp.route('/help')
@login_required
def help_page():
    faqs = [
        {"q": "How do I vote?", "a": "Go to Available Elections, select candidates, and submit."},
        {"q": "Can I change my vote?", "a": "No — once submitted, votes are final."},
        {"q": "Who to contact for issues?", "a": "Election Committee: comelec@example.edu"}
    ]
    return render_template('help.html', faqs=faqs)

# ------------------- FORGOT PASSWORD -------------------
@student_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        flash(f'Password reset instructions sent to {email}.', 'info')
        return redirect(url_for('student.login'))

    return render_template('forgot_password.html')

# ------------------- LOGOUT -------------------
@student_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
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

# ------------------- BIOMETRIC REGISTRATION CHALLENGE -------------------
@student_bp.route('/bio-register-challenge', methods=['POST'])
@login_required
def bio_register_challenge():
    # Only allow a logged-in user to register a passkey (safe flow)
    if current_user.passkey_id:
        return jsonify({"status": "failed", "message": "You already have a registered biometric login."})

    # Build user and rp entities through helper generate function
    try:
        registration_options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=str(current_user.id),
            user_name=current_user.email,
            user_display_name=f"{current_user.first_name} {current_user.last_name}",
            authenticator_selection={"userVerification": "preferred"}
        )

        # store challenge in session for later verification
        session['webauthn_registration_challenge'] = registration_options.challenge

        # return the JSON options expected by SimpleWebAuthn (camelCase)
        return jsonify({"status": "ok", **options_to_json(registration_options)})

    except Exception as e:
        return jsonify({"status": "failed", "message": str(e)}), 500


# ------------------- BIOMETRIC REGISTRATION VERIFY -------------------
@student_bp.route('/bio-register-verify', methods=['POST'])
@login_required
def bio_register_verify():
    try:
        credential = request.json
        expected_challenge = session.get('webauthn_registration_challenge')
        if not expected_challenge:
            return jsonify({"status": "failed", "message": "No registration challenge found."}), 400

        verification = verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_origin=RP_ORIGIN,
            expected_rp_id=RP_ID
        )

        # Save credential info in user record (Base64URL strings)
        current_user.passkey_id = bytes_to_base64url(verification.credential_id)
        current_user.public_key = bytes_to_base64url(verification.credential_public_key)
        current_user.sign_count = verification.sign_count or 0

        db.session.commit()
        session.pop('webauthn_registration_challenge', None)

        return jsonify({"status": "ok", "message": "Biometric registered!"})

    except Exception as e:
        # return error message (useful during testing)
        return jsonify({"status": "failed", "message": str(e)}), 400


# ------------------- BIOMETRIC LOGIN CHALLENGE -------------------
@student_bp.route('/bio-login-challenge', methods=['POST'])
def bio_login_challenge():
    """
    This endpoint supports two modes:
    - If client sends {"email": "user@example.com"} -> only allow that user's credential (helpful UX)
    - If no email provided -> return a generic authentication challenge (let browser choose passkey)
    """
    data = request.get_json(silent=True) or {}
    email = data.get('email')

    # Build allowCredentials list if we know which student (email supplied)
    allow_credentials = None
    if email:
        student = Student.query.filter(func.lower(Student.email) == email.strip().lower()).first()
        if not student or not student.passkey_id:
            return jsonify({"status": "failed", "message": "No biometric registered for that email."}), 400
        # library expects bytes for credential ids in some implementations - we pass bytes to generator
        try:
            cred_bytes = base64url_to_bytes(student.passkey_id)
            allow_credentials = [cred_bytes]
        except Exception:
            # fallback: pass nothing (some libs accept Base64URL strings)
            allow_credentials = [student.passkey_id]

    try:
        options = generate_authentication_options(
            rp_id=RP_ID,
            allow_credentials=allow_credentials  # may be None
        )

        session['webauthn_auth_challenge'] = options.challenge

        return jsonify({"status": "ok", **options_to_json(options)})

    except Exception as e:
        return jsonify({"status": "failed", "message": str(e)}), 500


# ------------------- BIOMETRIC LOGIN VERIFY -------------------
@student_bp.route('/bio-login-verify', methods=['POST'])
def bio_login_verify():
    data = request.json
    expected_challenge = session.get('webauthn_auth_challenge')
    if not expected_challenge:
        return jsonify({"status": "failed", "message": "No auth challenge in session."}), 400

    # The credential 'id' is base64url string in the client response.
    credential_id = data.get('id') or (data.get('rawId') if data.get('rawId') else None)
    if not credential_id:
        # Try credentialId in nested structure (some clients send different shapes)
        credential_id = data.get('response', {}).get('attestationObject') or data.get('response', {}).get('authenticatorData')

    # Attempt to find student by stored passkey_id
    student = None
    if credential_id:
        # If `rawId` could be bytes array; if bytes, convert to base64url
        try:
            # if it's already a base64url string (common), try direct match
            student = Student.query.filter_by(passkey_id=credential_id).first()
        except Exception:
            student = None

    # If we couldn't find by direct id, attempt to locate by trying to decode rawId if it's bytes-like
    if not student:
        # iterate students with passkey set to find match (slower, but fallback for dev/testing)
        candidates = Student.query.filter(Student.passkey_id.isnot(None)).all()
        for s in candidates:
            if s.passkey_id and credential_id and (credential_id == s.passkey_id):
                student = s
                break

    if not student:
        return jsonify({"status": "failed", "message": "Unknown credential or user not registered."}), 400

    try:
        verification = verify_authentication_response(
            credential=data,
            expected_challenge=expected_challenge,
            expected_rp_id=RP_ID,
            expected_origin=RP_ORIGIN,
            credential_public_key=base64url_to_bytes(student.public_key),
            previous_sign_count=student.sign_count
        )

        # update sign count
        student.sign_count = verification.new_sign_count or student.sign_count
        db.session.commit()

        # log the user in
        login_user(student)

        # clear challenge
        session.pop('webauthn_auth_challenge', None)

        return jsonify({"status": "ok", "message": "Logged in via biometric."})

    except Exception as e:
        return jsonify({"status": "failed", "message": str(e)}), 400
