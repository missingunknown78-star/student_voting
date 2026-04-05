from flask import Flask, redirect, url_for
import os
from dotenv import load_dotenv

load_dotenv()

from settings import SECRET_KEY, DATABASE_URL, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USE_SSL, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER
from extensions import db, bcrypt, login_manager, mail  
from datetime import timedelta
from sqlalchemy.pool import NullPool

# ---------------------- Initialize Flask app ---------------------- #
app = Flask(__name__)

# ---------------------- Configuration ---------------------- #
app.config['SECRET_KEY'] = SECRET_KEY

# Database configuration - WITH CONNECTION POOL FIXES FOR PYTHONANYWHERE
ON_PYTHONANYWHERE = 'PYTHONANYWHERE_DOMAIN' in os.environ

if ON_PYTHONANYWHERE:
    # Use NullPool to avoid connection timeouts
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': NullPool,  # Don't keep connections alive
        'pool_pre_ping': True,   # Check connection before using
        'pool_recycle': 280,      # Recycle connections every 280 seconds
        'connect_args': {
            'connect_timeout': 10,
            'read_timeout': 30,
            'write_timeout': 30
        }
    }
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ---- Proxy Fix for PythonAnywhere (CRITICAL!) ----
if ON_PYTHONANYWHERE:
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_for=1)
    print("✅ PythonAnywhere ProxyFix applied")

# ---- Session Security ----
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=20)

# ---- PythonAnywhere Session Fixes ----
if ON_PYTHONANYWHERE:
    # Fix for proxy/HTTPS
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_DOMAIN'] = None
    
    # Also ensure REMEMBER_COOKIE works
    app.config['REMEMBER_COOKIE_SECURE'] = True
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)

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