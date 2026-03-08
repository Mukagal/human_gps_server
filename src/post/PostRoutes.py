from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from ..db.main import get_session
from .PostService import PostService
from .PostSchemas import PostCreate
from ..db.models import Post


post_router = APIRouter()
post_service = PostService()

@post_router.post("/posts")
async def create_post(
    post_data: PostCreate,
    session: AsyncSession = Depends(get_session)
):
    return await post_service.create_post(post_data, session)

@post_router.get("/posts", response_model=List[Post])
async def get_feed(
    skip: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session)
):
    posts = await post_service.get_feed(session)
    return posts[skip: skip + limit]

@post_router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    session: AsyncSession = Depends(get_session)
):
    deleted = await post_service.delete_post(post_id, session)

    if not deleted:
        raise HTTPException(status_code=404, detail="Post not found")

    return {"message": "Deleted"}