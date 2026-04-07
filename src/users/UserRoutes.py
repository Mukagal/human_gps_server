from datetime import timedelta
import io
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query, Request
from sqlmodel import select
from fastapi.responses import JSONResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from ..tasks.moderation_task import moderate_profile_image
from ..middlware.rate_limit import limiter, WRITE_LIMIT, GENERAL_LIMIT_MIN
from ..users.dependencies import RoleChecker, get_current_user
from ..config import Config
from ..users.utils import (
    create_access_token, generate_password_hash, verify_password,
    decode_token, add_jti_to_blocklist, is_jti_blocked
)
from ..db.main import get_session
from .UserService import UserService
from .UserSchemas import PasswordReset, UserCreate, UserPublic, UserUpdate, UserLogin, UserModel, UserSafe, UserLocationUpdate
from ..db.models import User
from ..tasks.image_task import compress_and_store_image
from ..tasks.mail_task import send_password_reset_email
from ..config import Config
import base64

user_router = APIRouter()
user_service = UserService()
security = HTTPBearer()

admin_only = RoleChecker(["admin"])

@user_router.delete("/admin/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_only)  
):
    deleted = await user_service.delete_user(user_id, session)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return deleted

    

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
    if user.is_banned:
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
@limiter.limit(WRITE_LIMIT)
async def create_user_account(
    request: Request,
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

@user_router.post("/signup-with-verification", response_model=UserModel, status_code=status.HTTP_201_CREATED)
@limiter.limit(WRITE_LIMIT)
async def create_user_account_with_verification(
    request: Request,
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
    
    from ..tasks.mail_task import send_confirmation_email
    send_confirmation_email.delay(new_user.email, new_user.username, new_user.verification_token)
    
    return new_user

@user_router.post("/login")
@limiter.limit("20/minute")
async def login_users(
    request:Request,
    login_data: UserLogin,
    session: AsyncSession = Depends(get_session)
):
    user = await user_service.get_user_by_email(login_data.email, session)

    if user and verify_password(login_data.password, user.password):
        if user.is_banned:
            raise HTTPException(
                status_code=403,
                detail=f"Your account has been banned. Reason: {user.ban_reason or 'Policy violation'}"
            )
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

@user_router.get("/users/nearby")
async def get_nearby_users(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=10.0, gt=0, le=500),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    results = await user_service.get_nearby_users(latitude, longitude, radius_km, session)
    return [
        {
            "id": r["user"].id,
            "username": r["user"].username,
            "profile_image_path": r["user"].profile_image_path,
            "distance_km": r["distance_km"],
        }
        for r in results
    ]

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
):
    user = await user_service.get_user(user_id, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_banned:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@user_router.patch("/users/me", response_model=UserModel)
@limiter.limit(WRITE_LIMIT)
async def update_user(
    request:Request,
    update_data: UserUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user = await user_service.update_user(current_user.id, update_data, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@user_router.delete("/users/me", status_code=204)
@limiter.limit(WRITE_LIMIT)
async def delete_user(
    request:Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    deleted = await user_service.delete_user(current_user.id, session)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")

@user_router.post("/users/me/profile-image", response_model=UserModel)
@limiter.limit(WRITE_LIMIT)
async def upload_profile_image(
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    image_bytes = await file.read()
    file.file = io.BytesIO(image_bytes)
    
    user = await user_service.upload_profile_image(current_user.id, file, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    b64 = base64.b64encode(image_bytes).decode()
    moderate_profile_image.delay(current_user.id, b64, Config.DATABASE_URL)
    
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

@user_router.patch("/users/me/location", response_model=UserModel)
@limiter.limit(WRITE_LIMIT)
async def update_my_location(
    request:Request,
    location: UserLocationUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user = await user_service.update_location(current_user.id, location.latitude, location.longitude, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@user_router.get("/users/{user_id}/location")
async def get_user_location(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user = await user_service.get_user(user_id, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.latitude is None or user.longitude is None:
        raise HTTPException(status_code=404, detail="User has not set a location")
    return {"user_id": user_id, "latitude": user.latitude, "longitude": user.longitude}

@user_router.post("/users/me/profile-image-compressed")
@limiter.limit(WRITE_LIMIT)
async def upload_profile_image_with_compression(
    request:Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()

    b64 = base64.b64encode(image_bytes).decode()
    compress_and_store_image.delay(current_user.id, b64, Config.DATABASE_URL)
    
    moderate_profile_image.delay(current_user.id, b64, Config.DATABASE_URL)

    return {"message": "Upload started. Compression running in background.", "user": current_user}

@user_router.get("/verify-email")
async def verify_email(
    token: str,
    session: AsyncSession = Depends(get_session)
):
    
    result = await session.exec(select(User).where(User.verification_token == token))
    user = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    user.is_verified = True
    user.verification_token = None
    await session.commit()
    return {"message": "Email verified successfully"}

@user_router.post("/forgot-password")
@limiter.limit(WRITE_LIMIT)
async def forgot_password(
    request:Request,
    email: str,
    session: AsyncSession = Depends(get_session)
):
    user = await user_service.get_user_by_email(email, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token = secrets.token_urlsafe(32)
    user.verification_token = token
    await session.commit()
    send_password_reset_email.delay(user.email, token)
    return {"message": "Password reset email sent"}

@user_router.post("/reset-password")
async def reset_password(
    data: PasswordReset,
    session: AsyncSession = Depends(get_session)
):
    result = await session.exec(select(User).where(User.verification_token == data.token))
    user = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    user.password = generate_password_hash(data.new_password)
    user.verification_token = None
    await session.commit()
    return {"message": "Password reset successfully"}