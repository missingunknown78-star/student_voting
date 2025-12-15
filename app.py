from flask import Flask
from settings import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB, SECRET_KEY
from extensions import db, bcrypt, login_manager, mail

# Initialize Flask app
app = Flask(__name__)

# ---------------------- Configuration ---------------------- #
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Gmail SMTP for OTP
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'ctucomelecprototype@gmail.com'
app.config['MAIL_PASSWORD'] = 'gnro zcog eqpo ggcc'  # Gmail App Password
app.config['MAIL_DEFAULT_SENDER'] = 'ctucomelecprototype@gmail.com'

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
    """
    Load a user from Admin or Student table.
    """
    admin = Admin.query.get(int(user_id))
    if admin:
        return admin

    student = Student.query.get(int(user_id))
    if student:
        return student

    return None

# ---------------------- Register Blueprints ---------------------- #
from admin.routes import admin_bp
from student.routes import student_bp

app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(student_bp, url_prefix='/student')

# ---------------------- Run App ---------------------- #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
