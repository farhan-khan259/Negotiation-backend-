from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.crud import crud_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    # In token payload we used 'sub' as user id (int)
    # But usually sub is string. Let's cast or handle based on how we encoded it.
    # In security.py we put `to_encode.update({"exp": expire})`. We need to add sub.
    # Wait, I didn't add 'sub' in security.py create_access_token call in my head plan.
    # I should ensure the auth endpoint does that.
    
    user_id = token_data.sub
    if user_id is None:
         raise HTTPException(status_code=404, detail="User not found")
         
    # crud_user.get uses sync logic in some frameworks but here it is async
    # I need a get_by_id in crud_user
    result = await db.get(User, int(user_id))
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result

async def get_current_user_optional(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme_optional),
) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        return None

    user_id = token_data.sub
    if user_id is None:
        return None
    return await db.get(User, int(user_id))
