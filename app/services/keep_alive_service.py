from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.keep_alive import KeepAlive
from app.utils.logger import logger


def ping_keep_alive(db: Session) -> bool:
    try:
        stmt = (
            update(KeepAlive)
            .where(KeepAlive.id == 1)
            .values(
                counter=KeepAlive.counter + 1,
                pinged_at=func.now(),
            )
        )
        result = db.execute(stmt)
        if result.rowcount == 0:
            logger.warning("Keep-alive row missing; expected id=1.")
        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        logger.exception("Keep-alive ping failed: %s", exc)
        return False


def ping_keep_alive_job() -> None:
    db = SessionLocal()
    try:
        ping_keep_alive(db)
    finally:
        db.close()
