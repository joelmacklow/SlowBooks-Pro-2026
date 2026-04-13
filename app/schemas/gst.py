from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class GstCodeResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]
    rate: Decimal
    category: str
    is_active: bool
    is_system: bool
    sort_order: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
