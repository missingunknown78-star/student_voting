# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect  # Add this import
from flask import request, redirect, url_for

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()  # Add this line

# Default login view
login_manager.login_view = 'student.login'
login_manager.login_message_category = 'info'

# CUSTOM UNAUTHORIZED REDIRECT
@login_manager.unauthorized_handler
def unauthorized_callback():
    if request.blueprint == 'admin':
        return redirect(url_for('admin.login'))
    else:
        return redirect(url_for('student.login'))