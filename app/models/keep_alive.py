from sqlalchemy import BigInteger, Column, DateTime, Integer, func, text
from app.models.base import Base


class KeepAlive(Base):
    __tablename__ = "keep_alive"

    id = Column(Integer, primary_key=True)
    counter = Column(BigInteger, nullable=False, server_default=text("0"))
    pinged_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
