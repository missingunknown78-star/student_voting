# student/utils.py
import hashlib
from flask import request
from student.models import TrustedDevice
from flask_mail import Message
from extensions import mail, db
from flask import url_for
import secrets
from datetime import datetime
import socket

# Set default timeout for all socket connections
socket.setdefaulttimeout(30)

def generate_device_fingerprint():
    """
    Generate a consistent device fingerprint from request data
    """
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


def generate_verification_token():
    return secrets.token_urlsafe(32)


def send_new_device_email(student, trusted_device):
    """Send email when new device is detected"""
    import socket
    socket.setdefaulttimeout(30)

    token = generate_verification_token()
    trusted_device.verification_token = token
    trusted_device.verification_sent_at = datetime.utcnow()  # store timestamp
    db.session.commit()

    # YES button → confirm device
    confirm_url = url_for('student.confirm_device', token=token, _external=True)
    # NO button → reject device
    deny_url = url_for('student.reject_device', token=token, _external=True)

    msg = Message(
        subject="New Device Login Verification",
        recipients=[student.email],
        html=f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; padding: 20px; background-color: #f4f6fb;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                <h2 style="color: #1f2937;">New Device Detected 🔒</h2>
                <p style="color: #4b5563; font-size: 16px; line-height: 1.5;">
                    Hello {student.first_name},<br>
                    We detected a login from a new device. Was this you?
                </p>
                
                <p style="color: #6b7280; font-size: 14px; margin: 15px 0;">
                    <strong>Device details:</strong><br>
                    IP: {trusted_device.ip_address}<br>
                    Browser: {trusted_device.browser[:50]}...
                </p>

                <!-- Buttons container -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin: 25px auto;">
                    <tr>
                        <td style="padding: 5px;">
                            <a href="{confirm_url}" style="
                                display: inline-block;
                                padding: 12px 25px;
                                background-color: #10b981;
                                color: #ffffff;
                                text-decoration: none;
                                border-radius: 6px;
                                font-weight: 600;
                                box-shadow: 0 2px 6px rgba(0,0,0,0.15);
                            ">✅ Yes, it's me</a>
                        </td>
                        <td style="padding: 5px;">
                            <a href="{deny_url}" style="
                                display: inline-block;
                                padding: 12px 25px;
                                background-color: #ef4444;
                                color: #ffffff;
                                text-decoration: none;
                                border-radius: 6px;
                                font-weight: 600;
                                box-shadow: 0 2px 6px rgba(0,0,0,0.15);
                            ">❌ No, it's not me</a>
                        </td>
                    </tr>
                </table>

                <p style="color: #6b7280; font-size: 14px; line-height: 1.4;">
                    This link will expire in 15 minutes.<br>
                    If this wasn't you, click "No, it's not me" to secure your account.
                </p>
            </div>
        </div>
        """
    )
    try:
        mail.send(msg)
        print(f"📧 Verification email sent to {student.email}")
    except Exception as e:
        print(f"❌ Failed to send device verification email: {e}")