from abc import ABC, abstractmethod

from credentials.models import Credential
from models.standard import StandardAlarm
from platforms.models import PlatformDefinition


class BaseAdapter(ABC):
    PLATFORM = ""

    def __init__(self, definition: PlatformDefinition):
        self.definition = definition

    @abstractmethod
    async def list_alarms(
        self,
        credential: Credential,
        severity: str = "all",
        limit: int = 20,
    ) -> list[StandardAlarm]:
        raise NotImplementedError
