from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

from ..db.main import get_session
from ..users.dependencies import get_current_user
from ..users.dependencies import get_optional_user   # explained below
from ..db.models import User
from .PostService import PostService
from .PostSchemas import (
    PostCreate, PostUpdate, PostResponse,
    CommentCreate, CommentResponse,
    ShareRequest, ShareResponse,
    SortBy
)
from fastapi import File, UploadFile


post_router = APIRouter()
post_service = PostService()



@post_router.get("/posts", response_model=List[PostResponse])
async def get_feed(
    sort_by: SortBy = Query(default=SortBy.latest),
    keyword: Optional[str] = Query(default=None, description="Search in post content"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, le=100),
    session: AsyncSession = Depends(get_session)
):
    return await post_service.get_feed(session, sort_by, keyword, skip, limit)


@post_router.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    session: AsyncSession = Depends(get_session)
):
    return await post_service.get_post(post_id, session)


@post_router.get("/users/{user_id}/posts", response_model=List[PostResponse])
async def get_user_posts(
    user_id: int,
    sort_by: SortBy = Query(default=SortBy.latest),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, le=100),
    session: AsyncSession = Depends(get_session)
):
    return await post_service.get_user_posts(user_id, session, sort_by, skip, limit)


@post_router.get("/posts/{post_id}/view")
async def view_shared_post(
    post_id: int,
    session: AsyncSession = Depends(get_session)
):
    return await post_service.get_post(post_id, session)


@post_router.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
async def get_comments(
    post_id: int,
    session: AsyncSession = Depends(get_session)
):
    return await post_service.get_comments(post_id, session)



@post_router.post("/posts", response_model=PostResponse, status_code=201)
async def create_post(
    post_data: PostCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await post_service.create_post(current_user.id, post_data, session)

@post_router.post("/posts/{post_id}/image", response_model=PostResponse)
async def upload_post_image(
    post_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    return await post_service.upload_post_image(post_id, current_user.id, file, session)

@post_router.patch("/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    update_data: PostUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await post_service.update_post(post_id, current_user.id, update_data, session)


@post_router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    await post_service.delete_post(post_id, current_user.id, session)



@post_router.post("/posts/{post_id}/like")
async def like_post(
    post_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await post_service.like_post(post_id, current_user.id, session)


@post_router.delete("/posts/{post_id}/like")
async def unlike_post(
    post_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await post_service.unlike_post(post_id, current_user.id, session)



@post_router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    post_id: int,
    comment_data: CommentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await post_service.add_comment(post_id, current_user.id, comment_data, session)


@post_router.delete("/posts/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    await post_service.delete_comment(comment_id, current_user.id, session)

@post_router.post("/posts/{post_id}/share", response_model=ShareResponse, status_code=201)
async def share_post(
    post_id: int,
    share_data: ShareRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    base_url = str(request.base_url).rstrip("/")
    return await post_service.share_post(post_id, current_user.id, share_data, session, base_url)

@post_router.get("/posts/{post_id}/likes")
async def get_post_likers(
    post_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await post_service.get_post_likers(post_id, current_user.id, session)


@post_router.get("/posts/{post_id}/shares")
async def get_post_sharers(
    post_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await post_service.get_post_sharers(post_id, current_user.id, session)


@post_router.get("/me/posts/interactions")
async def my_posts_interactions_dashboard(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await post_service.get_all_interactions_on_my_posts(current_user.id, session)



@post_router.get("/me/liked-posts")
async def posts_i_liked(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await post_service.get_posts_i_liked(current_user.id, session)


@post_router.get("/me/commented-posts")
async def posts_i_commented(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await post_service.get_posts_i_commented(current_user.id, session)


@post_router.get("/me/shared-posts")
async def posts_i_shared(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await post_service.get_posts_i_shared(current_user.id, session)