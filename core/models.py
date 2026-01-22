"""
Core models for evewire.

Includes custom User model (for EVE SSO authentication only, no passwords)
and Character model for tracking EVE characters.

Data models are split into sub-modules:
- core.eve.models: Reference data (ItemType, SolarSystem, Station, etc.)
- core.character.models: Character data (skills, assets, wallet, orders)
- core.doctrines.models: Doctrine/fleet management (fits, shopping lists)
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
from datetime import timedelta
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger('evewire')


def get_encryption_key() -> bytes:
    """Get or create encryption key for token storage."""
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

    def create_user(self, username: str, **extra_fields) -> 'User':
        """Create a new user (no password required)."""
        if not username:
            raise ValueError('Username is required')

        user = self.model(username=username, **extra_fields)
        user.save(using=self._db)
        return user

    def create_superuser(self, username: str, **extra_fields) -> 'User':
        """Create a superuser (for admin access)."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, **extra_fields)

    def get_by_eve_character(self, character_id: int) -> Optional['User']:
        """Get a user by their EVE character ID (via Character model)."""
        try:
            from core.models import Character
            character = Character.objects.get(id=character_id)
            return character.user
        except Character.DoesNotExist:
            return None

    def generate_username(self) -> str:
        """Generate a unique username for a new user."""
        import random
        import string
        while True:
            # Generate random username like "pilot_abc123"
            username = f"pilot_{''.join(random.choices(string.ascii_lowercase + string.digits, k=12))}"
            if not self.filter(username=username).exists():
                return username


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for EVE SSO authentication.

    Supports multiple characters per user. Uses auto-generated username.
    Users are created automatically when they first log in via EVE SSO.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Auto-generated username for Django admin/auth (not displayed in UI)
    username = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        blank=True,
        default='',
        help_text=_('Auto-generated username for authentication')
    )

    # First character info kept for backward compatibility
    eve_character_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_('EVE Online Character ID of first linked character (deprecated)')
    )
    eve_character_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('EVE Online Character Name of first linked character (deprecated)')
    )
    corporation_id = models.BigIntegerField(null=True, blank=True)
    corporation_name = models.CharField(max_length=255, blank=True)
    alliance_id = models.BigIntegerField(null=True, blank=True)
    alliance_name = models.CharField(max_length=255, blank=True)

    # Deprecated - moved to Character model
    refresh_token = models.TextField(
        blank=True,
        help_text=_('Deprecated: Use character.refresh_token instead')
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

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self) -> str:
        # Return the first character's name if available, otherwise username
        first_char = self.characters.first()
        if first_char:
            return first_char.character_name
        return self.username

    @property
    def display_name(self) -> str:
        """Get display name from first character or username."""
        first_char = self.characters.first()
        if first_char:
            return first_char.character_name
        return self.username

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
        return timezone.now() >= self.token_expires - timedelta(minutes=5)


class EveScope(models.TextChoices):
    """EVE SSO scopes requested by evewire."""

    SKILLS_READ = 'esi-skills.read_skills.v1', 'Read Skills'
    SKILL_QUEUE_READ = 'esi-skills.read_skillqueue.v1', 'Read Skill Queue'
    CLONES_READ = 'esi-clones.read_clones.v1', 'Read Clones'
    IMPLANTS_READ = 'esi-clones.read_implants.v1', 'Read Implants'
    WALLET_READ = 'esi-wallet.read_character_wallet.v1', 'Read Wallet'
    ASSETS_READ = 'esi-assets.read_assets.v1', 'Read Assets'
    ORDERS_READ = 'esi-markets.read_character_orders.v1', 'Read Market Orders'
    INDUSTRY_JOBS_READ = 'esi-industry.read_character_jobs.v1', 'Read Industry Jobs'

    @classmethod
    def mvp_scopes(cls) -> list[str]:
        """Return list of scopes required for MVP."""
        return [
            cls.SKILLS_READ.value,
            cls.SKILL_QUEUE_READ.value,
            cls.CLONES_READ.value,
            cls.IMPLANTS_READ.value,
            cls.WALLET_READ.value,
            cls.ASSETS_READ.value,
            cls.ORDERS_READ.value,
            cls.INDUSTRY_JOBS_READ.value,
        ]


class SyncStatus(models.TextChoices):
    """Status of ESI data sync."""

    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    SUCCESS = 'success', 'Success'
    FAILED = 'failed', 'Failed'
    RATE_LIMITED = 'rate_limited', 'Rate Limited'
    NEEDS_REAUTH = 'needs_reauth', 'Needs Re-authentication'


class Character(models.Model):
    """
    EVE Character linked to a user.

    Supports multiple characters per user for character management.

    This model tracks sync metadata. Actual character data (skills, assets, wallet)
    is stored in relational models in core.character.models.
    """

    id = models.BigIntegerField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='characters')

    # OAuth2 token storage (per-character)
    refresh_token = models.TextField(
        blank=True,
        help_text=_('Encrypted OAuth2 refresh token for this character')
    )
    token_expires = models.DateTimeField(null=True, blank=True)

    # Character info from ESI
    character_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_('EVE Online Character Name')
    )
    corporation_id = models.BigIntegerField(null=True, blank=True)
    corporation_name = models.CharField(max_length=255, blank=True)
    alliance_id = models.BigIntegerField(null=True, blank=True)
    alliance_name = models.CharField(max_length=255, blank=True)

    # Wallet balance (cached for quick display)
    wallet_balance = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    wallet_synced_at = models.DateTimeField(null=True, blank=True)

    # Total SP (cached for quick display)
    total_sp = models.IntegerField(null=True, blank=True)
    skills_synced_at = models.DateTimeField(null=True, blank=True)
    industry_jobs_synced_at = models.DateTimeField(null=True, blank=True)
    orders_synced_at = models.DateTimeField(null=True, blank=True)
    contracts_synced_at = models.DateTimeField(null=True, blank=True)

    # Sync status
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
        ordering = ['character_name']

    def __str__(self) -> str:
        return self.character_name

    @property
    def name(self) -> str:
        return self.character_name

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
            logger.error(f'Failed to decrypt token for character {self.id}: {e}')
            return None

    def has_valid_token(self) -> bool:
        """Check if the character has a refresh token."""
        return bool(self.refresh_token)

    def needs_token_refresh(self) -> bool:
        """Check if access token needs refresh."""
        if not self.token_expires:
            return True
        return timezone.now() >= self.token_expires - timedelta(minutes=5)

    def get_access_token(self) -> Optional[str]:
        """Get a valid access token for ESI requests."""
        from core.services import TokenManager
        return TokenManager.get_access_token_for_character(self)

    def is_wallet_stale(self, max_age_seconds: int = 3600) -> bool:
        """Check if wallet balance is stale."""
        if not self.wallet_synced_at:
            return True
        age = timezone.now() - self.wallet_synced_at
        return age.total_seconds() > max_age_seconds

    def is_skills_stale(self, max_age_seconds: int = 3600) -> bool:
        """Check if skills data is stale."""
        if not self.skills_synced_at:
            return True
        age = timezone.now() - self.skills_synced_at
        return age.total_seconds() > max_age_seconds

    # Industry slot calculation methods
    # Manufacturing: Mass Production (3380) + Adv Mass Production (24325)
    # Science: Laboratory Operation (24268) + Adv Lab Operation (24270)
    # Reactions: Mass Reactions (45748) + Adv Mass Reactions (45749)
    # Each level adds 1 slot to base of 1, max 11 slots per category

    MASS_PRODUCTION_SKILL_ID = 3380
    ADV_MASS_PRODUCTION_SKILL_ID = 24325
    LAB_OPERATION_SKILL_ID = 24268
    ADV_LAB_OPERATION_SKILL_ID = 24270
    MASS_REACTIONS_SKILL_ID = 45748
    ADV_MASS_REACTIONS_SKILL_ID = 45749

    # Market order slot calculation methods
    # Skill IDs: Trade (3443), Retail (3444), Wholesale (3445), Tycoon (3446)
    TRADE_SKILL_ID = 3443
    RETAIL_SKILL_ID = 3444
    WHOLESALE_SKILL_ID = 3445
    TYCOON_SKILL_ID = 3446

    def get_skill_level(self, skill_id: int) -> int:
        """Get the level of a specific skill."""
        try:
            return self.skills.get(skill_id=skill_id).skill_level
        except CharacterSkill.DoesNotExist:
            return 0

    @property
    def manufacturing_slots(self) -> int:
        """Get max manufacturing slots from Mass Production skills."""
        base_slots = 1
        mass_prod_bonus = 1 * self.get_skill_level(self.MASS_PRODUCTION_SKILL_ID)
        adv_mass_prod_bonus = 1 * self.get_skill_level(self.ADV_MASS_PRODUCTION_SKILL_ID)
        return base_slots + mass_prod_bonus + adv_mass_prod_bonus

    @property
    def science_slots(self) -> int:
        """Get max science/research slots from Laboratory Operation skills."""
        base_slots = 1
        lab_op_bonus = 1 * self.get_skill_level(self.LAB_OPERATION_SKILL_ID)
        adv_lab_op_bonus = 1 * self.get_skill_level(self.ADV_LAB_OPERATION_SKILL_ID)
        return base_slots + lab_op_bonus + adv_lab_op_bonus

    @property
    def reaction_slots(self) -> int:
        """Get max reaction slots from Mass Reactions skills."""
        base_slots = 1
        mass_rx_bonus = 1 * self.get_skill_level(self.MASS_REACTIONS_SKILL_ID)
        adv_mass_rx_bonus = 1 * self.get_skill_level(self.ADV_MASS_REACTIONS_SKILL_ID)
        return base_slots + mass_rx_bonus + adv_mass_rx_bonus

    @property
    def active_manufacturing_jobs(self) -> int:
        """Count active manufacturing jobs (activity_id=1)."""
        from core.character.models import IndustryJob
        return self.industry_jobs.filter(activity_id=1, status=1).count()

    @property
    def active_research_jobs(self) -> int:
        """Count active research jobs (copying, invention, ME, TE)."""
        from core.character.models import IndustryJob
        return self.industry_jobs.filter(activity_id__in=[3, 4, 5, 8], status=1).count()

    @property
    def active_reaction_jobs(self) -> int:
        """Count active reaction jobs."""
        from core.character.models import IndustryJob
        return self.industry_jobs.filter(activity_id=9, status=1).count()

    @property
    def manufacturing_utilization(self) -> float:
        """Get manufacturing slot utilization as percentage (0-100)."""
        if self.manufacturing_slots == 0:
            return 0.0
        return (self.active_manufacturing_jobs / self.manufacturing_slots) * 100

    @property
    def science_utilization(self) -> float:
        """Get science slot utilization as percentage (0-100)."""
        if self.science_slots == 0:
            return 0.0
        return (self.active_research_jobs / self.science_slots) * 100

    @property
    def reaction_utilization(self) -> float:
        """Get reaction slot utilization as percentage (0-100)."""
        if self.reaction_slots == 0:
            return 0.0
        return (self.active_reaction_jobs / self.reaction_slots) * 100

    @property
    def is_manufacturing_nearly_full(self) -> bool:
        """Check if manufacturing slots are >80% utilized."""
        return self.manufacturing_utilization > 80.0

    @property
    def is_science_nearly_full(self) -> bool:
        """Check if science slots are >80% utilized."""
        return self.science_utilization > 80.0

    @property
    def is_reactions_nearly_full(self) -> bool:
        """Check if reaction slots are >80% utilized."""
        return self.reaction_utilization > 80.0

    @property
    def has_available_manufacturing_slot(self) -> bool:
        """Check if there's an available manufacturing slot."""
        return self.active_manufacturing_jobs < self.manufacturing_slots

    @property
    def has_available_science_slot(self) -> bool:
        """Check if there's an available science slot."""
        return self.active_research_jobs < self.science_slots

    @property
    def has_available_reaction_slot(self) -> bool:
        """Check if there's an available reaction slot."""
        return self.active_reaction_jobs < self.reaction_slots

    # Market order slot calculation methods
    # Base slots: 5
    # Trade: +5 per level, Retail: +4 per level, Wholesale: +8 per level, Tycoon: +16 per level

    @property
    def market_order_slots(self) -> int:
        """Get max market order slots from Trade skills."""
        base_slots = 5
        trade_bonus = 5 * self.get_skill_level(self.TRADE_SKILL_ID)
        retail_bonus = 4 * self.get_skill_level(self.RETAIL_SKILL_ID)
        wholesale_bonus = 8 * self.get_skill_level(self.WHOLESALE_SKILL_ID)
        tycoon_bonus = 16 * self.get_skill_level(self.TYCOON_SKILL_ID)
        return base_slots + trade_bonus + retail_bonus + wholesale_bonus + tycoon_bonus

    @property
    def active_market_orders(self) -> int:
        """Count active (open) market orders."""
        from core.character.models import MarketOrder
        return self.market_orders.filter(state='open').count()

    @property
    def market_order_utilization(self) -> float:
        """Get market order slot utilization as percentage (0-100)."""
        if self.market_order_slots == 0:
            return 0.0
        return (self.active_market_orders / self.market_order_slots) * 100

    @property
    def is_market_orders_nearly_full(self) -> bool:
        """Check if market order slots are >80% utilized."""
        return self.market_order_utilization > 80.0

    @property
    def has_available_market_order_slot(self) -> bool:
        """Check if there's an available market order slot."""
        return self.active_market_orders < self.market_order_slots


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
        user_name = self.user.display_name if self.user else 'Unknown'
        return f'{user_name}: {self.action}'

    @classmethod
    def log(cls, user: User, action: str, **kwargs) -> 'AuditLog':
        """Create a new audit log entry."""
        return cls.objects.create(user=user, action=action, metadata=kwargs)


# Import sub-modules for proper model registration
from core.eve.models import *  # noqa: E402, F401, F403
from core.character.models import *  # noqa: E402, F401, F403
from core.doctrines.models import *  # noqa: E402, F401, F403
from core.trade.models import *  # noqa: E402, F401, F403
