# student/__init__.py
from flask import Blueprint

# Define the student blueprint
student_bp = Blueprint('student_bp', __name__)

# DO NOT import app or login_manager here
# Routes will be imported in app.py or inside functions to avoid circular imports
