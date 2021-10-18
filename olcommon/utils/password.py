from pathlib import Path

import dateparser

def is_valid_password(password, invalid_contents=None):
    password = "".join(password.lower().split())
    if len(password) < 8:
        return False
    if common_passwords_cache is None:
        load_common_password_cache()
    if password in common_passwords_cache:
        return False
    for part in invalid_contents or []:
        part = "".join(part.lower().split())
        if part in password:
            return False
    if dateparser.parse(password) is not None:
        return False
    return True


common_passwords_cache = None


def load_common_password_cache():
    global common_passwords_cache
    path = Path(__file__).parent / "passwords-common.txt"
    common_passwords = set()
    with path.open() as fin:
        for line in fin:
            word = line.strip()
            common_passwords.add(word)
    common_passwords_cache = common_passwords
