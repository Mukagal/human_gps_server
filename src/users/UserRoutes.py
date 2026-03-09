from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from src.users.dependencies import get_current_user

from ..config import Config
from ..users.utils import create_access_token, verify_password

from ..db.main import get_session
from .UserService import UserService
from .UserSchemas import UserCreate, UserPublic, UserUpdate, UserLogin, UserModel
from ..db.models import User

user_router = APIRouter()
user_service = UserService()

@user_router.get("/users", response_model=List[User])
async def get_users(
    skip: int = 0,
    limit: int = 10,
    session: AsyncSession = Depends(get_session)
):
    users = await user_service.get_all_users(session)
    return users[skip: skip + limit]

@user_router.post(
    "/signup", response_model=UserModel, status_code=status.HTTP_201_CREATED
)
async def create_user_account(
    user_data: UserCreate, session: AsyncSession = Depends(get_session)
):
    email = user_data.email

    user_exists = await user_service.user_exists(email, session)

    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User with email already exists",
        )

    new_user = await user_service.create_user(user_data, session)

    return new_user

@user_router.post("/login")
async def login_users(
    login_data: UserLogin, session: AsyncSession = Depends(get_session)
):
    email = login_data.email
    password = login_data.password

    user = await user_service.get_user_by_email(email, session)

    if user is not None:
        password_valid = verify_password(password, user.password)

        if password_valid:
            access_token = create_access_token(
                user_data={"email": user.email, "user_id": str(user.id)}
            )

            refresh_token = create_access_token(
                user_data={"email": user.email, "user_id": str(user.id)},
                refresh=True,
                expiry=timedelta(days=Config.REFRESH_TOKEN_EXPIRY),
            )

            return JSONResponse(
                content={
                    "message": "Login successful",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {"email": user.email, "id": str(user.id)},
                }
            )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Email Or Password"
    )

@user_router.get("/users/{user_id}", response_model=User)
async def get_user(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    user = await user_service.get_user(current_user.id, session)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@user_router.patch("/users/{user_id}")
async def update_user(
    update_data: UserUpdate,
    session: AsyncSession = Depends(get_session),    
    current_user: User = Depends(get_current_user),
):
    user = await user_service.update_user(current_user.id, update_data, session)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

@user_router.delete("/users/")
async def delete_user(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    deleted = await user_service.delete_user(current_user.id, session)
    if deleted is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"User witb id {current_user.id} Deleted"}

@user_router.get("/users/{user_id}/profile", response_model=UserPublic)
async def get_user_profile(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)  
):
    user = await user_service.get_user(user_id, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user