"""Initial schema - full migration

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create full schema from scratch."""

    # ------------------------------------------------------------------
    # ENUM TYPES — use DO blocks for compatibility with older PostgreSQL
    # ------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE helpcategory AS ENUM ('TUTOR', 'PHYSICAL', 'RENTAL', 'OTHER');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE requeststatus AS ENUM ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE applicationstatus AS ENUM ('PENDING', 'ACCEPTED', 'REJECTED');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('password', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('role', sa.VARCHAR(), server_default='user', nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_banned', sa.Boolean(), nullable=False),
        sa.Column('ban_reason', sa.VARCHAR(), nullable=True),
        sa.Column('verification_token', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('profile_image_path', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('rating', sa.Float(), nullable=False),
        sa.Column('professions', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Backfill non-nullable columns for existing rows (safe on fresh DB, required for existing)
    op.execute("UPDATE users SET is_banned = FALSE WHERE is_banned IS NULL")
    op.execute("UPDATE users SET rating = 0 WHERE rating IS NULL")

    # ------------------------------------------------------------------
    # conversations
    # ------------------------------------------------------------------
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user1_id', sa.Integer(), nullable=False),
        sa.Column('user2_id', sa.Integer(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['user1_id'], ['users.id']),
        sa.ForeignKeyConstraint(['user2_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user1_id', 'user2_id', name='unique_conversation'),
    )

    # ------------------------------------------------------------------
    # messages
    # ------------------------------------------------------------------
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('receiver_id', sa.Integer(), nullable=False),
        sa.Column('sent_at', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('received_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id']),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id']),
        sa.ForeignKeyConstraint(['receiver_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ------------------------------------------------------------------
    # group_chats
    # ------------------------------------------------------------------
    op.create_table(
        'group_chats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ------------------------------------------------------------------
    # group_members
    # ------------------------------------------------------------------
    op.create_table(
        'group_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('joined_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['group_chats.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'user_id', name='unique_group_member'),
    )

    # ------------------------------------------------------------------
    # group_messages
    # ------------------------------------------------------------------
    op.create_table(
        'group_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('content', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('sent_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['group_chats.id']),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ------------------------------------------------------------------
    # posts
    # ------------------------------------------------------------------
    op.create_table(
        'posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('content', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('image_path', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('is_flagged', sa.Boolean(), nullable=False),
        sa.Column('flag_reason', sa.VARCHAR(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.execute("UPDATE posts SET is_flagged = FALSE WHERE is_flagged IS NULL")

    # ------------------------------------------------------------------
    # post_likes
    # ------------------------------------------------------------------
    op.create_table(
        'post_likes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('liked_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id', 'user_id', name='unique_post_like'),
    )

    # ------------------------------------------------------------------
    # post_comments
    # ------------------------------------------------------------------
    op.create_table(
        'post_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('content', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ------------------------------------------------------------------
    # post_shares
    # ------------------------------------------------------------------
    op.create_table(
        'post_shares',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('shared_by', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=True),
        sa.Column('group_id', sa.Integer(), nullable=True),
        sa.Column('share_link', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('shared_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shared_by'], ['users.id']),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id']),
        sa.ForeignKeyConstraint(['group_id'], ['group_chats.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ------------------------------------------------------------------
    # stories
    # ------------------------------------------------------------------
    op.create_table(
        'stories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('image_path', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('caption', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('expires_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ------------------------------------------------------------------
    # user_compressed_images
    # ------------------------------------------------------------------
    op.create_table(
        'user_compressed_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('image_data', postgresql.BYTEA(), nullable=False),
        sa.Column('original_size', sa.Integer(), nullable=False),
        sa.Column('compressed_size', sa.Integer(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    # ------------------------------------------------------------------
    # request_helps
    # ------------------------------------------------------------------
    op.create_table(
        'request_helps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('requester_id', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('category', postgresql.ENUM('TUTOR', 'PHYSICAL', 'RENTAL', 'OTHER', name='helpcategory', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', name='requeststatus', create_type=False), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ------------------------------------------------------------------
    # help_applications
    # ------------------------------------------------------------------
    op.create_table(
        'help_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('applicant_id', sa.Integer(), nullable=False),
        sa.Column('message', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('status', postgresql.ENUM('PENDING', 'ACCEPTED', 'REJECTED', name='applicationstatus', create_type=False), nullable=False),
        sa.Column('applied_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['applicant_id'], ['users.id']),
        sa.ForeignKeyConstraint(['request_id'], ['request_helps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('request_id', 'applicant_id', name='unique_help_application'),
    )

    # ------------------------------------------------------------------
    # user_ratings
    # ------------------------------------------------------------------
    op.create_table(
        'user_ratings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rater_id', sa.Integer(), nullable=False),
        sa.Column('target_user_id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['rater_id'], ['users.id']),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['request_id'], ['request_helps.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Drop all tables and enum types."""

    op.drop_table('user_ratings')
    op.drop_table('help_applications')
    op.drop_table('request_helps')
    op.drop_table('user_compressed_images')
    op.drop_table('stories')
    op.drop_table('post_shares')
    op.drop_table('post_comments')
    op.drop_table('post_likes')
    op.drop_table('posts')
    op.drop_table('group_messages')
    op.drop_table('group_members')
    op.drop_table('group_chats')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')

    sa.Enum(name='applicationstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='requeststatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='helpcategory').drop(op.get_bind(), checkfirst=True)