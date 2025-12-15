# student/__init__.py
from flask import Blueprint

student_bp = Blueprint('student_bp', __name__)

# Import routes only
from . import routes
