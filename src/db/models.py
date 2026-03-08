from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, timedelta
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, UniqueConstraint


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)

    username: str = Field(index=True, nullable=False)
    email: str = Field(index=True, nullable=False, unique=True)
    password: str

    profile_image_path: Optional[str] = None

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

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow)
    )

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