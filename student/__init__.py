from flask_login import LoginManager
from app import login_manager

# Import Student model locally to avoid circular imports
from .models import Student

@login_manager.user_loader
def load_student(user_id):
    return Student.query.get(int(user_id))
