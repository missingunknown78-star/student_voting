from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session, jsonify, Response
from extensions import db, bcrypt
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime
from functools import wraps
from admin.models import Admin, Candidate, Position, Election, Announcement, Department, Course
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


# ---------------------- Blueprint ---------------------- #
admin_bp = Blueprint('admin', __name__, template_folder='templates', static_folder='static')


# ---------------------- Secure Admin Required Decorator ---------------------- #
# Configure logging for unauthorized attempts
logging.basicConfig(filename='admin_access.log', level=logging.WARNING,
                    format='%(asctime)s - %(message)s')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Track failed attempts per IP
        ip = request.remote_addr
        attempts = session.get(f'admin_attempts_{ip}', 0)
        cooldown = session.get(f'admin_cooldown_{ip}', 0)

        # Check cooldown
        if time.time() < cooldown:
            flash(f"Too many failed attempts. Try again in {int(cooldown - time.time())} seconds.", "admin-warning")
            return redirect(url_for('admin.login'))

        # Check if user is authenticated and admin
        if not current_user.is_authenticated or getattr(current_user, 'user_type', None) != 'admin':
            logging.warning(f"Unauthorized admin access attempt from IP: {ip}")
            
            # Increase failed attempts
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

        # Reset failed attempts on successful admin login
        session[f'admin_attempts_{ip}'] = 0
        session[f'admin_cooldown_{ip}'] = 0

        return f(*args, **kwargs)
    return decorated_function




# ------------------- Configuration ------------------- #
MAX_ATTEMPTS = 3          # max allowed failed username/password attempts
COOLDOWN_TIME = 300       # cooldown in seconds (5 minutes)
MAX_2FA_ATTEMPTS = 5      # max allowed failed 2FA attempts
TWO_FA_COOLDOWN = 300     # cooldown for 2FA in seconds

# ------------------- Admin Login Route ------------------- #
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and getattr(current_user, 'user_type', None) == 'admin':
        return redirect(url_for('admin.dashboard'))

    ip = request.remote_addr
    attempts = session.get(f'login_attempts_{ip}', 0)
    cooldown = session.get(f'login_cooldown_{ip}', 0)

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
        if admin and bcrypt.check_password_hash(admin.password, password):
            # Reset failed attempts
            session[f'login_attempts_{ip}'] = 0
            session[f'login_cooldown_{ip}'] = 0

            # Set session permanent
            session.permanent = True

            # If admin has TOTP secret, require 2FA verification
            if getattr(admin, 'totp_secret', None):
                session['pre_2fa_admin_id'] = admin.id
                return redirect(url_for('admin.verify_2fa'))

            # If no TOTP secret, require 2FA setup first
            else:
                session['pre_2fa_admin_id'] = admin.id
                return redirect(url_for('admin.setup_2fa'))

        else:
            # Increment failed attempts
            attempts += 1
            session[f'login_attempts_{ip}'] = attempts

            if attempts >= MAX_ATTEMPTS:
                session[f'login_cooldown_{ip}'] = time.time() + COOLDOWN_TIME
                session[f'login_attempts_{ip}'] = 0
                error = 'Too many failed attempts. Admin login temporarily locked.'
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
        return render_template('admin_2fa_verify.html', error=error)

    error = None
    if request.method == 'POST':
        code = request.form.get('code')
        totp = pyotp.TOTP(admin.totp_secret)

        if totp.verify(code):
            # ✅ Success: log in the user
            login_user(admin)
            session.permanent = True

            # Cleanup session keys
            session.pop('pre_2fa_admin_id', None)
            session.pop(f'2fa_attempts_{ip}', None)
            session.pop(f'2fa_cooldown_{ip}', None)

            flash("2FA verified. Welcome, Admin.", "success")
            return redirect(url_for('admin.dashboard'))

        else:
            attempts += 1
            session[f'2fa_attempts_{ip}'] = attempts

            if attempts >= MAX_2FA_ATTEMPTS:
                session[f'2fa_cooldown_{ip}'] = time.time() + TWO_FA_COOLDOWN
                session[f'2fa_attempts_{ip}'] = 0
                error = "Too many invalid codes. 2FA temporarily locked."
            else:
                error = f"Invalid code. Attempt {attempts} of {MAX_2FA_ATTEMPTS}."

    return render_template('admin_2fa_verify.html', error=error)



def generate_2fa_secret(admin):
    if not getattr(admin, 'totp_secret', None):
        secret = pyotp.random_base32()
        admin.totp_secret = secret
        db.session.commit()
    return admin.totp_secret

@admin_bp.route('/2fa/setup', methods=['GET', 'POST'])
@admin_required
def setup_2fa():
    admin = current_user
    secret = generate_2fa_secret(admin)
    totp = pyotp.TOTP(secret)
    
    if request.method == 'POST':
        code = request.form.get('code')
        if totp.verify(code):
            admin.is_2fa_enabled = True  # you might need to add this column
            db.session.commit()
            flash("Two-factor authentication enabled!", "success")
            return redirect(url_for('admin.dashboard'))
        else:
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
    # Per-election chart data
    # ================================
    election_data = []

    elections = Election.query.order_by(Election.start_date.desc()).all()
    for e in elections:
        labels = []
        votes = []
        positions = []

        for c in e.candidates:
            labels.append(f"{c.first_name} {c.last_name}")
            votes.append(len(c.votes))
            positions.append(c.position.name if c.position else "Unknown")  # fetch position

        election_data.append({
            "id": e.id,
            "title": e.title,
            "labels": labels,
            "votes": votes,
            "positions": positions  # send positions to JS
        })

    # ================================
    # Recent elections table
    # ================================
    recent_elections_all = elections

    # Localize timezone if naive
    for election in recent_elections_all:
        if election.start_date.tzinfo is None:
            election.start_date = tz.localize(election.start_date)
        if election.end_date.tzinfo is None:
            election.end_date = tz.localize(election.end_date)

    recent_elections = recent_elections_all[:5]
    ongoing_elections = sum(1 for e in recent_elections_all if e.status == 'Open')

    return render_template(
        'admin_dashboard.html',
        admin=current_user,
        total_students=total_students,
        total_candidates=total_candidates,
        total_elections=total_elections,
        ongoing_elections=ongoing_elections,
        total_votes=total_votes,
        elections_json=election_data,
        recent_elections=recent_elections,
        recent_elections_all=recent_elections_all,
        now=now
    )






# ---------------------- MANAGE STUDENTS PAGE (ENHANCED) ---------------------- #
@admin_bp.route('/students')
@admin_required
def manage_students():
    # -------------------- Fetch Departments & Courses -------------------- #
    departments = Department.query.order_by(Department.name).all()
    courses = Course.query.order_by(Course.course_name).all()

    departments_data = [{"id": d.id, "name": d.name} for d in departments]
    courses_data = [{"id": c.id, "name": c.course_name} for c in courses]

    # -------------------- Fetch Elections -------------------- #
    elections = Election.query.order_by(Election.start_date.desc()).all()
    elections_data = [{"id": e.id, "title": e.title} for e in elections]

    # -------------------- Render Template -------------------- #
    return render_template(
        'manage_students.html',
        departments=departments_data,
        courses=courses_data,
        elections=elections_data
    )


# ---------------------- AJAX STUDENT DATA (with voting status) ---------------------- #
@admin_bp.route('/students/data')
@admin_required
def students_data():
    filter_type = request.args.get('filter_type', 'all')
    filter_id = request.args.get('filter_id')
    search = request.args.get('search', '')
    election_id = request.args.get('election_id')  # NEW: get selected election
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
                Student.course.ilike(f'%{search}%')
            )
        )

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

        students.append({
            "id": s.id,
            "id_number": s.id_number,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "course": s.course,
            "year_level": getattr(s, 'year_level', ''),
            "has_voted": has_voted  # NEW: send voting status to frontend
        })

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

    # Row 1: Election Title
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
    ws.cell(row=1, column=1, value=f"{election.title if election else 'All Elections'}")
    ws.cell(row=1, column=1).font = header_font
    ws.cell(row=1, column=1).fill = mustard_fill
    ws.cell(row=1, column=1).alignment = center_alignment

    # Row 2: Department
    department_text = election.department if election and election.department else '-'
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max_col)
    ws.cell(row=2, column=1, value=f"{department_text}")
    ws.cell(row=2, column=1).font = header_font
    ws.cell(row=2, column=1).fill = mustard_fill
    ws.cell(row=2, column=1).alignment = center_alignment

    # Row 3: Course
    course_text = election.course_rel.course_name if election and election.course_rel else '-'
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=max_col)
    ws.cell(row=3, column=1, value=f"{course_text}")
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

        row_values = [
            s.id_number,
            s.first_name,
            s.last_name,
            s.course,
            getattr(s, 'year_level', ''),
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
    db.session.delete(student)
    db.session.commit()
    return jsonify({"success": True})


# ---------------------- EDIT STUDENT ---------------------- #
@admin_bp.route('/students/edit/<int:id>', methods=['POST'])
@admin_required
def edit_student(id):
    student = Student.query.get_or_404(id)

    student.first_name = request.form.get('first_name')
    student.last_name = request.form.get('last_name')
    student.course = request.form.get('course')

    db.session.commit()
    return jsonify({"success": True})


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

    flash('Department added successfully', 'success')
    return redirect(url_for('admin.manage_departments'))  # <-- fixed


@admin_bp.route('/departments/delete-multiple', methods=['POST'])
@admin_required
def delete_multiple_departments():
    ids = request.form.getlist('department_ids')
    if ids:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        cursor = connection.cursor()
        format_strings = ','.join(['%s'] * len(ids))
        cursor.execute(f"DELETE FROM departments WHERE id IN ({format_strings})", tuple(ids))
        connection.commit()
        cursor.close()
        connection.close()
        flash(f'{len(ids)} department(s) deleted successfully!', 'success')
    else:
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
    cursor.close()
    connection.close()

    flash('Course added successfully', 'success')
    return redirect(url_for('admin.manage_departments'))  # <-- fixed


@admin_bp.route('/courses/delete-multiple', methods=['POST'])
@admin_required
def delete_multiple_courses():
    ids = request.form.getlist('course_ids')
    if ids:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        cursor = connection.cursor()
        format_strings = ','.join(['%s'] * len(ids))
        cursor.execute(f"DELETE FROM courses WHERE id IN ({format_strings})", tuple(ids))
        connection.commit()
        cursor.close()
        connection.close()
        flash(f'{len(ids)} course(s) deleted successfully!', 'success')
    else:
        flash('No courses selected for deletion.', 'warning')
    return redirect(url_for('admin.manage_departments'))  # <-- fixed


# ---------------------- Manage Candidates ---------------------- #
@admin_bp.route('/candidates', methods=['GET', 'POST'])
@admin_required
def manage_candidates():
    positions = Position.query.all()
    departments = Department.query.order_by(Department.name).all()
    elections = Election.query.order_by(Election.start_date.desc()).all()

    # ================= FILTER =================
    selected_election_type = request.args.get('election_type', default=None)
    department_id = request.args.get('department_id', type=int)
    selected_department = None

    query = Candidate.query.join(Election, Candidate.election_id == Election.id)

    # Filter by election type
    if selected_election_type:
        query = query.filter(Election.election_type == selected_election_type)

    # Filter by department only if election type is Department
    if selected_election_type == 'Department' and department_id:
        selected_department = Department.query.get(department_id)
        if selected_department:
            query = query.filter(Candidate.department_id == department_id)

    candidates = query.all()
    # ==========================================

    # ---------- ADD CANDIDATE ----------
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        department_id_form = request.form.get('department_id', type=int)
        position_id = request.form.get('position_id')
        election_id = request.form.get('election_id')
        election_type = request.form.get('election_type')

        # Validate required fields
        if not all([first_name, last_name, position_id, election_id, election_type]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('admin.manage_candidates'))

        # Only required if Department election
        if election_type == 'Department' and not department_id_form:
            flash('Department is required for Department Elections.', 'danger')
            return redirect(url_for('admin.manage_candidates'))

        # Save photo if uploaded
        photo_file = request.files.get('photo')
        photo_filename = None
        photo_folder = os.path.join(current_app.root_path, 'admin', 'static', 'images')
        os.makedirs(photo_folder, exist_ok=True)

        if photo_file and photo_file.filename:
            photo_filename = secure_filename(photo_file.filename)
            photo_file.save(os.path.join(photo_folder, photo_filename))

        new_candidate = Candidate(
            first_name=first_name,
            last_name=last_name,
            department_id=department_id_form if election_type == 'Department' else None,
            position_id=position_id,
            election_id=election_id,
            photo=photo_filename
        )

        db.session.add(new_candidate)
        db.session.commit()
        flash('Candidate added successfully!', 'success')
        return redirect(url_for('admin.manage_candidates'))

    # ----------------- Filter elections for modals -----------------
    # Prepare election lists for Add/Edit modal dropdowns
    department_elections = [e for e in elections if e.election_type == 'Department']
    ssg_elections = [e for e in elections if e.election_type == 'SSG']

    return render_template(
        'manage_candidates.html',
        candidates=candidates,
        positions=positions,
        departments=departments,
        elections=elections,  # all elections
        department_elections=department_elections,  # filtered for JS if needed
        ssg_elections=ssg_elections,               # filtered for JS if needed
        selected_department=selected_department,
        selected_election_type=selected_election_type
    )



@admin_bp.route('/candidates/edit/<int:id>', methods=['POST'])
@admin_required
def update_candidate(id):   # 👈 renamed
    candidate = Candidate.query.get_or_404(id)

    candidate.first_name = request.form.get('first_name')
    candidate.last_name = request.form.get('last_name')
    candidate.position_id = request.form.get('position_id')
    candidate.election_id = request.form.get('election_id')

    department_id = request.form.get('department_id')
    department = Department.query.get(department_id)
    candidate.course = department.name if department else candidate.course

    photo_file = request.files.get('photo')
    if photo_file and photo_file.filename:
        filename = secure_filename(photo_file.filename)
        photo_folder = os.path.join(
            current_app.root_path, 'admin', 'static', 'images'
        )
        os.makedirs(photo_folder, exist_ok=True)
        photo_file.save(os.path.join(photo_folder, filename))
        candidate.photo = filename

    db.session.commit()
    flash('Candidate updated successfully!', 'success')
    return redirect(url_for('admin.manage_candidates'))


@admin_bp.route('/candidates/delete/<int:id>')
@admin_required
def delete_candidate(id):
    candidate = Candidate.query.get_or_404(id)
    db.session.delete(candidate)
    db.session.commit()
    flash('Candidate deleted successfully!', 'success')
    return redirect(url_for('admin.manage_candidates'))



# ---------------------- Create Department Election ---------------------- #
@admin_bp.route('/create-department-election', methods=['GET', 'POST'])
@admin_required
def create_department_election():

    # Get all departments
    departments = Department.query.order_by(Department.name).all()

    if request.method == 'POST':
        # ------------------ POST DATA ------------------ #
        title = request.form.get('title', '').strip()
        election_type = request.form.get('election_type', '').strip()
        department_id_str = request.form.get('department_id')
        description = request.form.get('description', '').strip()
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()

        # Convert department_id to int if provided
        department_id = int(department_id_str) if department_id_str else None

        # ------------------ VALIDATION ------------------ #
        if not title or not election_type or not start_date_str or not end_date_str:
            flash('All required fields must be filled.', 'election')
            return redirect(url_for('admin.create_department_election'))

        if election_type == 'Department' and not department_id:
            flash('Department is required for Department Elections.', 'election')
            return redirect(url_for('admin.create_department_election'))

        # ------------------ PARSE DATES ------------------ #
        tz = pytz.timezone('Asia/Manila')
        try:
            start_date = tz.localize(datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M'))
            end_date = tz.localize(datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M'))
        except ValueError:
            flash('Invalid date format.', 'election')
            return redirect(url_for('admin.create_department_election'))

        if end_date <= start_date:
            flash('End date must be later than start date.', 'election')
            return redirect(url_for('admin.create_department_election'))

        # ------------------ DEPARTMENT NAME ------------------ #
        department_name = None
        if election_type == 'Department' and department_id:
            dept_obj = Department.query.get(department_id)
            department_name = dept_obj.name if dept_obj else None

        # ------------------ CREATE ELECTION ------------------ #
        new_election = Election(
            title=title,
            election_type=election_type,
            department_id=department_id,
            department=department_name,
            description=description,
            start_date=start_date,
            end_date=end_date
        )

        db.session.add(new_election)
        db.session.commit()

        flash('Election created successfully!', 'election')
        return redirect(url_for('admin.create_department_election'))

    # ------------------ GET REQUEST ------------------ #
    return render_template('create_department_election.html', departments=departments)




# ---------------------- Manage Positions ---------------------- #
@admin_bp.route('/manage_positions', methods=['GET', 'POST'])
@admin_required
def manage_positions():
    if request.method == 'POST':
        position_name = request.form.get('position_name', '').strip()
        description = request.form.get('description', '').strip()
        if position_name:
            existing = Position.query.filter_by(name=position_name).first()
            if existing:
                flash(f'Position "{position_name}" already exists!', 'warning')
            else:
                new_position = Position(name=position_name, description=description)
                db.session.add(new_position)
                db.session.commit()
                flash(f'Position "{position_name}" added successfully!', 'success')
            return redirect(url_for('admin.manage_positions'))
    positions = Position.query.all()
    return render_template('manage_positions.html', positions=positions)



    # ----------- ANNOUNCEMENTS ROUTE -----------
@admin_bp.route('/announcements', methods=['GET', 'POST'])
@login_required
def announcements():
    departments = Department.query.all()  # For dropdown

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

        return redirect(url_for('admin.announcements'))

    # GET: fetch announcements to display
    announcements_list = Announcement.query.order_by(Announcement.date.desc()).all()

    return render_template('announcements.html', departments=departments, announcements=announcements_list)



@admin_bp.route('/profile')
@login_required
def admin_profile():
    # Ensure only admin user can access
    if current_user.user_type != 'admin':
        return "Unauthorized", 403

    # Get the admin data
    admin = Admin.query.get(current_user.id)

    # Optional: fetch stats
    total_elections = 12  # replace with actual query
    total_votes = 340      # replace with actual query

    return render_template('admin_profile.html', admin=admin,
                           total_elections=total_elections,
                           total_votes=total_votes)





@admin_bp.route('/statistics')
@admin_required
def statistics():
    tz = pytz.timezone('Asia/Manila')
    
    # Get all elections that have ended
    all_elections = Election.query.all()
    past_elections = [e for e in all_elections if e.status == "Ended"]

    election_stats = []
    for election in past_elections:
        candidates = election.candidates  # relationship from your Candidate model

        # Prepare votes per candidate
        votes_per_candidate = {}
        for c in candidates:
            full_name = f"{c.first_name} {c.last_name}"
            votes_per_candidate[full_name] = len(c.votes)

        # Determine winner
        winner = max(votes_per_candidate, key=votes_per_candidate.get) if votes_per_candidate else "No votes"

        election_stats.append({
            'title': election.title,
            'election_type': election.election_type,
            'department': election.department,  # department name
            'course': getattr(election.course_rel, 'name', None) if election.course_rel else None,
            'start_date': election.start_date.strftime('%Y-%m-%d %H:%M'),
            'end_date': election.end_date.strftime('%Y-%m-%d %H:%M'),
            'votes': votes_per_candidate,
            'winner': winner
        })

    # Get all departments for the filter dropdown
    departments = Department.query.order_by(Department.name).all()

    return render_template('statistics.html', 
                           election_stats=election_stats,
                           departments=departments)



# ---------------------- Logout ---------------------- #
@admin_bp.route('/logout')
@admin_required
def logout():
    logout_user()
    flash('Admin has been logged out.', 'info')
    return redirect(url_for('admin.login'))

