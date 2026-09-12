from sqlmodel import Session

from app.core.exceptions import EmailAlreadyUsed, InvalidCredentials
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, UserRole
from app.repositories import UserRepository


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)

    def register(self, email: str, password: str, role: UserRole = UserRole.OPERATOR) -> User:
        if self.users.get_by_email(email) is not None:
            raise EmailAlreadyUsed(email)
        user = User(email=email, password_hash=hash_password(password), role=role)
        self.users.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def login(self, email: str, password: str) -> tuple[str, int]:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentials()
        return create_access_token(user.id, user.email, user.role.value)
