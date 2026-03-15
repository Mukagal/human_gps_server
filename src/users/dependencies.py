
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession
from ..db.main import get_session
from ..users.UserService import UserService
from ..users.utils import decode_token
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
):
    token = credentials.credentials
    token_data = decode_token(token)  
    if not token_data or token_data.get("refresh"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    
    user = await UserService().get_user_by_email(token_data["user"]["email"], session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    session: AsyncSession = Depends(get_session)
):
    if not credentials:
        return None
    token_data = decode_token(credentials.credentials)
    if not token_data or token_data.get("refresh"):
        return None
    return await UserService().get_user_by_email(token_data["user"]["email"], session)