## 1. Middleware

## 1. Middleware

### 1a. CORS & TrustedHostMiddleware
- `CORSMiddleware` allows cross-origin requests (configurable per environment)
- `TrustedHostMiddleware` restricts allowed Host headers
- Implemented in `src/__init__.py` via `app.add_middleware()`

### 1b. Custom Logging
Format: `<IP>:<Port> - <Method> - <URL> - <Status Code> - <Processing Time>`
- INFO for 2xx, WARNING for 4xx, ERROR for 5xx
- Implemented in `src/middlware/logging.py` as Starlette `BaseHTTPMiddleware`

### 1c. Rate Limiting (slowapi + Redis-compatible limits)
- 60 requests/min per IP (all endpoints)
- 500 requests/hour per IP (all endpoints)
- 50 write requests/hour per IP (POST/DELETE/PATCH endpoints only)
- GET endpoints are not rate-limited
- Returns HTTP 429 with JSON error on limit exceeded

### 1d. Profiling (pyinstrument)
- Sampling profiler: captures call stacks every 1ms (low overhead)
- Enabled via `?profile=1` query param (dev) or `PROFILING_ENABLED=true` env var
- When profiler overhead is a concern: use sampling over tracing, enable only on-demand,
  never run always-on in production. pyinstrument adds ~1-2% overhead vs cProfile's 10-30%.
- Identified slow endpoints: any endpoint doing N+1 ORM queries (e.g. get_feed loads
  all posts then all likes/comments separately). Fix: use joinedload/selectinload.

#### Slow endpoints identified from logs:
| Endpoint | Avg Time | Reason | Fix |
|---|---|---|---|
| POST /posts (with image) | ~4200ms | Cloudinary upload is synchronous, blocks request | Move to background task |
| GET /posts | ~172ms | N+1 ORM queries: separate SELECT for likes/comments/shares per post | Use `joinedload()` |
| POST /login | ~800ms | bcrypt hashing is intentionally slow | Not a bug |

#### Live Stats Dashboard:
- Available at `GET /api/v1/stats` — auto-refreshes every 5 seconds
- Groups endpoints by HTTP method (GET / POST / PATCH / DELETE)
- Shows: call count, avg/min/max response time, error count, error rate
- Slow endpoints (avg > 500ms) highlighted in orange automatically
- Implemented in `src/__init__.py` as an inline HTML response

---

## 2. Background Tasks (Celery + Redis)

### 2a. Email Confirmation & Password Reset

#### Email Confirmation
- Triggered on `POST /api/v1/signup-with-verification`
- Generates a `verification_token` (32-byte URL-safe random string) stored in DB
- Fires `send_confirmation_email` Celery task in background
- User clicks link → `GET /api/v1/verify-email?token=...` → sets `is_verified=True`
- Implemented in `src/tasks/mail_task.py` using `fastapi-mail` with Gmail SMTP

#### Password Reset
- `POST /api/v1/forgot-password` → generates token → fires `send_password_reset_email` task
- `POST /api/v1/reset-password` → verifies token → hashes and saves new password
- Gmail App Password used


### 2b. Image Compression → PostgreSQL Binary Storage

#### Route: `POST /api/v1/users/me/profile-image-compressed`
- User uploads image → Cloudinary upload runs synchronously (URL needed immediately)
- `compress_and_store_image` Celery task fires in background
- Task uses Pillow to compress image to JPEG quality=60
- Stores raw binary (`BYTEA`) in `user_compressed_images` table
- Logs before/after size comparison:

### 2c. AI Image Moderation + Auto-Ban (Sightengine API)

#### Background Task: `moderate_image` and `moderate_profile_image`
- Fires automatically after every post image upload and profile image upload
- Uses **Sightengine API** (free tier: 2,000 operations/month, no credit card)
- Checks for: nudity, violence, offensive content
- Threshold: score ≥ 0.7 → flagged

#### Post moderation flow:
1. User uploads post with image → post saved, moderation task fires in background
2. Celery worker calls Sightengine API with image bytes
3. If flagged:
   - `posts.is_flagged = TRUE`, `posts.flag_reason` set
   - `users.is_banned = TRUE`, `users.ban_reason` set
   - All user's post/story content set to `[removed]`, image paths nulled
   - Cloudinary images deleted to free storage
   - Compressed binary deleted from PostgreSQL
4. Flagged posts hidden from public feed (`WHERE is_flagged = FALSE`)
5. Banned users cannot login or make any authenticated request

#### Profile image moderation flow:
1. User uploads profile image → Cloudinary upload runs, moderation fires in background
2. If flagged: profile image removed from Cloudinary + DB, user banned

#### Ban enforcement:
- `POST /login` → banned users get HTTP 403 before token is issued
- All authenticated routes → `get_current_user` dependency checks `is_banned`
- Public user endpoints → banned users return 404 (existence not revealed)
- User list (`GET /users`) → banned users excluded from results


python -m celery -A src.celery worker --loglevel=INFO --pool=solo

data:image/jpeg;base64, <result of query below>
SELECT encode(image_data, 'base64') AS base64_image
FROM user_compressed_images
WHERE user_id = 4;
