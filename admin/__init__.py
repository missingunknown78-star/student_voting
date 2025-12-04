from flask_login import LoginManager
from .models import Admin
from app import login_manager, db

@login_manager.user_loader
def load_admin(user_id):
    return Admin.query.get(int(user_id))
