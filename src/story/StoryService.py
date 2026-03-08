from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime
from ..db.models import Story
from .StorySchemas import StoryCreate

class StoryService:

    async def create_story(self, story_data: StoryCreate, session: AsyncSession):
        new_story = Story(**story_data.model_dump())
        session.add(new_story)
        await session.commit()
        await session.refresh(new_story)
        return new_story

    async def get_active_stories(self, session: AsyncSession):
        result = await session.exec(
            select(Story).where(Story.expires_at > datetime.utcnow())
        )
        return result.all()

    async def delete_story(self, story_id: int, session: AsyncSession):
        result = await session.exec(select(Story).where(Story.id == story_id))
        story = result.first()
        if not story:
            return None
        await session.delete(story)
        await session.commit()
        return True