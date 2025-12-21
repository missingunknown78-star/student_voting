from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from extensions import db, bcrypt
from flask_login import login_user, logout_user, current_user
from datetime import datetime
from functools import wraps

from admin.models import Admin, Candidate, Position, Election
from student.models import Student, Vote

import mysql.connector
from settings import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
import pytz
from werkzeug.utils import secure_filename
import os
from flask import current_app
from admin.models import Department, Course






# ---------------------- Blueprint ---------------------- #
admin_bp = Blueprint('admin', __name__, template_folder='templates', static_folder='static')

# ---------------------- Admin Required Decorator ---------------------- #
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or getattr(current_user, 'user_type', None) != 'admin':
            flash("Please log in as admin to access this page.", "admin-warning")
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------------- Admin Login ---------------------- #
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and getattr(current_user, 'user_type', None) == 'admin':
        return redirect(url_for('admin.dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        admin = Admin.query.filter_by(username=username).first()
        if admin and bcrypt.check_password_hash(admin.password, password):
            login_user(admin)
            flash('Admin logged in successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            error = 'Invalid username or password'

    return render_template('admin_login.html', error=error)

# ---------------------- Admin Dashboard ---------------------- #
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)

    # KPI counts
    total_students = Student.query.count()
    total_candidates = Candidate.query.count()
    total_elections = Election.query.count()
    total_votes = Vote.query.count()

    # Candidates and votes for charts
    candidates = Candidate.query.all()
    vote_labels = [f"{c.first_name} {c.last_name}" for c in candidates]
    vote_counts = [len(c.votes) for c in candidates]

    # Recent elections
    recent_elections = Election.query.order_by(Election.start_date.desc()).all()

    # Ensure start_date and end_date are timezone-aware
    for election in recent_elections:
        if election.start_date.tzinfo is None:
            election.start_date = tz.localize(election.start_date)
        if election.end_date.tzinfo is None:
            election.end_date = tz.localize(election.end_date)

    # Count ongoing elections using the status property
    ongoing_elections = sum(1 for e in recent_elections if e.status == 'Open')

    return render_template(
        'admin_dashboard.html',
        admin=current_user,
        total_students=total_students,
        total_candidates=total_candidates,
        total_elections=total_elections,
        ongoing_elections=ongoing_elections,
        total_votes=total_votes,
        vote_labels=vote_labels,
        vote_counts=vote_counts,
        recent_elections=recent_elections,
        now=now
    )

# ---------------------- Manage Students ---------------------- #
@admin_bp.route('/students')
@admin_required
def manage_students():
    students = Student.query.all()
    return render_template('manage_students.html', students=students)

# ---------------------- Departments & Courses ---------------------- #
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

#---------------STOP HERE WHEN UNDO-----------------------------------------------------


# ---------------------- Manage Candidates ---------------------- #
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
# ---------------------- Create Department Election ---------------------- #
@admin_bp.route('/create-department-election', methods=['GET', 'POST'])
@admin_required
def create_department_election():
    from admin.models import Department, Election
    from datetime import datetime
    import pytz

    # Get all departments
    departments = Department.query.order_by(Department.name).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        election_type = request.form.get('election_type', '').strip()
        department_id_str = request.form.get('department_id')
        description = request.form.get('description', '').strip()
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()

        # Convert department_id to int if provided
        department_id = int(department_id_str) if department_id_str else None

        # Validation
        if not title or not election_type or not start_date_str or not end_date_str:
            flash('All required fields must be filled.', 'danger')
            return redirect(url_for('admin.create_department_election'))

        if election_type == 'Department' and not department_id:
            flash('Department is required for Department Elections.', 'danger')
            return redirect(url_for('admin.create_department_election'))

        # Parse datetime with timezone
        tz = pytz.timezone('Asia/Manila')
        try:
            start_date = tz.localize(datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M'))
            end_date = tz.localize(datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M'))
        except ValueError:
            flash('Invalid date format.', 'danger')
            return redirect(url_for('admin.create_department_election'))

        if end_date <= start_date:
            flash('End date must be later than start date.', 'danger')
            return redirect(url_for('admin.create_department_election'))

        # Get department name if Department election
        department_name = None
        if election_type == 'Department' and department_id:
            dept_obj = Department.query.get(department_id)
            department_name = dept_obj.name if dept_obj else None
        else:
            # SSG election: no department assigned
            department_id = None
            department_name = None

        # Create the new election
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

        flash('Election created successfully!', 'success')
        return redirect(url_for('admin.create_department_election'))

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

# ---------------------- Logout ---------------------- #
@admin_bp.route('/logout')
@admin_required
def logout():
    logout_user()
    flash('Admin has been logged out.', 'info')
    return redirect(url_for('admin.login'))
