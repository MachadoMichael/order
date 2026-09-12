from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.responses import ErrorResponse
from app.models import Token, UserPublic, UserRegister
from app.routers.deps import AuthServiceDep, CurrentUser

router = APIRouter(prefix="/auth", tags=["autenticacao"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um usuario",
    responses={409: {"model": ErrorResponse, "description": "Email ja cadastrado"}},
)
def register(payload: UserRegister, service: AuthServiceDep) -> UserPublic:
    user = service.register(payload.email, payload.password, payload.role)
    return UserPublic.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="Autentica e devolve o JWT",
    description="Compativel com o botao **Authorize** do Swagger: informe email no campo `username`.",
    responses={401: {"model": ErrorResponse, "description": "Credenciais invalidas"}},
)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], service: AuthServiceDep
) -> Token:
    token, expires_in = service.login(form.username, form.password)
    return Token(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserPublic, summary="Usuario do token atual")
def me(user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(user)
