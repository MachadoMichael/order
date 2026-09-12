from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.security import decode_access_token
from app.database import get_session
from app.models import User
from app.repositories import UserRepository
from app.services import AuthService, CustomerService, OrderOrchestrator

SessionDep = Annotated[Session, Depends(get_session)]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    session: SessionDep, token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="token invalido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user = UserRepository(session).get(UUID(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise credentials_error from exc
    if user is None:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(session)


def get_customer_service(session: SessionDep) -> CustomerService:
    return CustomerService(session)


def get_orchestrator(session: SessionDep) -> OrderOrchestrator:
    return OrderOrchestrator(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CustomerServiceDep = Annotated[CustomerService, Depends(get_customer_service)]
OrchestratorDep = Annotated[OrderOrchestrator, Depends(get_orchestrator)]
