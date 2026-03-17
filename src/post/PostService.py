from sqlmodel import select, desc, func
from sqlmodel.ext.asyncio.session import AsyncSession

from src.messages import MessageService
from ..messages.MessageSchemas import MessageSend
from ..db.models import Conversation, GroupMember, Post, PostLike, PostComment, PostShare, User, Message
from .PostSchemas import PostCreate, PostUpdate, CommentCreate, ShareRequest, SortBy
from ..errors import PostNotFoundError, PostOwnershipError
import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile
from ..config import Config

cloudinary.config(
    cloud_name=Config.CLOUDINARY_CLOUD_NAME,
    api_key=Config.CLOUDINARY_API_KEY,
    api_secret=Config.CLOUDINARY_API_SECRET
)

class PostService:
    async def _get_post(self, post_id: int, session: AsyncSession) -> Post:
        result = await session.exec(select(Post).where(Post.id == post_id))
        post = result.first()
        if not post:
            raise PostNotFoundError()
        return post

    def _to_response(self, post: Post) -> dict:
        return {
            "id": post.id,
            "author_id": post.author_id,
            "content": post.content,
            "image_path": post.image_path,
            "created_at": post.created_at,
            "like_count": len(post.likes),
            "comment_count": len(post.comments),
            "share_count": len(post.shares),
        }


    async def get_feed(
        self,
        session: AsyncSession,
        sort_by: SortBy = SortBy.latest,
        keyword: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list:
        statement = select(Post)

        if keyword:
            statement = statement.where(Post.content.ilike(f"%{keyword}%"))

        result = await session.exec(statement)
        posts = list(result.all())

        if sort_by == SortBy.latest:
            posts.sort(key=lambda p: p.created_at, reverse=True)
        elif sort_by == SortBy.likes:
            posts.sort(key=lambda p: len(p.likes), reverse=True)
        elif sort_by == SortBy.comments:
            posts.sort(key=lambda p: len(p.comments), reverse=True)

        return [self._to_response(p) for p in posts[skip: skip + limit]]

    async def get_post(self, post_id: int, session: AsyncSession) -> dict:
        post = await self._get_post(post_id, session)
        return self._to_response(post)

    async def get_user_posts(
        self, user_id: int, session: AsyncSession,
        sort_by: SortBy = SortBy.latest,
        skip: int = 0, limit: int = 20
    ) -> list:
        result = await session.exec(select(Post).where(Post.author_id == user_id))
        posts = list(result.all())

        if sort_by == SortBy.latest:
            posts.sort(key=lambda p: p.created_at, reverse=True)
        elif sort_by == SortBy.likes:
            posts.sort(key=lambda p: len(p.likes), reverse=True)
        elif sort_by == SortBy.comments:
            posts.sort(key=lambda p: len(p.comments), reverse=True)

        return [self._to_response(p) for p in posts[skip: skip + limit]]


    async def create_post(self, author_id: int, data: PostCreate, session: AsyncSession):
        post = Post(author_id=author_id, **data.model_dump())
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return self._to_response(post)

    async def update_post(self, post_id: int, user_id: int, data: PostUpdate, session: AsyncSession):
        post = await self._get_post(post_id, session)
        if post.author_id != user_id:
            raise PostOwnershipError()
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(post, k, v)
        await session.commit()
        await session.refresh(post)
        return self._to_response(post)
    
    async def delete_post(self,post_id: int, user_id: int, session: AsyncSession ) -> None:
        post = await self._get_post(post_id, session)

        if post.author_id != user_id:
            raise PostOwnershipError() 

        await session.delete(post)
        await session.commit()

    async def create_post_with_image(self, author_id: int, content: str, file: UploadFile | None, session: AsyncSession):
        image_url = None
        if file and file.content_type and file.content_type.startswith("image/"):
            file_bytes = await file.read()  
            result = cloudinary.uploader.upload(
                file_bytes,          
                folder="post_images",
                transformation=[{"width": 1080, "height": 1080, "crop": "limit"}]
            )
            image_url = result["secure_url"]
        post = Post(author_id=author_id, content=content, image_path=image_url)
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return self._to_response(post)


    async def like_post(self, post_id: int, user_id: int, session: AsyncSession):
        await self._get_post(post_id, session)

        existing = await session.exec(
            select(PostLike).where(
                PostLike.post_id == post_id,
                PostLike.user_id == user_id
            )
        )
        if existing.first():
            result = await session.exec(
                select(func.count()).where(PostLike.post_id == post_id)  # type: ignore
            )
            return {"post_id": post_id, "likes": result.one()}

        like = PostLike(post_id=post_id, user_id=user_id)
        session.add(like)
        await session.commit()

        result = await session.exec(
            select(func.count(PostLike.id)).where(PostLike.post_id == post_id)
        )
        return {"post_id": post_id, "likes": result.one()}

    async def unlike_post(self, post_id: int, user_id: int, session: AsyncSession):
        await self._get_post(post_id, session)

        existing = await session.exec(
            select(PostLike).where(
                PostLike.post_id == post_id,
                PostLike.user_id == user_id
            )
        )
        like = existing.first()
        if not like:
            return {"post_id": post_id, "likes": 0}  # nothing to unlike

        await session.delete(like)
        await session.commit()

        result = await session.exec(
            select(func.count(PostLike.id)).where(PostLike.post_id == post_id)
        )
        return {"post_id": post_id, "likes": result.one()}


    async def add_comment(self, post_id: int, author_id: int, data: CommentCreate, session: AsyncSession):
        await self._get_post(post_id, session)
        comment = PostComment(post_id=post_id, author_id=author_id, content=data.content)
        session.add(comment)
        await session.commit()
        await session.refresh(comment)
        user_result = await session.exec(select(User.username).where(User.id == author_id))
        username = user_result.first()
        return {
            "id": comment.id,
            "post_id": comment.post_id,
            "author_id": comment.author_id,
            "content": comment.content,
            "created_at": comment.created_at,
            "author_username": username
        }

    async def get_comments(self, post_id: int, session: AsyncSession):
        await self._get_post(post_id, session)
        result = await session.exec(
            select(PostComment, User.username)
            .join(User, User.id == PostComment.author_id)
            .where(PostComment.post_id == post_id)
            .order_by(desc(PostComment.created_at))
        )
        rows = result.all()
        comments = []
        for comment, username in rows:
            comments.append({
                "id": comment.id,
                "post_id": comment.post_id,
                "author_id": comment.author_id,
                "content": comment.content,
                "created_at": comment.created_at,
                "author_username": username
            })
        return comments

    async def delete_comment(self, comment_id: int, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(PostComment).where(PostComment.id == comment_id)
        )
        comment = result.first()
        if not comment:
            from ..errors import CommentNotFoundError
            raise CommentNotFoundError()
        if comment.author_id != user_id:
            from ..errors import CommentOwnershipError
            raise CommentOwnershipError()
        await session.delete(comment)
        await session.commit()


    async def share_post(self, post_id: int, user_id: int, data: ShareRequest, session: AsyncSession, base_url: str = ""):
        await self._get_post(post_id, session)

        if not data.conversation_id and not data.group_id:
            raise HTTPException(
                status_code=400,
                detail="Provide conversation_id or group_id"
            )

        if data.conversation_id and data.group_id:
            raise HTTPException(
                status_code=400,
                detail="Share either to conversation OR group"
            )

        if data.conversation_id:

            statement = select(Conversation).where(
                Conversation.id == data.conversation_id
            )

            result = await session.exec(statement)
            conversation = result.first()

            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

            if user_id not in [conversation.user1_id, conversation.user2_id]:
                raise HTTPException(
                    status_code=403,
                    detail="You are not part of this conversation"
                )

        if data.group_id:

            statement = select(GroupMember).where(
                GroupMember.group_id == data.group_id,
                GroupMember.user_id == user_id
            )

            result = await session.exec(statement)
            member = result.first()

            if not member:
                raise HTTPException(
                    status_code=403,
                    detail="You are not a member of this group"
                )

        share_link = f"{base_url}/api/v1/posts/{post_id}/view"

        share = PostShare(
            post_id=post_id,
            shared_by=user_id,
            conversation_id=data.conversation_id,
            group_id=data.group_id,
            share_link=share_link
        )

        session.add(share)
        await session.commit()
        await session.refresh(share)
        await MessageService().send_message(
            conversation_id=data.conversation_id,
            message_data=MessageSend(content=f"[shared_post:{post_id}] {share_link}"),
            sender_id=user_id,
            session=session
        )

        return share

    async def get_post_likers(self, post_id: int, owner_id: int, session: AsyncSession):
        post = await self._get_post(post_id, session)
        if post.author_id != owner_id:
            raise PostOwnershipError()

        result = await session.exec(
            select(PostLike).where(PostLike.post_id == post_id)
            .order_by(desc(PostLike.liked_at))
        )
        return result.all()

    async def get_post_commenters(self, post_id: int, session: AsyncSession):
        await self._get_post(post_id, session)
        result = await session.exec(
            select(PostComment).where(PostComment.post_id == post_id)
            .order_by(desc(PostComment.created_at))
        )
        return result.all()

    async def get_post_sharers(self, post_id: int, owner_id: int, session: AsyncSession):
        post = await self._get_post(post_id, session)
        if post.author_id != owner_id:
            raise PostOwnershipError()

        result = await session.exec(
            select(PostShare).where(PostShare.post_id == post_id)
            .order_by(desc(PostShare.shared_at))
        )
        return result.all()

    async def get_all_interactions_on_my_posts(self, owner_id: int, session: AsyncSession):
        result = await session.exec(
            select(Post).where(Post.author_id == owner_id)
        )
        posts = result.all()

        return [
            {
                "post_id": p.id,
                "content_preview": p.content[:60],
                "like_count": len(p.likes),
                "comment_count": len(p.comments),
                "share_count": len(p.shares),
            }
            for p in posts
        ]

    async def get_posts_i_liked(self, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(PostLike).where(PostLike.user_id == user_id)
            .order_by(desc(PostLike.liked_at))
        )
        likes = result.all()
        post_ids = [like.post_id for like in likes]

        if not post_ids:
            return []

        posts_result = await session.exec(
            select(Post).where(Post.id.in_(post_ids))
        )
        posts = {p.id: p for p in posts_result.all()}

        return [
            {
                **self._to_response(posts[like.post_id]),
                "liked_at": like.liked_at,
            }
            for like in likes
            if like.post_id in posts
        ]

    async def get_posts_i_commented(self, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(PostComment).where(PostComment.author_id == user_id)
            .order_by(desc(PostComment.created_at))
        )
        comments = result.all()

        if not comments:
            return []

        post_ids = list({c.post_id for c in comments})
        posts_result = await session.exec(
            select(Post).where(Post.id.in_(post_ids))
        )
        posts = {p.id: self._to_response(p) for p in posts_result.all()}

        return [
            {
                "comment_id": c.id,
                "comment_content": c.content,
                "commented_at": c.created_at,
                "post": posts.get(c.post_id),
            }
            for c in comments
        ]

    async def get_posts_i_shared(self, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(PostShare).where(PostShare.shared_by == user_id)
            .order_by(desc(PostShare.shared_at))
        )
        shares = result.all()

        if not shares:
            return []

        post_ids = [s.post_id for s in shares]
        posts_result = await session.exec(
            select(Post).where(Post.id.in_(post_ids))
        )
        posts = {p.id: self._to_response(p) for p in posts_result.all()}

        return [
            {
                "share_id": s.id,
                "share_link": s.share_link,
                "shared_to_conversation": s.conversation_id,
                "shared_to_group": s.group_id,
                "shared_at": s.shared_at,
                "post": posts.get(s.post_id),
            }
            for s in shares
        ]