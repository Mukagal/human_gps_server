from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query
from fastapi.responses import JSONResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional

from ..users.dependencies import get_current_user
from ..config import Config
from ..users.utils import (
    create_access_token, verify_password,
    decode_token, add_jti_to_blocklist, is_jti_blocked
)
from ..db.main import get_session
from .UserService import UserService
from .UserSchemas import UserCreate, UserPublic, UserUpdate, UserLogin, UserModel, UserSafe
from ..db.models import User

user_router = APIRouter()
user_service = UserService()
security = HTTPBearer()



@user_router.get("/users", response_model=List[UserSafe])
async def get_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, le=100),
    username: Optional[str] = Query(default=None, description="Search by username"),
    session: AsyncSession = Depends(get_session)
):
    users = await user_service.get_all_users(session, username=username)
    return users[skip: skip + limit]


@user_router.get("/users/{user_id}/profile", response_model=UserPublic)
async def get_user_profile(
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    user = await user_service.get_user(user_id, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@user_router.get("/users/{user_id}/profile-image")
async def get_profile_image(
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    user = await user_service.get_user(user_id, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.profile_image_path:
        raise HTTPException(status_code=404, detail="No profile image uploaded")
    return RedirectResponse(url=user.profile_image_path)



@user_router.post("/signup", response_model=UserModel, status_code=status.HTTP_201_CREATED)
async def create_user_account(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    user_exists = await user_service.user_exists(user_data.email, session)
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    new_user = await user_service.create_user(user_data, session)
    return new_user


@user_router.post("/login")
async def login_users(
    login_data: UserLogin,
    session: AsyncSession = Depends(get_session)
):
    user = await user_service.get_user_by_email(login_data.email, session)

    if user and verify_password(login_data.password, user.password):
        access_token = create_access_token(
            user_data={"email": user.email, "user_id": str(user.id)}
        )
        refresh_token = create_access_token(
            user_data={"email": user.email, "user_id": str(user.id)},
            refresh=True,
            expiry=timedelta(days=Config.REFRESH_TOKEN_EXPIRY),
        )
        return JSONResponse(content={
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {"email": user.email, "id": str(user.id)},
        })

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid email or password"
    )


@user_router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_data = decode_token(token)

    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    jti = token_data.get("jti")
    if not jti:
        raise HTTPException(status_code=401, detail="Token has no jti")

    await add_jti_to_blocklist(jti)
    return {"message": "Logged out successfully"}


@user_router.post("/refresh")
async def refresh_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_data = decode_token(token)

    if not token_data or not token_data.get("refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provide a valid refresh token"
        )

    jti = token_data.get("jti")
    if jti and await is_jti_blocked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked"
        )

    new_access_token = create_access_token(
        user_data=token_data["user"]
    )
    return {"access_token": new_access_token}



@user_router.get("/users/me", response_model=UserModel)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """Returns the currently logged in user's full profile."""
    return current_user


@user_router.get("/users/{user_id}", response_model=UserSafe)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    user = await user_service.get_user(user_id, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@user_router.patch("/users/me", response_model=UserModel)
async def update_user(
    update_data: UserUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user = await user_service.update_user(current_user.id, update_data, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@user_router.delete("/users/me", status_code=204)
async def delete_user(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    deleted = await user_service.delete_user(current_user.id, session)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")


@user_router.post("/users/me/profile-image", response_model=UserModel)
async def upload_profile_image(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    user = await user_service.upload_profile_image(current_user.id, file, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user



@user_router.get("/users/{user_id}/liked-posts")
async def get_user_liked_posts(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    from ..post.PostService import PostService
    return await PostService().get_posts_i_liked(user_id, session)


@user_router.get("/users/{user_id}/commented-posts")
async def get_user_commented_posts(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    from ..post.PostService import PostService
    return await PostService().get_posts_i_commented(user_id, session)


@user_router.get("/users/{user_id}/shared-posts")
async def get_user_shared_posts(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    from ..post.PostService import PostService
    return await PostService().get_posts_i_shared(user_id, session)