"""Common validators for the application"""

from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_birth_date_minimum_age(birth_date, min_age=18):
    """
    Validate that birth_date is at least min_age years ago.

    Args:
        birth_date: Date object to validate
        min_age: Minimum age in years (default: 18)

    Raises:
        ValidationError if birth_date is too recent or in the future
    """
    if not birth_date:
        return

    today = timezone.now().date()

    # Check if date is in the future
    if birth_date > today:
        raise ValidationError("Birth date cannot be in the future.")

    # Calculate age
    age = (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )

    if age < min_age:
        raise ValidationError(
            f"You must be at least {min_age} years old. "
            f"Earliest birth date allowed: {today - timedelta(days=365 * min_age)}"
        )


def validate_birth_date_student(birth_date):
    """
    Validate student birth date.
    Students must be at least 5 years old (no pre-school children).
    """
    return validate_birth_date_minimum_age(birth_date, min_age=5)


def validate_birth_date_teacher(birth_date):
    """
    Validate teacher birth date.
    Teachers must be at least 18 years old.
    """
    return validate_birth_date_minimum_age(birth_date, min_age=18)


def validate_birth_date_parent(birth_date):
    """
    Validate parent birth date.
    Parents must be at least 18 years old (legal age).
    """
    return validate_birth_date_minimum_age(birth_date, min_age=18)


def validate_string_length(value, min_length=1, max_length=255, field_name="Field"):
    """
    Validate string field length.

    Args:
        value: String to validate
        min_length: Minimum length required
        max_length: Maximum length allowed
        field_name: Name of field for error message

    Raises:
        ValidationError if length is invalid
    """
    if not value:
        if min_length > 0:
            raise ValidationError(f"{field_name} is required.")
        return

    if len(value) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} character(s)."
        )

    if len(value) > max_length:
        raise ValidationError(f"{field_name} cannot exceed {max_length} character(s).")


def validate_phone_number(phone_number):
    """
    Validate phone number format.
    Accepts: 10-15 digits, optionally with +, -, (, ), spaces
    """
    if not phone_number:
        return

    # Remove common phone formatting characters
    digits_only = "".join(c for c in phone_number if c.isdigit())

    if len(digits_only) < 10 or len(digits_only) > 15:
        raise ValidationError("Phone number must contain between 10 and 15 digits.")


def validate_hourly_rate(hourly_rate):
    """
    Validate teacher hourly rate.
    Must be positive and reasonable (0.01 to 999999.99)
    """
    if hourly_rate is None:
        return

    if hourly_rate <= 0:
        raise ValidationError("Hourly rate must be greater than zero.")

    if hourly_rate > 999999.99:
        raise ValidationError("Hourly rate is unreasonably high.")
