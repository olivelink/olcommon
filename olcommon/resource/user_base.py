
from ..exc import UserPasswordBaseInvalidTokenError
from datetime import datetime
from datetime import timedelta
import bcrypt
import secrets

from olcommon import logger


class UserPasswordBase:
    """Base recipie for a user object to implmenet user password.

    The resulting object mustimplmenet the fllowing settable attributes:

    - password_hash (bytes)
    - password_reset_token (string)
    - password_reset_expiry (datetime)
    - nounce (big int)

    """

    PASSWORD_RESET_TOKEN_SIZE = 24

    @classmethod
    def hash_password(cls, password):
        return bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt())

    def set_password(self, password):
        logger.info(f"Set password for: {self}")
        password_hash = self.hash_password(password)
        self.password_hash = password_hash
        self.change_nounce()
        self.password_reset_token = None
        self.password_reset_expiry = None

    def set_password_with_token(self, password, token, now=None):
        logger.info(f"Set password with token for: {self}")
        if not self.password_reset_token:
            raise UserPasswordBaseInvalidTokenError()
        now = now or datetime.utcnow()
        if now > self.password_reset_expiry:
            raise UserPasswordBaseInvalidTokenError()
        if len(token) == 0:
            raise UserPasswordBaseInvalidTokenError()
        if token != self.password_reset_token:
            raise UserPasswordBaseInvalidTokenError()
        self.set_password(password)
        self.password_reset_token = None
        self.password_reset_expiry = None

    def check_password(self, password):
        if not password:
            return False
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode("utf8"), self.password_hash)

    def initiate_password_reset(self):
        """Generates and sets the password_reset_token and
        password_reset_expiry fields, if a password reset is not yet in
        progress or has already expired.
        """
        logger.info(f"Initate password reset for: {self}")
        now = datetime.utcnow()
        token = secrets.token_urlsafe(self.PASSWORD_RESET_TOKEN_SIZE)
        self.password_reset_token = token
        self.password_reset_expiry = now + timedelta(days=1)

    def change_nounce(self):
        logger.info(f"Change nounce for: {self}")
        if self.nounce is None:
            self.nounce = 0
        self.nounce += 1