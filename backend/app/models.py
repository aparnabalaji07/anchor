from datetime import datetime

from pydantic import BaseModel, Field


class Reading(BaseModel):
    time: datetime
    counter: int = Field(ge=1)
    power_on: bool
    sensors: dict = Field(default_factory=dict)
    prev_hash: str
    hash: str


class IngestBatch(BaseModel):
    device_id: str
    call_requested: bool = False
    readings: list[Reading] = Field(min_length=1, max_length=500)