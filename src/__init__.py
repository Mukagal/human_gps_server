from .users.UserRoutes import user_router
from .messages.MessageRoutes import message_router
from .conversations.ConversationRoutes import conversation_router
from .post.PostRoutes import post_router
from .story.StoryRoutes import story_router
from .groups.GroupRoutes import group_router
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .db.main import initdb
from .errors import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from fastapi.exceptions import RequestValidationError

@asynccontextmanager
async def lifespan(app: FastAPI):
    await initdb()
    yield
    print("server is stopping")

version = 'v1'

app = FastAPI(
    title="MessaGe",
    description="A REST API for a Chat Application",
    version= version,
    lifespan=lifespan
)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(user_router, prefix=f"/api/{version}", tags=["users"])
app.include_router(conversation_router, prefix=f"/api/{version}", tags=["conversations"])
app.include_router(message_router, prefix=f"/api/{version}", tags=["messages"])
app.include_router(post_router, prefix=f"/api/{version}", tags=["posts"])
app.include_router(story_router, prefix=f"/api/{version}", tags=["story"])
app.include_router(group_router, prefix=f"/api/{version}", tags=["group"])