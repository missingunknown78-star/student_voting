from flask import Flask, redirect, url_for
import os
from dotenv import load_dotenv

load_dotenv()

from settings import SECRET_KEY, DATABASE_URL, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USE_SSL, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER
from extensions import db, bcrypt, login_manager, mail, csrf
from datetime import timedelta

# ---------------------- Initialize Flask app ---------------------- #
app = Flask(__name__)

# ---------------------- Configuration ---------------------- #
app.config['SECRET_KEY'] = SECRET_KEY

# Database configuration - works with Railway MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ---- CSRF Configuration ----
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = SECRET_KEY
app.config['WTF_CSRF_TIME_LIMIT'] = 3600
app.config['WTF_CSRF_SSL_STRICT'] = False

# ---- Session Security ----
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=20)

# ---------------------- Mail Configuration ---------------------- #
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER
app.config['MAIL_TIMEOUT'] = 30
app.config['MAIL_MAX_EMAILS'] = None

# ---------------------- Initialize Extensions ---------------------- #
db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)
mail.init_app(app)
csrf.init_app(app)

# ---------------------- Import Models ---------------------- #
from student.models import Student
from admin.models import Admin, Election

# ---------------------- Flask-Login User Loader ---------------------- #
@login_manager.user_loader
def load_user(user_id):
    admin = db.session.get(Admin, int(user_id))
    if admin:
        return admin
    student = Student.query.get(int(user_id))
    if student:
        return student
    return None

# ---------------------- Root Route ---------------------- #
@app.route('/')
def index():
    return redirect(url_for('student.login'))

# ---------------------- Register Blueprints ---------------------- #
from admin.routes import admin_bp
from student.routes import student_bp

app.register_blueprint(admin_bp, url_prefix='/ctumoalboal-comelec')
app.register_blueprint(student_bp, url_prefix='/student')

# ---------------------- Database Setup ---------------------- #
with app.app_context():
    db.create_all()

# ---------------------- Run App ---------------------- #
if __name__ == '__main__':
    app.run(debug=True)