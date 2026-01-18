"""
Core models for evewire.

Includes custom User model (for EVE SSO authentication only, no passwords)
and Character model for tracking EVE characters.
"""

import uuid
import logging
from typing import Optional

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger('evewire')


def get_encryption_key() -> bytes:
    """Get or create encryption key for token storage."""
    from cryptography.fernet import Fernet
    import base64
    import hashlib

    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_token(token: str) -> str:
    """Encrypt a refresh token for storage."""
    f = Fernet(get_encryption_key())
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a stored refresh token."""
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted.encode()).decode()


class EvewireUserManager(BaseUserManager['User']):
    """Custom user manager for EVE SSO-only authentication."""

    def create_user(self, **extra_fields) -> 'User':
        """Create a new user (no password required)."""
        if not extra_fields.get('eve_character_id'):
            raise ValueError('EVE character ID is required')

        user = self.model(**extra_fields)
        user.save(using=self._db)
        return user

    def create_superuser(self, **extra_fields) -> 'User':
        """Create a superuser (for admin access)."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(**extra_fields)

    def get_by_eve_character(self, character_id: int) -> Optional['User']:
        """Get a user by their EVE character ID."""
        try:
            return self.get(eve_character_id=character_id)
        except self.model.DoesNotExist:
            return None


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for EVE SSO authentication.

    Uses EVE character ID as the primary identifier. No password field.
    Users are created automatically when they first log in via EVE SSO.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    eve_character_id = models.BigIntegerField(
        unique=True,
        db_index=True,
        help_text=_('EVE Online Character ID (from SSO)')
    )
    eve_character_name = models.CharField(
        max_length=255,
        help_text=_('EVE Online Character Name')
    )
    corporation_id = models.BigIntegerField(null=True, blank=True)
    corporation_name = models.CharField(max_length=255, blank=True)
    alliance_id = models.BigIntegerField(null=True, blank=True)
    alliance_name = models.CharField(max_length=255, blank=True)

    refresh_token = models.TextField(
        blank=True,
        help_text=_('Encrypted OAuth2 refresh token')
    )
    token_expires = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True)

    settings = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = EvewireUserManager()

    USERNAME_FIELD = 'eve_character_id'
    REQUIRED_FIELDS = ['eve_character_name']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['eve_character_name']

    def __str__(self) -> str:
        return self.eve_character_name

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def set_refresh_token(self, token: str) -> None:
        """Encrypt and store refresh token."""
        self.refresh_token = encrypt_token(token)

    def get_refresh_token(self) -> Optional[str]:
        """Decrypt and return refresh token."""
        if not self.refresh_token:
            return None
        try:
            return decrypt_token(self.refresh_token)
        except Exception as e:
            logger.error(f'Failed to decrypt token for user {self.id}: {e}')
            return None

    def update_from_esi(self, character_data: dict) -> None:
        """Update user fields from ESI character data."""
        self.eve_character_name = character_data.get('name', self.eve_character_name)
        self.corporation_id = character_data.get('corporation_id')
        self.save(update_fields=['eve_character_name', 'corporation_id', 'updated_at'])

    def has_valid_token(self) -> bool:
        """Check if the user has a refresh token."""
        return bool(self.refresh_token)

    def needs_token_refresh(self) -> bool:
        """Check if access token needs refresh."""
        if not self.token_expires:
            return True
        return timezone.now() >= self.token_expires - timezone.timedelta(minutes=5)


class EveScope(models.TextChoices):
    """EVE SSO scopes requested by evewire."""

    SKILLS_READ = 'esi-skills.read_skills.v1', 'Read Skills'
    SKILL_QUEUE_READ = 'esi-skills.read_skillqueue.v1', 'Read Skill Queue'
    WALLET_READ = 'esi-wallet.read_character_wallet.v1', 'Read Wallet'
    ASSETS_READ = 'esi-assets.read_assets.v1', 'Read Assets'
    ORDERS_READ = 'esi-markets.read_character_orders.v1', 'Read Market Orders'

    @classmethod
    def mvp_scopes(cls) -> list[str]:
        """Return list of scopes required for MVP."""
        return [
            cls.SKILLS_READ.value[0],
            cls.SKILL_QUEUE_READ.value[0],
            cls.WALLET_READ.value[0],
            cls.ASSETS_READ.value[0],
            cls.ORDERS_READ.value[0],
        ]


class SyncStatus(models.TextChoices):
    """Status of ESI data sync."""

    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    SUCCESS = 'success', 'Success'
    FAILED = 'failed', 'Failed'
    RATE_LIMITED = 'rate_limited', 'Rate Limited'


class Character(models.Model):
    """
    EVE Character linked to a user.

    MVP: 1:1 User-Character relationship. Future: support multiple chars per user.
    """

    id = models.BigIntegerField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='character')

    skills_data = models.JSONField(null=True, blank=True)
    skills_synced_at = models.DateTimeField(null=True, blank=True)

    skill_queue_data = models.JSONField(null=True, blank=True)
    skill_queue_synced_at = models.DateTimeField(null=True, blank=True)

    wallet_balance = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    wallet_synced_at = models.DateTimeField(null=True, blank=True)

    assets_data = models.JSONField(null=True, blank=True)
    assets_synced_at = models.DateTimeField(null=True, blank=True)

    orders_data = models.JSONField(null=True, blank=True)
    orders_synced_at = models.DateTimeField(null=True, blank=True)

    last_sync_status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING
    )
    last_sync_error = models.TextField(blank=True)
    last_sync = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('character')
        verbose_name_plural = _('characters')

    def __str__(self) -> str:
        return self.user.eve_character_name

    @property
    def name(self) -> str:
        return self.user.eve_character_name

    def get_access_token(self) -> Optional[str]:
        """Get a valid access token for ESI requests."""
        # This will be implemented in services.py
        from core.services import TokenManager
        return TokenManager.get_access_token(self.user)

    def is_data_stale(self, data_type: str, max_age_seconds: int = 3600) -> bool:
        """Check if cached data is stale."""
        field_name = f'{data_type}_synced_at'
        sync_time = getattr(self, field_name, None)
        if not sync_time:
            return True
        age = timezone.now() - sync_time
        return age.total_seconds() > max_age_seconds


class AuditLog(models.Model):
    """Audit log for security-sensitive actions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('audit log')
        verbose_name_plural = _('audit logs')
        ordering = ['-created_at']

    def __str__(self) -> str:
        user_name = self.user.eve_character_name if self.user else 'Unknown'
        return f'{user_name}: {self.action}'

    @classmethod
    def log(cls, user: User, action: str, **kwargs) -> 'AuditLog':
        """Create a new audit log entry."""
        return cls.objects.create(user=user, action=action, metadata=kwargs)
