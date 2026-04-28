from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional, List
from ..db.models import HelpCategory, RequestStatus, ApplicationStatus


class HelpApplicationOut(BaseModel):
    id: int
    applicant_id: int
    applicant_username: Optional[str] = None
    message: Optional[str]
    status: ApplicationStatus
    applied_at: datetime

    class Config:
        from_attributes = True


class KomekCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    category: HelpCategory
    expires_in_days: int = Field(default=3, ge=1, le=30, description="How many days until the request expires (1–30, default 3)")

    @model_validator(mode="after")
    def strip_timezone(self):
        return self


class KomekOut(BaseModel):
    id: int
    requester_id: int
    title: str
    description: str
    category: HelpCategory
    status: RequestStatus
    created_at: datetime
    expires_at: Optional[datetime]
    applications: List[HelpApplicationOut] = []

    class Config:
        from_attributes = True

class KomekNearbyOut(BaseModel):
    request: KomekOut
    distance_km: float
    requester_latitude: float
    requester_longitude: float
    requester_username: str

    class Config:
        from_attributes = True


class ApplyToRequestCreate(BaseModel):
    message: Optional[str] = Field(default=None, max_length=500)


class RatingRequest(BaseModel):
    target_user_id: int
    request_id: int
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=500)


class UserRatingOut(BaseModel):
    id: int
    rater_id: int
    target_user_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UserAverageRating(BaseModel):
    average_rating: float
    total_ratings: int