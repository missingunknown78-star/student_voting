from flask import Blueprint, render_template, redirect, url_for, flash, request
from extensions import db, bcrypt, login_manager
from admin.models import Admin, Candidate, Position, Election
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime

admin_bp = Blueprint('admin', __name__, template_folder='templates', static_folder='static')

# ------------------ FLASK-LOGIN USER LOADER ------------------ #
@login_manager.user_loader
def load_admin(user_id):
    return Admin.query.get(int(user_id))

# ------------------ ADMIN LOGIN ------------------ #
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        logout_user()

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

# ------------------ ADMIN DASHBOARD ------------------ #
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    from student.models import Student

    total_students = Student.query.count()
    total_candidates = Candidate.query.count()
    total_elections = Election.query.count()

    return render_template(
        'admin_dashboard.html',
        admin=current_user,
        total_students=total_students,
        total_candidates=total_candidates,
        total_elections=total_elections
    )

# ------------------ MANAGE STUDENTS ------------------ #
@admin_bp.route('/students')
@login_required
def manage_students():
    from student.models import Student

    students = Student.query.all()
    return render_template('manage_students.html', students=students)

# ------------------ MANAGE CANDIDATES ------------------ #
@admin_bp.route('/candidates')
@login_required
def manage_candidates():
    candidates = Candidate.query.all()
    return render_template('manage_candidates.html', candidates=candidates)

@admin_bp.route('/candidates/add', methods=['GET', 'POST'])
@login_required
def add_candidate():
    from student.models import Student
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
@login_required
def edit_candidate(id):
    candidate = Candidate.query.get_or_404(id)
    from student.models import Student
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
@login_required
def delete_candidate(id):
    candidate = Candidate.query.get_or_404(id)
    db.session.delete(candidate)
    db.session.commit()
    flash('Candidate removed!', 'danger')
    return redirect(url_for('admin.manage_candidates'))

# ------------------ CREATE DEPARTMENT ELECTION ------------------ #
@admin_bp.route('/create-department-election', methods=['GET', 'POST'])
@login_required
def create_department_election():
    if request.method == 'POST':
        title = request.form.get('title')
        department = request.form.get('department')
        description = request.form.get('description')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(end_date, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format!', 'danger')
            return redirect(url_for('admin.create_department_election'))

        new_election = Election(title=title, department=department, description=description, start_date=start_date, end_date=end_date)
        db.session.add(new_election)
        db.session.commit()
        flash('Election created successfully!', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('create_department_election.html')

# ------------------- MANAGE POSITIONS ------------------- #
@admin_bp.route('/manage_positions', methods=['GET', 'POST'])
@login_required
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

# ------------------ LOGOUT ------------------ #
@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Admin has been logged out.', 'info')
    return redirect(url_for('admin.login'))
