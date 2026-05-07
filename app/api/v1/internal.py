from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.keep_alive_service import ping_keep_alive

router = APIRouter()


@router.post("/keep-alive/ping", summary="Trigger keep-alive ping")
def keep_alive_ping(db: Session = Depends(get_db)):
    # TODO: Bind this endpoint to internal auth once available.
    success = ping_keep_alive(db)
    return {"success": success}
