# Human GPS Server

 A community-driven social platform for connecting people, sharing posts, and requesting help — built with FastAPI and Kotlin.

## Problem Statement

In many communities, people struggle to find help nearby or connect with others around them. Maman-Tap solves this by providing a mobile-first platform where users can post updates, chat with each other, request or offer help, and discover people near their location — all in one place.

## Features

### Backend (FastAPI)
- Authentication — JWT-based login/signup with access & refresh tokens, token blocklist via Redis, email verification, password reset
- Role-Based Access Control — user/admin roles with RoleChecker dependency
- Posts — create, read, update, delete posts with image upload (Cloudinary), likes, comments, shares
- Direct Messaging — one-on-one conversations with message history
- Komek (Help Requests) — post help requests by category (tutor, physical, rental, other), apply to help others, accept/reject applications
- Location Services — update user location, discover nearby users within a radius using Haversine formula
- AI Image Moderation — automatic content moderation via Sightengine API; flags and bans users who post inappropriate content
- Rate Limiting — per-IP request throttling with slowapi (write endpoints limited separately from reads)
- Request Profiling — sampling profiler via pyinstrument, live stats dashboard at /api/v1/stats
- Custom Logging — structured request logs with IP, method, URL, status code, and response time

### Android (Kotlin)
- User Profile — view and edit profile, upload profile image
- Posts — browse, create, and interact with posts
- Direct Chat — real-time one-on-one messaging
- Komek — browse and post help requests in the community
- Nearby Map — discover users near your location using Google Maps SDK


## Installation Steps

1. **Prerequisites**:
   - Python 3.8+
   - PostgreSQL database
   - Redis server
   - Gmail account for email (or configure SMTP)

2. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd human_gps_server
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the root directory with:
   ```
# Database
DATABASE_URL=postgresql+asyncpg://...

# Redis
REDIS_URL=redis://...

# JWT
JWT_SECRET=your_secret_key
JWT_ALGORITHM=HS256
REFRESH_TOKEN_EXPIRY=7

# Cloudinary
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Email (Gmail App Password)
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx
MAIL_FROM=your@gmail.com
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
MAIL_FROM_NAME=Maman-Tap

# Sightengine (Image Moderation)
SIGHTENGINE_API_USER=
SIGHTENGINE_API_SECRET=
   ```

5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start the server**:
   ```bash
   uvicorn src.main:app --reload
   ```

   The server will run on `http://localhost:8000`.

## Usage Instructions

- **API Endpoints**: Access the interactive API documentation at `http://localhost:8000/docs`
- **User Registration**: POST to `/api/v1/signup-with-verification` to register and verify email
- **Authentication**: Use JWT tokens obtained from `/api/v1/login`
- **Creating Posts**: Authenticated users can POST to `/api/v1/posts` with optional images
- **Requesting Help**: Use `/api/v1/komek` endpoints for location-based help requests
- **Stats Dashboard**: Visit `/api/v1/stats` for live performance metrics

## Screenshots


- Screenshots of the application are available in the second repository (Android Studio project).

## Technology Stack

| Layer | Technology |
|---|---|
| Mobile | Kotlin (Android) |
| Backend | FastAPI (Python) |
| Database | PostgreSQL via Neon DB (cloud) |
| ORM | SQLModel + SQLAlchemy (async) |
| Background Tasks | Celery |
| Message Broker | Redis (Redis Labs cloud / local) |
| Task Monitor | Flower |
| Image Storage | Cloudinary |
| Image Moderation | Sightengine API |
| Authentication | JWT (PyJWT) + bcrypt |
| Rate Limiting | slowapi |
| Profiling | pyinstrument |
| Maps (Android) | Google Cloud Console Maps SDK |
| DB Migrations | Alembic |
| Cache UI | Redis Commander |
| Deployment | Render (API + Celery worker) |

### API Endpoints Overview

#### Auth
POST   /api/v1/signup                     Register (no email verification)
POST   /api/v1/signup-with-verification   Register with email confirmation
POST   /api/v1/login                      Login → returns access + refresh tokens
POST   /api/v1/logout                     Invalidate token
POST   /api/v1/refresh                    Refresh access token
GET    /api/v1/verify-email?token=...     Verify email
POST   /api/v1/forgot-password            Request password reset
POST   /api/v1/reset-password             Reset password with token

#### Users
GET    /api/v1/users                      List users (search by username)
GET    /api/v1/users/me                   Get current user
PATCH  /api/v1/users/me                   Update profile
DELETE /api/v1/users/me                   Delete account
POST   /api/v1/users/me/profile-image     Upload profile image
PATCH  /api/v1/users/me/location          Update location
GET    /api/v1/users/nearby               Find nearby users

#### Posts
GET    /api/v1/posts                      Feed (sort by latest/likes/comments)
POST   /api/v1/posts                      Create post (with optional image)
PATCH  /api/v1/posts/{id}                 Update post
DELETE /api/v1/posts/{id}                 Delete post
POST   /api/v1/posts/{id}/like            Like post
DELETE /api/v1/posts/{id}/like            Unlike post
POST   /api/v1/posts/{id}/comments        Add comment
POST   /api/v1/posts/{id}/share           Share post to conversation/group

#### Conversations & Messages
POST   /api/v1/conversations              Start conversation
GET    /api/v1/users/{id}/conversations   List conversations
POST   /api/v1/conversations/{id}/messages  Send message
GET    /api/v1/conversations/{id}/messages  Get messages
PATCH  /api/v1/messages/{id}              Edit message
DELETE /api/v1/messages/{id}              Delete message

#### Komek (Help Requests)
POST   /api/v1/komek/requests             Create help request
GET    /api/v1/komek/requests             Browse requests (filter by category)
POST   /api/v1/komek/requests/{id}/apply  Apply to help
PATCH  /api/v1/komek/applications/{id}    Accept or reject application


## Team Members
- Kanalbekov Kuanysh 230103101
- Kultayev Agadil 203103368
- Seidaly Burkit 230103108
- Amankossov Mukagali 230103162
