import logging
import threading
from typing import Optional
from uuid import uuid1

logger = logging.getLogger(__name__)


class ExtensionContext:
    def __init__(self, execution_id: str) -> None:
        self.lock = threading.Lock()
        self.execution_id = execution_id
        self.extension_id: Optional[str] = None

    def set_extension_id(self, extension_id: str) -> None:
        with self.lock:
            logger.debug("set_extension_id:%s", extension_id)
            self.extension_id = extension_id


extension_context = ExtensionContext(str(uuid1()))
