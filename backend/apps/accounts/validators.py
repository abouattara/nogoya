"""Phone normalisation, shared by registration and login.

Lived in the server-rendered forms module until those pages were removed;
the API is the only caller now.
"""
import re


def normalize_phone(phone):
    """Strip spaces/separators, keeping an optional leading +."""
    phone = (phone or "").strip()
    plus = phone.startswith("+")
    digits = re.sub(r"\D", "", phone)
    return f"+{digits}" if plus else digits
