from datetime import datetime

from pydantic import BaseModel


class TermsStatusRead(BaseModel):
    accepted: bool
    current_version: str
    accepted_version: str | None = None
    accepted_at: datetime | None = None


class AcceptTermsRequest(BaseModel):
    terms_version: str


class AcceptTermsResponse(BaseModel):
    accepted: bool
    terms_version: str
    accepted_at: datetime
