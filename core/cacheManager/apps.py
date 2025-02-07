import logging

from django.apps import AppConfig

from .tasks import CacheTaskHandler

logger = logging.getLogger(__name__)


class CachemanagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.cacheManager"
    cache_handler: CacheTaskHandler | None = None

    def ready(self):
        super().ready()
        try:
            self.cache_handler = CacheTaskHandler()
            self.cache_handler.initIndexes()
            logger.info(
                f"Cache client ready; connected server -> {':'.join([str(el) for el in self.cache_handler.task_client.server])}"
            )
        except GeneratorExit:
            logger.error("Memcached client generator exhausted")
