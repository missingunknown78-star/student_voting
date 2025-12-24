# student/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from student.models import Student, Vote
from admin.models import Candidate, Election, Course, Department
from extensions import db, bcrypt, mail
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func, or_
from flask_mail import Message
import hashlib, time, random
from datetime import datetime
import pytz
from student.models import Message  # Make sure you have a Message model
from student.models import LoginHistory
from user_agents import parse  # pip install user-agents








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

    if request.method == 'POST':
        registration_data = {
            "first_name": request.form.get('first_name'),
            "middle_name": request.form.get('middle_name'),
            "last_name": request.form.get('last_name'),
            "suffix": request.form.get('suffix'),
            "username": request.form.get('username'),
            "email": request.form.get('email').strip(),
            "password": request.form.get('password'),
            "course": request.form.get('course'),
            "birth_date": request.form.get('birth_date'),
            "id_number": request.form.get('id_number')
        }

        email = registration_data["email"]
        id_number = registration_data["id_number"]

        if Student.query.filter(func.trim(Student.id_number) == id_number).first():
            flash("ID Number already registered!", "danger")
        elif Student.query.filter_by(email=email).first():
            flash("Email already registered!", "danger")
        else:
            course_id = registration_data["course"]
            course_obj = Course.query.get(course_id)
            if not course_obj:
                flash("Selected course is invalid.", "danger")
                return redirect(url_for('student.register'))

            registration_data["course"] = course_obj.course_name
            registration_data["course_id"] = course_obj.id
            registration_data["department_id"] = course_obj.department_id

            otp = generate_otp()
            session['otp'] = otp
            session['registration_data'] = registration_data

            try:
                msg = Message(subject="CTU Registration OTP", recipients=[email])
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

    departments = Department.query.order_by(Department.name).all()
    courses_by_department = {dept.name: Course.query.filter_by(department_id=dept.id).all() for dept in departments}
    return render_template('student_register.html', courses_by_department=courses_by_department)

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
            session.pop('otp', None)
            session.pop('registration_data', None)
            flash('Registration successful! You may now log in.', 'success')
            return redirect(url_for('student.login'))

        else:
            flash('Invalid OTP.', 'danger')

    return render_template('verify_otp.html')

# ==================== LOGIN (merged traditional + WebAuthn page) ====================
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

            # ---------------- Log login history ----------------
            try:
                

                user_agent = parse(request.headers.get('User-Agent'))

                device_type = "PC"
                if user_agent.is_mobile:
                    device_type = "Mobile"
                elif user_agent.is_tablet:
                    device_type = "Tablet"

                ip = request.remote_addr or "Unknown"
                browser = f"{user_agent.browser.family} {user_agent.browser.version_string}"

                login_record = LoginHistory(
                    user_id=student.id,
                    device=device_type,
                    ip_address=ip,
                    browser=browser
                )
                db.session.add(login_record)
                db.session.commit()
            except Exception as e:
                print("Login history logging failed:", e)
            # ----------------------------------------------------

            return redirect(url_for('student.dashboard'))
        else:
            flash('Incorrect password', 'danger')
            return render_template('student_login.html')

    return render_template('student_login.html')



# ==================== DASHBOARD ====================
@student_bp.route('/dashboard')
@login_required
def dashboard():
    # Total students and votes
    total_students = Student.query.count()
    total_votes = Vote.query.count()
    
    # Check if current student has voted
    has_voted = Vote.query.filter_by(student_id=current_user.id).first() is not None

    # Example announcements (replace with your actual logic)
    announcements = [
        "Student government elections start on Nov 25.",
        "Voting closes on Nov 30 at 5:00 PM.",
        "Check the candidates' platforms on the voting page."
    ]

    # Leading candidates by vote count
    leading_candidates = (
        db.session.query(Candidate, func.count(Vote.id).label("vote_count"))
        .outerjoin(Vote, Candidate.id == Vote.candidate_id)
        .group_by(Candidate.id)
        .order_by(func.count(Vote.id).desc())
        .limit(5)
        .all()
    )

    # Unread messages count for header badge
    unread_count = Message.query.filter_by(sender_id=current_user.id, read=False).count()

    return render_template(
        'student_dashboard.html',
        total_students=total_students,
        total_votes=total_votes,
        has_voted=has_voted,
        announcements=announcements,
        leading_candidates=leading_candidates,
        unread_messages_count=unread_count
    )


# ==================== MESSAGES ====================
from sqlalchemy import or_, and_


@student_bp.route('/messages', methods=['GET', 'POST'])
@login_required
def messages_page():
    if request.method == 'POST':
        content = request.form.get('message')
        if content:
            new_message = Message(
                sender_id=current_user.id,
                receiver='admin',
                content=content,
                read=False
            )
            db.session.add(new_message)
            db.session.commit()
            return redirect(url_for('student.messages_page'))

    # Fetch all messages: student → admin OR admin reply
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver == 'admin'),
            and_(Message.replied != None, Message.receiver == 'student')  # only messages with admin replies
        )
    ).order_by(Message.created_at.asc()).all()

    return render_template('student_messages.html', messages=messages)


from flask_login import login_required, current_user

@student_bp.route('/login-history')
@login_required
def login_history():
    # Use current_user.id instead of session
    history = LoginHistory.query.filter_by(user_id=current_user.id).order_by(LoginHistory.timestamp.desc()).all()
    return render_template('login_history.html', history=history)


# ------------------- VOTING -------------------
from flask import flash, redirect, url_for, render_template, request
from flask_login import login_required, current_user
from datetime import datetime
import pytz
from student.models import Vote
from admin.models import Election, Candidate
from collections import defaultdict


@student_bp.route('/vote/<int:election_id>', methods=['GET', 'POST'])
@login_required
def vote_page(election_id):
    local_tz = pytz.timezone("Asia/Manila")
    now = datetime.now(local_tz).replace(tzinfo=None)

    election = Election.query.filter_by(id=election_id).first()
    if not election:
        flash("Election not found.", "danger")
        return redirect(url_for('student.available_elections'))

    start_date = election.start_date
    end_date = election.end_date

    if not (start_date <= now <= end_date):
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
    candidate_id = request.form.get('candidate_id')
    if not candidate_id:
        flash("Please select a candidate before submitting.", "warning")
        return redirect(url_for('student.vote_page', election_id=election_id))

    # Prevent duplicate voting
    existing_vote = Vote.query.filter_by(student_id=current_user.id, election_id=election_id).first()
    if existing_vote:
        flash("You have already voted in this election.", "info")
        return redirect(url_for('student.available_elections'))

    # Record the vote
    vote = Vote(student_id=current_user.id, candidate_id=candidate_id, election_id=election_id)
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
    fingerprint_registered = bool(current_user.passkey_id)  # True if fingerprint exists
    return render_template('profile.html', student=current_user, fingerprint_registered=fingerprint_registered)

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
def logout():
    if current_user.is_authenticated:
        try:
            # Log the logout in login_history table
            user_agent = parse(request.headers.get('User-Agent'))
            device_type = "PC"
            if user_agent.is_mobile:
                device_type = "Mobile"
            elif user_agent.is_tablet:
                device_type = "Tablet"

            ip = request.remote_addr or "Unknown"
            browser = f"{user_agent.browser.family} {user_agent.browser.version_string}"

            logout_record = LoginHistory(
                user_id=current_user.id,
                device=device_type,
                ip_address=ip,
                browser=browser,
                action="logout"  # optional: you can have an 'action' column
            )
            db.session.add(logout_record)
            db.session.commit()
        except Exception as e:
            print("Logout history logging failed:", e)

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
