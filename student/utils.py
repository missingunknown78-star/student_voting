import hashlib
from flask import request
from student.models import TrustedDevice
from flask_mail import Message
from extensions import mail, db
from flask import url_for
import secrets

def generate_device_fingerprint():
    raw_data = (
        request.headers.get('User-Agent', '') +
        request.headers.get('Accept-Language', '') +
        request.remote_addr
    )
    return hashlib.sha256(raw_data.encode()).hexdigest()


def is_device_trusted(student_id):
    fingerprint = generate_device_fingerprint()

    return TrustedDevice.query.filter_by(
        student_id=student_id,
        device_fingerprint=fingerprint,
        trusted=True
    ).first()



# student/utils.py (or student/email.py)

def generate_verification_token():
    return secrets.token_urlsafe(32)

def send_new_device_email(student, trusted_device):
    token = generate_verification_token()
    trusted_device.verification_token = token
    db.session.commit()

    verify_url = url_for('student.verify_device_email', token=token, _external=True)

    msg = Message(
        subject="New Device Login Verification",
        recipients=[student.email],
        html=f"""
        <p>Hello {student.first_name},</p>
        <p>We detected a login from a new device. Was this you?</p>
        <a href="{verify_url}" style="padding:10px 20px;background:#4a90e2;color:white;text-decoration:none;border-radius:5px;">Yes, it’s me</a>
        <p>If this wasn’t you, please ignore this email.</p>
        """
    )
    try:
        mail.send(msg)
    except Exception as e:
        print("Failed to send device verification email:", e)
