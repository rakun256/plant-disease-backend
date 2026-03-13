from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.exceptions import CredentialsException
from jose import jwt, JWTError
from app.core.config import settings
from app.core.constants import ALGORITHM
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise CredentialsException()
    except JWTError:
        raise CredentialsException()
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise CredentialsException()
    return user
