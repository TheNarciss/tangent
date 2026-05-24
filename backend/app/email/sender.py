"""Resend-based email sender.

Resend docs: https://resend.com/docs/api-reference/emails/send-email
"""

import logging
import os

import resend

logger = logging.getLogger(__name__)

resend.api_key = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "onboarding@resend.dev")
FROM_NAME = os.getenv("SMTP_FROM_NAME", "Tangent")


def send_password_reset_code(to_email: str, code: str, expires_minutes: int = 15) -> None:
    """Send the 6-digit reset code by email. Raises on failure (caller may swallow)."""
    if not resend.api_key:
        logger.error("RESEND_API_KEY missing — email NOT sent for %s", to_email)
        raise RuntimeError("Email service not configured")

    html = f"""
    <!doctype html>
    <html>
      <body style="font-family: -apple-system, system-ui, sans-serif; background: #0a0a0a; color: #f4f4f5; padding: 32px;">
        <div style="max-width: 480px; margin: 0 auto; background: #18181b; border-radius: 12px; padding: 32px; border: 1px solid #27272a;">
          <h1 style="font-size: 20px; margin: 0 0 16px;">Réinitialisation de ton mot de passe</h1>
          <p style="color: #a1a1aa; line-height: 1.6; margin: 0 0 24px;">
            Tu as demandé à réinitialiser ton mot de passe Tangent. Voici ton code de vérification :
          </p>
          <div style="background: #27272a; border-radius: 8px; padding: 16px; text-align: center; font-family: 'SF Mono', monospace; font-size: 32px; letter-spacing: 8px; color: #10b981; font-weight: 600; margin-bottom: 24px;">
            {code}
          </div>
          <p style="color: #a1a1aa; font-size: 13px; line-height: 1.6; margin: 0 0 8px;">
            Ce code expire dans <strong style="color: #f4f4f5;">{expires_minutes} minutes</strong>. Il ne peut être utilisé qu'une seule fois.
          </p>
          <p style="color: #71717a; font-size: 12px; line-height: 1.6; margin: 16px 0 0;">
            Tu n'as pas demandé ce reset ? Ignore ce mail et change immédiatement ton mot de passe par sécurité.
          </p>
        </div>
        <p style="text-align: center; color: #52525b; font-size: 11px; margin-top: 24px;">Tangent · Personal Portfolio Dashboard</p>
      </body>
    </html>
    """

    try:
        resend.Emails.send(
            {
                "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                "to": [to_email],
                "subject": "Code de réinitialisation — Tangent",
                "html": html,
            }
        )
        logger.info("Password reset code sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send reset code email to %s", to_email)
        raise
