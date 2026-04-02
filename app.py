from flask import Flask, redirect, url_for
import os
from dotenv import load_dotenv

load_dotenv()

from settings import SECRET_KEY, DATABASE_URL, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USE_SSL, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER, USE_RESEND, RESEND_API_KEY, RESEND_FROM_EMAIL
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

# ---------------------- Mail Configuration (Updated) ---------------------- #
# Regular Flask-Mail config (for local development)
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER
app.config['MAIL_TIMEOUT'] = 30  # Reduced timeout
app.config['MAIL_MAX_EMAILS'] = None

# ---------------------- Resend Configuration (for Railway) ---------------------- #
app.config['USE_RESEND'] = USE_RESEND
app.config['RESEND_API_KEY'] = RESEND_API_KEY
app.config['RESEND_FROM_EMAIL'] = RESEND_FROM_EMAIL

# Print which email service is being used
if USE_RESEND:
    print("=" * 50)
    print("📧 Using Resend for email (Railway HTTPS API)")
    print(f"   API Key: {'✅ Set' if RESEND_API_KEY else '❌ Missing'}")
    print(f"   From Email: {RESEND_FROM_EMAIL}")
    print("=" * 50)
else:
    print("📧 Using Gmail SMTP for email (Local Development)")

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

# ---------------------- DEBUG ROUTES FOR TESTING ---------------------- #

@app.route('/debug-email')
def debug_email():
    """Test email configuration and sending"""
    try:
        # Show current email config
        config_info = {
            'MAIL_SERVER': app.config.get('MAIL_SERVER'),
            'MAIL_PORT': app.config.get('MAIL_PORT'),
            'MAIL_USE_TLS': app.config.get('MAIL_USE_TLS'),
            'MAIL_USE_SSL': app.config.get('MAIL_USE_SSL'),
            'MAIL_USERNAME': app.config.get('MAIL_USERNAME'),
            'MAIL_PASSWORD': 'SET' if app.config.get('MAIL_PASSWORD') else 'NOT SET',
            'MAIL_DEFAULT_SENDER': app.config.get('MAIL_DEFAULT_SENDER'),
            'MAIL_TIMEOUT': app.config.get('MAIL_TIMEOUT'),
            'USE_RESEND': app.config.get('USE_RESEND'),
            'RESEND_API_KEY': 'SET' if app.config.get('RESEND_API_KEY') else 'NOT SET',
        }
        
        # Try to send a test email
        from flask_mail import Message
        msg = Message('Test Email from Railway',
                      recipients=['ctucomelecprototype@gmail.com'],  # Send to yourself
                      body=f'This is a test email from your Railway app\n\nConfig: {config_info}')
        mail.send(msg)
        
        return f"✅ Test email sent successfully!<br><br>Config: {config_info}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}<br><br>Config: {config_info}"

@app.route('/test-resend')
def test_resend():
    """Test Resend email sending (for Railway)"""
    if not app.config.get('USE_RESEND'):
        return "❌ Resend is not configured. Set USE_RESEND=True in settings"
    
    try:
        from email_helper import send_email
        
        result = send_email(
            recipient='ctucomelecprototype@gmail.com',
            subject='Resend Test from Railway',
            body='If you receive this, Resend is working on Railway!'
        )
        
        if result:
            return "✅ Resend test email sent successfully! Check your inbox."
        else:
            return "❌ Resend test failed. Check logs for details."
    except Exception as e:
        return f"❌ Resend error: {str(e)}"

@app.route('/test-gmail-connection')
def test_gmail():
    """Test if Railway can connect to Gmail"""
    import socket
    import smtplib
    
    results = []
    results.append("<h3>Testing Gmail Connection from Railway</h3>")
    
    # Test DNS resolution
    try:
        ip = socket.gethostbyname('smtp.gmail.com')
        results.append(f"✅ DNS resolved: smtp.gmail.com -> {ip}")
    except Exception as e:
        results.append(f"❌ DNS failed: {e}")
    
    # Test port 587 connection (TLS)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex(('smtp.gmail.com', 587))
        sock.close()
        if result == 0:
            results.append("✅ Port 587 (TLS) is reachable")
        else:
            results.append(f"❌ Port 587 (TLS) is blocked (error: {result})")
    except Exception as e:
        results.append(f"❌ Port 587 test failed: {e}")
    
    # Test port 465 connection (SSL)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex(('smtp.gmail.com', 465))
        sock.close()
        if result == 0:
            results.append("✅ Port 465 (SSL) is reachable")
        else:
            results.append(f"❌ Port 465 (SSL) is blocked (error: {result})")
    except Exception as e:
        results.append(f"❌ Port 465 test failed: {e}")
    
    # Test actual SMTP connection on port 587
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.starttls()
        results.append("✅ SMTP connection on port 587 successful")
        server.quit()
    except Exception as e:
        results.append(f"❌ SMTP connection on port 587 failed: {e}")
    
    return "<br>".join(results)

@app.route('/test-simple-email')
def test_simple_email():
    """Simple email test without Flask-Mail"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = 'ctucomelecprototype@gmail.com'
        msg['Subject'] = 'Simple Test Email from Railway'
        
        body = "This is a test email sent directly with smtplib"
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect and send
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], timeout=30)
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        
        return "✅ Simple email sent successfully using smtplib!"
    except Exception as e:
        return f"❌ Simple email failed: {str(e)}"

# ---------------------- Register Blueprints ---------------------- #
from admin.routes import admin_bp
from student.routes import student_bp

app.register_blueprint(admin_bp, url_prefix='/ctumoalboal-comelec')
app.register_blueprint(student_bp, url_prefix='/student')

# ---------------------- Database Setup & Auto-Import (ONLY ONCE) ---------------------- #
with app.app_context():
    try:
        # Create tables if they don't exist
        db.create_all()
        print("=" * 50)
        print("✅ Database tables created/verified!")
        print("=" * 50)
        
        # Check if we've already imported data
        import_flag_file = 'import_done.txt'
        import_already_done = os.path.exists(import_flag_file)
        
        if not import_already_done:
            from sqlalchemy import text
            student_count = Student.query.count()
            
            if student_count == 0:
                print("📀 Database is empty. Importing your data...")
                print("-" * 50)
                
                # Check if SQL file exists
                sql_file = 'student_voting.sql'
                if os.path.exists(sql_file):
                    with open(sql_file, 'r', encoding='utf-8') as f:
                        sql_content = f.read()
                    
                    commands = sql_content.split(';')
                    imported = 0
                    errors = 0
                    
                    for cmd in commands:
                        cmd = cmd.strip()
                        # ONLY RUN INSERT COMMANDS (skip CREATE, ALTER, DROP, etc.)
                        if cmd and not cmd.startswith('--') and cmd.upper().startswith('INSERT'):
                            try:
                                db.session.execute(text(cmd))
                                imported += 1
                                if imported % 50 == 0:
                                    print(f"   ... {imported} data rows inserted")
                            except Exception as e:
                                errors += 1
                                if errors < 10:
                                    print(f"   ⚠️ Skip: {str(e)[:60]}")
                    
                    db.session.commit()
                    print("-" * 50)
                    print(f"✅ IMPORT COMPLETE!")
                    print(f"   📊 {imported} data rows inserted")
                    print(f"   📊 {Student.query.count()} students imported")
                    print("=" * 50)
                    
                    # Mark import as done
                    with open(import_flag_file, 'w') as f:
                        f.write('done')
                    print("✅ Import flag set - will not import again on restart")
                else:
                    print(f"⚠️ SQL file not found: {sql_file}")
                    print("   Your database is empty. Please add data through admin panel.")
            else:
                print(f"✅ Database already has {student_count} students.")
                print("   Skipping import to avoid duplicates.")
                # Mark import as done even if data exists
                with open(import_flag_file, 'w') as f:
                    f.write('done')
        else:
            print(f"✅ Import already completed previously. Skipping.")
            
    except Exception as e:
        print(f"⚠️ Database setup error: {e}")

# ---------------------- Run App ---------------------- #
if __name__ == '__main__':
    app.run(debug=True)