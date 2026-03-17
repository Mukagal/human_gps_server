from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db.main import get_session
from ..db.models import User
from ..users.dependencies import get_current_user
from .StoryService import StoryService

story_router = APIRouter()
story_service = StoryService()


@story_router.post("/stories")
async def create_story(
    caption: Optional[str] = Form(default=None),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await story_service.create_story_with_image(
        current_user.id,
        caption,
        file,
        session
    )


@story_router.get("/stories")
async def get_active_stories(session: AsyncSession = Depends(get_session)):
    return await story_service.get_active_stories(session)


@story_router.delete("/stories/{story_id}")
async def delete_story(
    story_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    deleted = await story_service.delete_story(story_id, current_user.id, session)

    if not deleted:
        raise HTTPException(status_code=404, detail="Story not found")

    return {"message": "Deleted"}