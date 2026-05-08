import resend
from app.config import settings

resend.api_key = settings.resend_api_key


def _send(to: str, subject: str, html: str) -> None:
    resend.Emails.send({
        "from": settings.resend_from_email,
        "to": to,
        "subject": subject,
        "html": html,
    })


def send_submission_confirmation(to: str, reference_number: str, full_name: str) -> None:
    _send(
        to=to,
        subject="Your KYC submission has been received — Cognify",
        html=f"""
        <p>Dear {full_name},</p>
        <p>We have received your KYC document submission.</p>
        <p><strong>Reference number: {reference_number}</strong></p>
        <p>Our team will review your documents and notify you of the outcome within 2–3 business days.</p>
        <p>Cognify Team</p>
        """,
    )


def send_status_update(to: str, reference_number: str, full_name: str, status: str, reason: str | None = None) -> None:
    if status == "under_review":
        subject = "Your KYC submission is under review — Cognify"
        body = "<p>Our team has started reviewing your documents. We will notify you once a decision has been made.</p>"
    elif status == "approved":
        subject = "Your KYC submission has been approved — Cognify"
        body = "<p>Congratulations! Your identity has been successfully verified.</p>"
    elif status == "rejected":
        subject = "Your KYC submission requires attention — Cognify"
        reason_text = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""
        body = f"<p>Unfortunately, we were unable to verify your identity with the documents provided.</p>{reason_text}<p>Please resubmit with the correct documents.</p>"
    else:
        return

    _send(
        to=to,
        subject=subject,
        html=f"<p>Dear {full_name},</p>{body}<p>Reference: {reference_number}</p><p>Cognify Team</p>",
    )
