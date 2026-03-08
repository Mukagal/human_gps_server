from sqlmodel import select, desc
from ..db.models import Post
from sqlmodel.ext.asyncio.session import AsyncSession


class PostService:

    async def create_post(self, post_data, session: AsyncSession):

        new_post = Post(**post_data.model_dump())

        session.add(new_post)
        await session.commit()
        await session.refresh(new_post)

        return new_post

    async def get_feed(self, session: AsyncSession):

        statement = select(Post).order_by(desc(Post.created_at))

        result = await session.exec(statement)
        return result.all()

    async def delete_post(self, post_id: int, session: AsyncSession):

        result = await session.exec(
            select(Post).where(Post.id == post_id)
        )

        post = result.first()

        if not post:
            return None

        await session.delete(post)
        await session.commit()

        return True