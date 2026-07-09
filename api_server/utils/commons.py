import time
import hashlib
import secrets
import string
import uuid

def get_current_ts():
    return int(time.time())


def get_md5(text: str, salt: str="") -> str:
    return hashlib.md5(f"{text}{salt}".encode("utf-8")).hexdigest()


def generate_sessionid(prefix: str = "sessionid_", random_len: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(random_len))
    return f"{prefix}{token}"



def generate_user_id() -> int:
    """Generate a unique 32-bit positive integer."""
    return uuid.uuid4().fields[0]


def generate_random_id() -> int:
    return generate_user_id()


def generate_uuid_hex() -> str:
    """Generate a unique random hexadecimal UUID string."""
    return uuid.uuid4().hex


def get_bytes_md5(content: bytes) -> str:
    """Calculate the MD5 hash of raw bytes."""
    return hashlib.md5(content).hexdigest()