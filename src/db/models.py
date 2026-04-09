from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, timedelta
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
import enum


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)

    username: str = Field(index=True, nullable=False)
    email: str = Field(index=True, nullable=False, unique=True)
    password: str
    role: str = Field(
        sa_column=Column(pg.VARCHAR, nullable=False, server_default="user")
    )
    is_verified: bool = Field(default=False)
    is_banned: bool = Field(default=False)
    ban_reason: Optional[str] = Field(default=None)
    verification_token: Optional[str] = Field(default=None)

    profile_image_path: Optional[str] = None
    latitude: Optional[float] = Field(default=None, nullable=True)
    longitude: Optional[float] = Field(default=None, nullable=True)
    rating: float = Field(default=0.0)

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )

    sent_messages: List["Message"] = Relationship(
        back_populates="sender",
        sa_relationship_kwargs={"foreign_keys": "[Message.sender_id]"}
    )

    received_messages: List["Message"] = Relationship(
        back_populates="receiver",
        sa_relationship_kwargs={"foreign_keys": "[Message.receiver_id]"}
    )
    stories: List["Story"] = Relationship(back_populates="author")


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    __table_args__ = (
        UniqueConstraint("user1_id", "user2_id", name="unique_conversation"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    user1_id: int = Field(foreign_key="users.id")
    user2_id: int = Field(foreign_key="users.id")

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )

    messages: List["Message"] = Relationship(back_populates="conversation")


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)

    content: str

    conversation_id: int = Field(foreign_key="conversations.id")

    sender_id: int = Field(foreign_key="users.id")
    receiver_id: int = Field(foreign_key="users.id")

    sent_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )

    received_at: Optional[datetime] = None

    conversation: Optional[Conversation] = Relationship(back_populates="messages")

    sender: Optional[User] = Relationship(
        back_populates="sent_messages",
        sa_relationship_kwargs={"foreign_keys": "[Message.sender_id]"}
    )

    receiver: Optional[User] = Relationship(
        back_populates="received_messages",
        sa_relationship_kwargs={"foreign_keys": "[Message.receiver_id]"}
    )

class Post(SQLModel, table=True):
    __tablename__ = "posts"

    id: Optional[int] = Field(default=None, primary_key=True)
    author_id: int = Field(foreign_key="users.id")
    content: str
    image_path: Optional[str] = None
    is_flagged: bool = Field(default=False)
    flag_reason: Optional[str] = Field(default=None)

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )

    likes: List["PostLike"] = Relationship(
        back_populates="post",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan"
        }
    )

    comments: List["PostComment"] = Relationship(
        back_populates="post",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan"
        }
    )

    shares: List["PostShare"] = Relationship(
        back_populates="post",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan"
        }
    )

class PostLike(SQLModel, table=True):
    __tablename__ = "post_likes"

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="unique_post_like"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False
        )
    )
    user_id: int = Field(foreign_key="users.id")

    liked_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )

    post: Optional["Post"] = Relationship(back_populates="likes")


class PostComment(SQLModel, table=True):
    __tablename__ = "post_comments"

    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False
        )
    )
    author_id: int = Field(foreign_key="users.id")
    content: str

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )

    post: Optional["Post"] = Relationship(back_populates="comments")


class PostShare(SQLModel, table=True):
    __tablename__ = "post_shares"

    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False
        )
    )
    shared_by: int = Field(foreign_key="users.id")

    conversation_id: Optional[int] = Field(default=None, foreign_key="conversations.id")
    group_id: Optional[int] = Field(default=None, foreign_key="group_chats.id")

    share_link: str  

    shared_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )

    post: Optional["Post"] = Relationship(back_populates="shares")

class Story(SQLModel, table=True):
    __tablename__ = "stories"

    id: Optional[int] = Field(default=None, primary_key=True)
    author_id: int = Field(foreign_key="users.id")
    image_path: str
    caption: Optional[str] = None

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )
    expires_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            default=lambda: datetime.utcnow() + timedelta(hours=24)
        )
    )

    author: Optional[User] = Relationship(back_populates="stories")

class GroupChat(SQLModel, table=True):
    __tablename__ = "group_chats"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_by: int = Field(foreign_key="users.id")

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )

    members: List["GroupMember"] = Relationship(back_populates="group")
    messages: List["GroupMessage"] = Relationship(back_populates="group")


class GroupMember(SQLModel, table=True):
    __tablename__ = "group_members"

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="unique_group_member"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group_chats.id")
    user_id: int = Field(foreign_key="users.id")
    joined_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )

    group: Optional[GroupChat] = Relationship(back_populates="members")


class GroupMessage(SQLModel, table=True):
    __tablename__ = "group_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group_chats.id")
    sender_id: int = Field(foreign_key="users.id")
    content: str

    sent_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )

    group: Optional[GroupChat] = Relationship(back_populates="messages")


class HelpCategory(str, enum.Enum):
    TUTOR = "tutor"
    PHYSICAL = "physical"
    RENTAL = "rental"
    OTHER = "other"

class RequestStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RequestHelp(SQLModel, table=True):
    __tablename__ = "request_helps"

    id: Optional[int] = Field(default=None, primary_key=True)
    requester_id: int = Field(foreign_key="users.id")

    title: str
    description: str
    category: HelpCategory

    status: RequestStatus = Field(default=RequestStatus.OPEN)

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )
    expires_at: Optional[datetime] = None

    applications: List["HelpApplication"] = Relationship(
        back_populates="request",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class HelpApplication(SQLModel, table=True):
    __tablename__ = "help_applications"

    __table_args__ = (
        UniqueConstraint("request_id", "applicant_id", name="unique_help_application"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("request_helps.id", ondelete="CASCADE"),
            nullable=False
        )
    )
    applicant_id: int = Field(foreign_key="users.id")
    message: Optional[str] = None

    status: ApplicationStatus = Field(default=ApplicationStatus.PENDING)

    applied_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )

    request: Optional[RequestHelp] = Relationship(back_populates="applications")

class UserCompressedImage(SQLModel, table=True):
    __tablename__ = "user_compressed_images"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)
    image_data: bytes = Field(sa_column=Column(pg.BYTEA, nullable=False))
    original_size: int
    compressed_size: int
    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )


class UserRating(SQLModel, table=True):
    __tablename__ = "user_ratings"

    id: Optional[int] = Field(default=None, primary_key=True)
    rater_id: int = Field(foreign_key="users.id")
    target_user_id: int = Field(foreign_key="users.id")
    request_id: int = Field(foreign_key="request_helps.id")
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )