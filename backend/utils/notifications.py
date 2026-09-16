"""Email notification service for Smart Campus.

Uses standard library smtplib to send transactional emails.
If SMTP credentials are not configured in .env, notifications are
gracefully simulated in the application log so the application never crashes.
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def send_email_notification(to_email, subject, body_text, body_html=None):
    """Send an email notification.

    Falls back to logging if SMTP is not configured.
    """
    if not to_email:
        return False

    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_from = os.getenv('SMTP_FROM', smtp_user or 'noreply@smartcampus.local')
    use_tls = os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'

    # Fallback simulation if SMTP is not set up
    if not smtp_server or not smtp_user:
        logger.info(
            "📧 [Simulated Email Notification]\n"
            "   To: %s\n"
            "   Subject: %s\n"
            "   Body: %s",
            to_email, subject, body_text
        )
        return True

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_from
        msg['To'] = to_email

        part1 = MIMEText(body_text, 'plain')
        msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, 'html')
            msg.attach(part2)

        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        if use_tls:
            server.starttls()
        if smtp_password:
            server.login(smtp_user, smtp_password)

        server.sendmail(smtp_from, [to_email], msg.as_string())
        server.quit()
        logger.info("✅ Email notification successfully sent to %s", to_email)
        return True
    except Exception as e:
        logger.warning("⚠️ Failed to deliver email to %s: %s", to_email, e)
        return False


def notify_issue_reported(issue):
    """Notify the reporter that their maintenance issue has been logged."""
    to_email = issue.get('reporter_email')
    reporter_name = issue.get('reporter_name', 'Student')
    title = issue.get('title', 'Campus Issue')
    facility = issue.get('facility', 'Facility')

    subject = f"Smart Campus: Issue Report Received - {title}"
    body_text = (
        f"Hello {reporter_name},\n\n"
        f"Thank you for reporting an issue with {facility}.\n"
        f"Title: {title}\n"
        f"Status: Pending Review\n\n"
        f"Our facilities team has received your report and will look into it promptly. "
        f"You can track the progress of your report using the 'My Reports' page on Smart Campus.\n\n"
        f"Best regards,\n"
        f"Smart Campus Facilities Team"
    )
    body_html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2>🛠️ Issue Report Received</h2>
        <p>Hello <strong>{reporter_name}</strong>,</p>
        <p>Thank you for helping keep our campus running smoothly. Your report has been logged:</p>
        <table style="border-collapse: collapse; margin: 16px 0;">
            <tr><td style="padding: 6px 12px; font-weight: bold;">Facility:</td><td style="padding: 6px 12px;">{facility}</td></tr>
            <tr><td style="padding: 6px 12px; font-weight: bold;">Title:</td><td style="padding: 6px 12px;">{title}</td></tr>
            <tr><td style="padding: 6px 12px; font-weight: bold;">Status:</td><td style="padding: 6px 12px; color: #e67e22; font-weight: bold;">Pending Review</td></tr>
        </table>
        <p>You can track the real-time status of your report on the Smart Campus portal.</p>
        <p>Best regards,<br><strong>Smart Campus Facilities Team</strong></p>
    </div>
    """
    return send_email_notification(to_email, subject, body_text, body_html)


def notify_issue_status_updated(issue, new_status):
    """Notify the reporter when their issue status has changed."""
    to_email = issue.get('reporter_email')
    reporter_name = issue.get('reporter_name', 'Student')
    title = issue.get('title', 'Campus Issue')
    facility = issue.get('facility', 'Facility')

    status_display = {
        'in_progress': 'In Progress ⏳',
        'resolved': 'Resolved ✅',
        'rejected': 'Closed / Rejected ❌'
    }.get(new_status, new_status.title())

    subject = f"Smart Campus: Issue Status Update - {status_display} ({title})"
    body_text = (
        f"Hello {reporter_name},\n\n"
        f"The status of your reported issue for {facility} ({title}) has been updated to: {status_display}.\n\n"
        f"You can check full details on the Smart Campus 'My Reports' page.\n\n"
        f"Best regards,\n"
        f"Smart Campus Facilities Team"
    )
    body_html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2>📢 Issue Status Update</h2>
        <p>Hello <strong>{reporter_name}</strong>,</p>
        <p>Your reported maintenance issue has received an update:</p>
        <table style="border-collapse: collapse; margin: 16px 0;">
            <tr><td style="padding: 6px 12px; font-weight: bold;">Facility:</td><td style="padding: 6px 12px;">{facility}</td></tr>
            <tr><td style="padding: 6px 12px; font-weight: bold;">Title:</td><td style="padding: 6px 12px;">{title}</td></tr>
            <tr><td style="padding: 6px 12px; font-weight: bold;">New Status:</td><td style="padding: 6px 12px; font-weight: bold; color: #2980b9;">{status_display}</td></tr>
        </table>
        <p>Thank you for your patience and contribution to a better campus environment.</p>
        <p>Best regards,<br><strong>Smart Campus Facilities Team</strong></p>
    </div>
    """
    return send_email_notification(to_email, subject, body_text, body_html)

