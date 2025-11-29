"""Pydantic validation schemas."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class MediaUpdateRequest(BaseModel):
    """Media update request schema."""
    eventDate: Optional[str] = None
    eventDateDisplay: Optional[str] = None
    eventDatePrecision: Optional[Literal['YEAR', 'MONTH', 'DAY', 'UNKNOWN']] = None
    eventDateApproximate: Optional[bool] = None
    subject: Optional[str] = None
    notes: Optional[str] = None
    people: Optional[List[str]] = None
    locationName: Optional[str] = None
    locationCoords: Optional[dict] = None
    reviewStatus: Optional[Literal['unreviewed', 'reviewed']] = None
    
    @field_validator('locationCoords')
    @classmethod
    def validate_coords(cls, v):
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError('locationCoords must be a dict')
            if 'lat' not in v or 'lon' not in v:
                raise ValueError('locationCoords must have lat and lon')
            try:
                float(v['lat'])
                float(v['lon'])
            except (ValueError, TypeError):
                raise ValueError('locationCoords lat and lon must be numbers')
        return v


class NavigateQuery(BaseModel):
    """Navigate query parameters."""
    direction: Literal['next', 'previous']
    reviewStatus: Literal['unreviewed', 'reviewed', 'all'] = 'unreviewed'


class SearchQuery(BaseModel):
    """Search query parameters."""
    libraryId: str
    folder: Optional[str] = None
    hasSubject: Optional[bool] = None
    hasNotes: Optional[bool] = None
    hasPeople: Optional[bool] = None
    reviewStatus: Literal['unreviewed', 'reviewed', 'all'] = 'all'


class UploadRequest(BaseModel):
    """Upload request (multipart form data - validated separately)."""
    targetFolder: str = ""
    batchName: Optional[str] = None

