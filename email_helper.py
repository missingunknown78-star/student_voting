# email_helper.py
from flask import current_app

def send_email(recipient, subject, body, mail_instance=None):
    """Smart email sender - works on Railway AND locally"""
    
    # Check if we're on Railway
    if current_app.config.get('USE_RESEND'):
        # Use Resend on Railway
        try:
            import resend
            resend.api_key = current_app.config.get('RESEND_API_KEY')
            
            params = {
                "from": current_app.config.get('RESEND_FROM_EMAIL'),
                "to": [recipient],
                "subject": subject,
                "text": body,
            }
            
            resend.Emails.send(params)
            print(f"✅ Email sent to {recipient} via Resend")
            return True
        except Exception as e:
            print(f"❌ Resend error: {e}")
            return False
    
    else:
        # Use Gmail locally
        try:
            from flask_mail import Message
            if mail_instance:
                msg = Message(subject, recipients=[recipient], body=body)
                mail_instance.send(msg)
            else:
                from extensions import mail
                msg = Message(subject, recipients=[recipient], body=body)
                mail.send(msg)
            print(f"✅ Email sent to {recipient} via Gmail")
            return True
        except Exception as e:
            print(f"❌ Gmail error: {e}")
            return False