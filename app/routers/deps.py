from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.database import get_session
from app.services import OrderOrchestrator

SessionDep = Annotated[Session, Depends(get_session)]


def get_orchestrator(session: SessionDep) -> OrderOrchestrator:
    return OrderOrchestrator(session)


OrchestratorDep = Annotated[OrderOrchestrator, Depends(get_orchestrator)]
