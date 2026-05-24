"""Email service. Currently uses Resend (https://resend.com)."""
from .sender import send_password_reset_code

__all__ = ["send_password_reset_code"]
