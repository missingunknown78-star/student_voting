from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from extensions import db, bcrypt
from flask_login import login_user, logout_user, current_user
from datetime import datetime
from functools import wraps

from admin.models import Admin, Candidate, Position, Election
from student.models import Student, Vote

import mysql.connector
from settings import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
import pytz  # <-- added for timezone handling

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
            login_user(admin)  # Login
            flash('Admin logged in successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            error = 'Invalid username or password'

    return render_template('admin_login.html', error=error)

# ---------------------- Admin Dashboard ---------------------- #
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    now = datetime.now()  # naive datetime, same type as election.start_date

    total_students = Student.query.count()
    total_candidates = Candidate.query.count()
    total_elections = Election.query.count()
    total_votes = Vote.query.count()

    candidates = Candidate.query.all()
    vote_labels = [f"{c.first_name} {c.last_name}" for c in candidates]
    vote_counts = [len(c.votes) for c in candidates]

    recent_elections = Election.query.order_by(Election.start_date.desc()).limit(5).all()

    # --- Dynamically determine election status ---
    for election in recent_elections:
        if now < election.start_date:
            election.status = 'Upcoming'
        elif now > election.end_date:
            election.status = 'Ended'
        else:
            election.status = 'Open'

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
        now=now  # naive datetime
    )


# ---------------------- Manage Students ---------------------- #
@admin_bp.route('/students')
@admin_required
def manage_students():
    students = Student.query.all()
    return render_template('manage_students.html', students=students)

# ---------------------- Departments & Courses ---------------------- #
@admin_bp.route('/departments')
def manage_departments():
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = connection.cursor(dictionary=True)

    # Get all departments
    cursor.execute("SELECT * FROM departments ORDER BY name")
    departments = cursor.fetchall()

    # Get all courses along with their department
    cursor.execute("""
        SELECT c.*, d.name AS department_name
        FROM courses c
        JOIN departments d ON c.department_id = d.id
        ORDER BY d.name, c.course_name
    """)
    courses = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        'manage_departments.html',
        departments=departments,
        courses=courses
    )

# --- Department routes ---
@admin_bp.route('/departments/add', methods=['POST'])
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
    return redirect(url_for('admin.manage_departments'))

@admin_bp.route('/departments/delete/<int:id>')
def delete_department(id):
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = connection.cursor()
    cursor.execute("DELETE FROM departments WHERE id = %s", (id,))
    connection.commit()
    cursor.close()
    connection.close()

    flash('Department deleted', 'success')
    return redirect(url_for('admin.manage_departments'))

# --- Course routes ---
@admin_bp.route('/courses/add', methods=['POST'])
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
    return redirect(url_for('admin.manage_departments'))

@admin_bp.route('/courses/edit/<int:id>', methods=['POST'])
def edit_course(id):
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
        "UPDATE courses SET course_name = %s, department_id = %s WHERE id = %s",
        (course_name, department_id, id)
    )
    connection.commit()
    cursor.close()
    connection.close()

    flash('Course updated successfully', 'success')
    return redirect(url_for('admin.manage_departments'))

@admin_bp.route('/courses/delete/<int:id>')
def delete_course(id):
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = connection.cursor()
    cursor.execute("DELETE FROM courses WHERE id = %s", (id,))
    connection.commit()
    cursor.close()
    connection.close()

    flash('Course deleted', 'success')
    return redirect(url_for('admin.manage_departments'))

# ---------------------- Manage Candidates ---------------------- #
@admin_bp.route('/candidates')
@admin_required
def manage_candidates():
    candidates = Candidate.query.all()
    return render_template('manage_candidates.html', candidates=candidates)

@admin_bp.route('/candidates/add', methods=['GET', 'POST'])
@admin_required
def add_candidate():
    positions = Position.query.all()
    students = Student.query.all()
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        position_id = request.form.get('position_id')

        new_candidate = Candidate(student_id=student_id, position_id=position_id)
        db.session.add(new_candidate)
        db.session.commit()
        flash('Candidate added successfully!', 'success')
        return redirect(url_for('admin.manage_candidates'))

    return render_template('add_candidate.html', students=students, positions=positions)

@admin_bp.route('/candidates/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_candidate(id):
    candidate = Candidate.query.get_or_404(id)
    positions = Position.query.all()
    students = Student.query.all()
    if request.method == 'POST':
        candidate.student_id = request.form.get('student_id')
        candidate.position_id = request.form.get('position_id')
        db.session.commit()
        flash('Candidate updated successfully!', 'success')
        return redirect(url_for('admin.manage_candidates'))

    return render_template('edit_candidate.html', candidate=candidate, students=students, positions=positions)

@admin_bp.route('/candidates/delete/<int:id>')
@admin_required
def delete_candidate(id):
    candidate = Candidate.query.get_or_404(id)
    db.session.delete(candidate)
    db.session.commit()
    flash('Candidate removed!', 'danger')
    return redirect(url_for('admin.manage_candidates'))

# ---------------------- Create Department Election ---------------------- #
@admin_bp.route('/create-department-election', methods=['GET', 'POST'])
@admin_required
def create_department_election():
    from admin.models import Department, Course  # ensure Course import

    if request.method == 'POST':
        title = request.form.get('title')
        department_name = request.form.get('department')
        description = request.form.get('description')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(end_date, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format!', 'danger')
            return redirect(url_for('admin.create_department_election'))

        new_election = Election(
              title=title,
              department=department_name,
              description=description,
              start_date=start_date,
              end_date=end_date
                )
        db.session.add(new_election)
        db.session.commit()
        flash('Election created successfully!', 'success')
        return redirect(url_for('admin.dashboard'))

    # Fetch departments with their courses
    departments = Department.query.order_by(Department.name).all()
    courses_by_department = {dept: Course.query.filter_by(department_id=dept.id).order_by(Course.course_name).all() for dept in departments}

    return render_template('create_department_election.html', courses_by_department=courses_by_department)

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
