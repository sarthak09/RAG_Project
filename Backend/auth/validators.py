import re

def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email))

def is_strong_password(password: str) -> bool:
    return (
        len(password) >= 8 and
        re.search(r"[0-9]", password) and
        re.search(r"[A-Z]", password) and
        re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    )
