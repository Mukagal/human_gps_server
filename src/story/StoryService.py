import cloudinary.uploader
from fastapi import HTTPException, UploadFile
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime
from ..db.models import Story
from .StorySchemas import StoryCreate

class StoryService:

    async def create_story(self, author_id: int, story_data: StoryCreate, session: AsyncSession):
        new_story = Story(
            author_id=author_id,
            **story_data.model_dump()
        )

        session.add(new_story)
        await session.commit()
        await session.refresh(new_story)

        return new_story

    async def get_active_stories(self, session: AsyncSession):
        result = await session.exec(
            select(Story).where(Story.expires_at > datetime.utcnow())
        )
        return result.all()

    async def delete_story(self, story_id: int, user_id: int, session: AsyncSession):
        result = await session.exec(select(Story).where(Story.id == story_id))
        story = result.first()

        if not story:
            return None

        if story.author_id != user_id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not your story")

        await session.delete(story)
        await session.commit()

        return True
    
    async def create_story_with_image(
        self,
        author_id: int,
        caption: str | None,
        file: UploadFile,
        session: AsyncSession
    ):
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        file_bytes = await file.read()

        result = cloudinary.uploader.upload(
            file_bytes,
            folder="story_images",
            transformation=[{"width": 1080, "height": 1920, "crop": "limit"}]
        )

        image_url = result["secure_url"]

        story = Story(
            author_id=author_id,
            image_path=image_url,
            caption=caption
        )

        session.add(story)
        await session.commit()
        await session.refresh(story)

        return story

    