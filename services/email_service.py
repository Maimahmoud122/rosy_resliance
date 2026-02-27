from flask_mail import Message
from app import mail


# ══════════════════════════════════════════════════════════
#  SEND VERIFICATION CODE — used by both patient and doctor
# ══════════════════════════════════════════════════════════

def send_verification_email(user_email, full_name, code):
    msg = Message(
        subject    = "Your Email Verification Code",
        recipients = [user_email]
    )

    msg.body = f"Hi {full_name}, your verification code is: {code}. It expires in 10 minutes."

    msg.html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0; padding:0; background-color:#f9fafb; font-family: Arial, sans-serif;">
        <div style="max-width:480px; margin:40px auto; background:#ffffff;
                    border-radius:12px; overflow:hidden;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <div style="background:#be185d; padding:32px; text-align:center;">
                <h1 style="color:#ffffff; margin:0; font-size:22px;">Email Verification</h1>
            </div>
            <div style="padding:32px;">
                <p style="color:#374151;">Hi <strong>{full_name}</strong>,</p>
                <p style="color:#6b7280;">Use the code below to verify your email address:</p>
                <div style="background:#fdf2f8; border:2px dashed #be185d;
                            border-radius:10px; padding:28px; text-align:center; margin:28px 0;">
                    <span style="font-size:42px; font-weight:bold;
                                 letter-spacing:14px; color:#be185d;">{code}</span>
                </div>
                <p style="color:#6b7280; font-size:13px;">⏱ Expires in <strong>10 minutes</strong>.</p>
                <p style="color:#6b7280; font-size:13px;">If you did not create an account, ignore this email.</p>
            </div>
            <div style="background:#f3f4f6; padding:16px; text-align:center;">
                <p style="color:#9ca3af; font-size:12px; margin:0;">Automated message — do not reply.</p>
            </div>
        </div>
    </body>
    </html>
    """
    mail.send(msg)


# ══════════════════════════════════════════════════════════
#  DOCTOR PENDING APPROVAL — sent after email is verified
# ══════════════════════════════════════════════════════════

def send_doctor_pending_email(user_email, full_name):
    msg = Message(
        subject    = "Your Account is Under Review",
        recipients = [user_email]
    )

    msg.body = f"Hi Dr. {full_name}, your email has been verified. Your account is now pending admin approval. We will notify you once reviewed."

    msg.html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0; padding:0; background-color:#f9fafb; font-family: Arial, sans-serif;">
        <div style="max-width:480px; margin:40px auto; background:#ffffff;
                    border-radius:12px; overflow:hidden;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <div style="background:#be185d; padding:32px; text-align:center;">
                <h1 style="color:#ffffff; margin:0; font-size:22px;">Account Under Review</h1>
            </div>
            <div style="padding:32px;">
                <p style="color:#374151;">Hi <strong>Dr. {full_name}</strong>,</p>
                <p style="color:#6b7280;">
                    Your email has been verified successfully. Your account is now
                    <strong>pending admin approval</strong>.
                </p>
                <div style="background:#fdf2f8; border-left:4px solid #be185d;
                            padding:16px; margin:24px 0; border-radius:4px;">
                    <p style="color:#be185d; margin:0; font-weight:bold;">⏳ What happens next?</p>
                    <p style="color:#6b7280; margin:8px 0 0 0; font-size:14px;">
                        Our admin team will review your credentials and verify your account.
                        You will receive an email once the review is complete.
                    </p>
                </div>
                <p style="color:#6b7280; font-size:13px;">
                    This process typically takes 1–2 business days.
                </p>
            </div>
            <div style="background:#f3f4f6; padding:16px; text-align:center;">
                <p style="color:#9ca3af; font-size:12px; margin:0;">Automated message — do not reply.</p>
            </div>
        </div>
    </body>
    </html>
    """
    mail.send(msg)


# ══════════════════════════════════════════════════════════
#  DOCTOR APPROVED — sent when admin approves
# ══════════════════════════════════════════════════════════

def send_doctor_approved_email(user_email, full_name):
    msg = Message(
        subject    = "Your Account Has Been Approved!",
        recipients = [user_email]
    )

    msg.body = f"Congratulations Dr. {full_name}! Your account has been approved. You can now log in."

    msg.html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0; padding:0; background-color:#f9fafb; font-family: Arial, sans-serif;">
        <div style="max-width:480px; margin:40px auto; background:#ffffff;
                    border-radius:12px; overflow:hidden;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <div style="background:#15803d; padding:32px; text-align:center;">
                <h1 style="color:#ffffff; margin:0; font-size:22px;">Account Approved ✓</h1>
            </div>
            <div style="padding:32px;">
                <p style="color:#374151;">Congratulations <strong>Dr. {full_name}</strong>!</p>
                <p style="color:#6b7280;">
                    Your account has been reviewed and <strong>approved</strong>.
                    You can now log in and access all clinical features.
                </p>
                <div style="text-align:center; margin:32px 0;">
                    <a href="http://localhost:3000/login"
                       style="background:#15803d; color:#ffffff; padding:14px 32px;
                              border-radius:8px; text-decoration:none; font-weight:bold;">
                        Log In Now
                    </a>
                </div>
            </div>
            <div style="background:#f3f4f6; padding:16px; text-align:center;">
                <p style="color:#9ca3af; font-size:12px; margin:0;">Automated message — do not reply.</p>
            </div>
        </div>
    </body>
    </html>
    """
    mail.send(msg)


# ══════════════════════════════════════════════════════════
#  DOCTOR REJECTED — sent when admin rejects
# ══════════════════════════════════════════════════════════

def send_doctor_rejected_email(user_email, full_name, reason=None):
    msg = Message(
        subject    = "Account Verification Update",
        recipients = [user_email]
    )

    reason_text = reason if reason else "Your credentials could not be verified at this time."

    msg.body = f"Hi Dr. {full_name}, unfortunately your account could not be approved. Reason: {reason_text}"

    msg.html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0; padding:0; background-color:#f9fafb; font-family: Arial, sans-serif;">
        <div style="max-width:480px; margin:40px auto; background:#ffffff;
                    border-radius:12px; overflow:hidden;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <div style="background:#b91c1c; padding:32px; text-align:center;">
                <h1 style="color:#ffffff; margin:0; font-size:22px;">Verification Update</h1>
            </div>
            <div style="padding:32px;">
                <p style="color:#374151;">Hi <strong>Dr. {full_name}</strong>,</p>
                <p style="color:#6b7280;">
                    Unfortunately, we were unable to approve your account at this time.
                </p>
                <div style="background:#fef2f2; border-left:4px solid #b91c1c;
                            padding:16px; margin:24px 0; border-radius:4px;">
                    <p style="color:#b91c1c; margin:0; font-weight:bold;">Reason:</p>
                    <p style="color:#6b7280; margin:8px 0 0 0; font-size:14px;">{reason_text}</p>
                </div>
                <p style="color:#6b7280; font-size:13px;">
                    If you believe this is a mistake, please contact our support team.
                </p>
            </div>
            <div style="background:#f3f4f6; padding:16px; text-align:center;">
                <p style="color:#9ca3af; font-size:12px; margin:0;">Automated message — do not reply.</p>
            </div>
        </div>
    </body>
    </html>
    """
    mail.send(msg)





    #  PASSWORD RESET EMAILS
# ══════════════════════════════════════════════════════════

def send_password_reset_email(user_email, full_name, code):
    msg = Message(subject="Password Reset Code", recipients=[user_email])
    msg.body = f"Hi {full_name}, your password reset code is: {code}. It expires in 15 minutes."
    msg.html = f"""
    <!DOCTYPE html><html>
    <body style="margin:0;padding:0;background:#f9fafb;font-family:Arial,sans-serif;">
    <div style="max-width:480px;margin:40px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.08);">
        <div style="background:#7c3aed;padding:32px;text-align:center;">
            <h1 style="color:#fff;margin:0;font-size:22px;">Password Reset</h1>
        </div>
        <div style="padding:32px;">
            <p style="color:#374151;">Hi <strong>{full_name}</strong>,</p>
            <p style="color:#6b7280;">We received a request to reset your password. Use the code below:</p>
            <div style="background:#f5f3ff;border:2px dashed #7c3aed;border-radius:10px;padding:28px;text-align:center;margin:28px 0;">
                <span style="font-size:42px;font-weight:bold;letter-spacing:14px;color:#7c3aed;">{code}</span>
            </div>
            <p style="color:#6b7280;font-size:13px;">⏱ Expires in <strong>15 minutes</strong>.</p>
            <p style="color:#6b7280;font-size:13px;">If you did not request a password reset, ignore this email. Your password will not change.</p>
        </div>
        <div style="background:#f3f4f6;padding:16px;text-align:center;">
            <p style="color:#9ca3af;font-size:12px;margin:0;">Automated message — do not reply.</p>
        </div>
    </div>
    </body></html>
    """
    mail.send(msg)


def send_password_changed_email(user_email, full_name):
    msg = Message(subject="Your Password Has Been Changed", recipients=[user_email])
    msg.body = f"Hi {full_name}, your password has been successfully changed. If you did not do this, contact support immediately."
    msg.html = f"""
    <!DOCTYPE html><html>
    <body style="margin:0;padding:0;background:#f9fafb;font-family:Arial,sans-serif;">
    <div style="max-width:480px;margin:40px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.08);">
        <div style="background:#0369a1;padding:32px;text-align:center;">
            <h1 style="color:#fff;margin:0;font-size:22px;">Password Changed</h1>
        </div>
        <div style="padding:32px;">
            <p style="color:#374151;">Hi <strong>{full_name}</strong>,</p>
            <p style="color:#6b7280;">Your password has been <strong>successfully changed</strong>.</p>
            <div style="background:#f0f9ff;border-left:4px solid #0369a1;padding:16px;margin:24px 0;border-radius:4px;">
                <p style="color:#0369a1;margin:0;font-weight:bold;">⚠️ Wasn't you?</p>
                <p style="color:#6b7280;margin:8px 0 0 0;font-size:14px;">If you did not make this change, please contact our support team immediately to secure your account.</p>
            </div>
        </div>
        <div style="background:#f3f4f6;padding:16px;text-align:center;">
            <p style="color:#9ca3af;font-size:12px;margin:0;">Automated message — do not reply.</p>
        </div>
    </div>
    </body></html>
    """
    mail.send(msg)