from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from ..db.main import get_session
from .StoryService import StoryService
from .StorySchemas import StoryCreate

story_router = APIRouter()
story_service = StoryService()

@story_router.post("/stories")
async def create_story(story_data: StoryCreate, session: AsyncSession = Depends(get_session)):
    return await story_service.create_story(story_data, session)

@story_router.get("/stories")
async def get_active_stories(session: AsyncSession = Depends(get_session)):
    return await story_service.get_active_stories(session)

@story_router.delete("/stories/{story_id}")
async def delete_story(story_id: int, session: AsyncSession = Depends(get_session)):
    deleted = await story_service.delete_story(story_id, session)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"message": "Deleted"}