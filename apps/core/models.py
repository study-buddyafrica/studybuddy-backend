import random
import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta
from apps.core.utils.countries import AfricanCountry
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)


class Core(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    def create_user(self, email, first_name, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field is required")
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, first_name, password, **extra_fields)


class OnboardingStep(models.TextChoices):
    PENDING_OTP = "pending_otp", "Pending OTP"
    STEP_2_PROFILE = "step_2_profile", "Step 2 Profile"
    STEP_3_ACADEMIC_KYC = "step_3_academic_kyc", "Step 3 Academic / KYC"
    STEP_4_LAUNCH = "step_4_launch", "Step 4 Launch"
    COMPLETED = "completed", "Completed"


class User(AbstractBaseUser, PermissionsMixin, Core):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("parent", "Parent"),
        ("teacher", "Teacher"),
    ]
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    account_confirmed = models.BooleanField(default=False)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=100)
    username = models.CharField(unique=True, max_length=30)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True, blank=True)
    onboarding_step = models.CharField(
        max_length=30,
        choices=OnboardingStep.choices,
        default=OnboardingStep.PENDING_OTP,
        db_index=True,
    )
    country = models.CharField(
        max_length=50,
        choices=AfricanCountry.choices,
        default=AfricanCountry.KENYA,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "username"]

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email}"

    def get_full_name(self) -> str:
        """Return the user's full name."""
        full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return full_name or self.email


class EmailVerificationCode(Core):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verifications",
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=6, db_index=True)
    email = models.EmailField(null=True, blank=True, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
        ]

    @classmethod
    def create_for_email(
        cls, email: str, user: User | None = None
    ) -> "EmailVerificationCode":
        """Create and return a new code record for given email (user optional)."""
        code = cls.generate_code()
        cls.objects.filter(email=email, user__isnull=True).delete()
        return cls.objects.create(email=email, code=code, user=user)

    @staticmethod
    def generate_code():
        """Generate a random 6-digit numeric code."""
        return f"{random.randint(100000, 999999)}"

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=15)

    def __str__(self):
        return f"{self.email} - {self.code}"


class ResetPasswordCode(Core):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    code = models.CharField(max_length=6)
    verified = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["code"]),
        ]

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=5)
