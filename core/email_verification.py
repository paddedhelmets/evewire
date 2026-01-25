"""
Email verification service for account recovery and magic link login.

Supports both email sending and dev-log mode for testing.
"""

import secrets
import logging
from typing import Optional

from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger('evewire')


def generate_verification_token() -> str:
    """Generate a secure token for email verification."""
    return secrets.token_urlsafe(32)


def send_verification_email(user, request) -> bool:
    """
    Send verification email with magic login link.

    In development mode (DEV_EMAIL_LOG=True), prints the code to console
    instead of sending an email.
    """
    token = generate_verification_token()
    user.email_verification_token = token
    user.email_verification_expires = timezone.now() + timedelta(hours=24)
    user.save()

    # Build login link
    base_url = getattr(settings, 'APP_BASE_URL', 'http://192.168.0.90:8000')
    login_link = f"{base_url}/verify-email/{token}/"

    # Development mode: print to console instead of sending email
    if getattr(settings, 'DEV_EMAIL_LOG', False):
        logger.info(f"")
        logger.info(f"=" * 60)
        logger.info(f"📧 DEV EMAIL LOG MODE - Magic Login Link")
        logger.info(f"=" * 60)
        logger.info(f"User: {user.display_name}")
        logger.info(f"Email: {user.email}")
        logger.info(f"Token: {token}")
        logger.info(f"Login Link: {login_link}")
        logger.info(f"=" * 60)
        logger.info(f"")
        return True

    # Production mode: send actual email
    try:
        send_mail(
            'Verify your evewire account',
            f'Click the link below to log in to your evewire account:\n\n{login_link}\n\n'
            f'This link will expire in 24 hours.\n\n'
            f'If you did not request this login, please ignore this email.',
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@evewire.local'),
            [user.email],
            fail_silently=False,
        )
        logger.info(f'Sent verification email to {user.email}')
        return True
    except Exception as e:
        logger.error(f'Failed to send verification email: {e}')
        return False


def verify_email_token(token: str) -> Optional['User']:
    """
    Verify an email verification token and return the user if valid.

    Returns None if token is invalid or expired.
    """
    from core.models import User

    try:
        user = User.objects.get(
            email_verification_token=token,
            email_verification_expires__gt=timezone.now()
        )
        # Mark email as verified and clear token
        user.email_verified = True
        user.email_verification_token = None
        user.email_verification_expires = None
        user.save()
        logger.info(f'Email verified for user {user.display_name}')
        return user
    except User.DoesNotExist:
        logger.warning(f'Invalid or expired email verification token')
        return None


def is_email_configured() -> bool:
    """Check if email is properly configured for sending."""
    return all([
        hasattr(settings, 'EMAIL_HOST'),
        hasattr(settings, 'EMAIL_PORT'),
        getattr(settings, 'DEV_EMAIL_LOG', False) or bool(getattr(settings, 'EMAIL_HOST_USER', ''))
    ])


def require_email_verification(user):
    """
    Check if user has verified email for sensitive operations.

    Returns True if user has verified email, False otherwise.
    Can be used to restrict certain operations to verified accounts only.
    """
    return bool(user.email and user.email_verified)
