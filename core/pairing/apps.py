import asyncio
import logging

from django.apps import AppConfig

from .schema import Pair
from .tasks import ITaskQueue, TTLTaskQueue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PairingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.pairing"
    ttl_task_queue: ITaskQueue[Pair] = TTLTaskQueue()

    def ready(self):
        super().ready()
        try:
            # TODO: Handle graceful shutdown on SIGINT signal
            processor = asyncio.create_task(self.ttl_task_queue.process())
        except Exception as e:
            logger.error(str(e))
