import re

# VALID_USER_EMAIL checks for a semi-validish email. Of most concern
# it will fail to validate emails with unsafe url charactors
VALID_USER_EMAIL_EXPRESSION = (
    "^"
    "[^][{}|#?/:<>%`\\\\\x00-\x1f\x7f ]"  # The first letter: url unsafe chars + space
    "[^][{}|#?/:<>%`\\\\\x00-\x1f\x7f]*"  # Letters up to @ symbol: url unstafe chars
    "@"  # an @ symbol
    "[^]\"'@[{}|#?/:<>%`\\\\\x00-\x1f\x7f ]+"  # Domain parts: url unsafe chars + space + quotes + @
    "\\."  # a dot
    "[^]\"'@[{}|#?/:<>%`\\\\\x00-\x1f\x7f ]{2,}"  # The top level: url unsafe chars + sapece + quotes + @
    "$"
)
VALID_USER_EMAIL = re.compile(VALID_USER_EMAIL_EXPRESSION)


def is_valid_email(email):
    """Test if an email is a valid (safe) email

    Because we use email's in our url scheme the VALID_USER_EMAIL regular expression filters
    out potential unsafe charactors.

    Args:
        user_email (str): The value to be tested

    Returns:
        bool: True if the user_email was valid. Otherwise False
    """
    if len(email) > 254:
        return False
    return VALID_USER_EMAIL.match(email) is not None
