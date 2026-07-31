from datetime import datetime

from pydantic import BaseModel, Field


class StandardAlarm(BaseModel):
    alarm_id: str
    severity: str
    resource_id: str
    resource_type: str
    resource_name: str
    title: str
    description: str
    occurred_at: datetime
    platform: str
    status: str
    raw_data: dict = Field(default_factory=dict)
