from flask import Flask, redirect, url_for
from settings import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB, SECRET_KEY
from extensions import db, bcrypt, login_manager, mail
from datetime import timedelta


# ---------------------- Initialize Flask app ---------------------- #
app = Flask(__name__)

# ---------------------- Configuration ---------------------- #
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False



# ---- Session Security ----
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=20)

# ---------------------- Mail Configuration ---------------------- #
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'ctucomelecprototype@gmail.com'
app.config['MAIL_PASSWORD'] = 'gnro zcog eqpo ggcc'  # ⚠️ move to env variable later
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
    admin = db.session.get(Admin, int(user_id))
    if admin:
        return admin

    student = Student.query.get(int(user_id))
    if student:
        return student

    return None

# ---------------------- Root Route (FIXED) ---------------------- #
@app.route('/')
def index():
    # Redirect users to student login by default
    return redirect(url_for('student.login'))

# ---------------------- Register Blueprints ---------------------- #
from admin.routes import admin_bp
from student.routes import student_bp

app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(student_bp, url_prefix='/student')

# ---------------------- Run App (LOCAL ONLY) ---------------------- #
if __name__ == '__main__':
    app.run(debug=True)
