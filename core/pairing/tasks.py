import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, Protocol

from .schema import Pair

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ITaskQueue[T](Protocol):
    queue: asyncio.Queue[T]
    pool: ThreadPoolExecutor
    available: bool
    startdt_tasks: Dict[str, datetime]
    remaining_tasks: Dict[str, int]
    task_objects: Dict[str, T]

    def __init__(self): ...

    async def add_task(self, obj: T) -> None: ...

    async def get_task(self) -> T: ...

    @property
    def _queue_length(self) -> int: ...

    def register_task(self, obj: T) -> None: ...

    def task_complete(self, obj: T) -> None: ...

    async def process(self) -> None: ...

    def calc_remaining(self, obj: T, start_dt: datetime) -> None: ...

    def shutdown(self) -> None: ...


class TTLTaskQueue:
    def __init__(self):
        self.queue: asyncio.Queue[Pair] = asyncio.Queue()
        self.pool = ThreadPoolExecutor()
        self.available: bool = True
        self.startdt_tasks: Dict[str, datetime] = dict()
        self.remaining_tasks: Dict[str, int] = dict()
        self.task_objects: Dict[str, Pair] = dict()

    async def add_task(self, obj: Pair) -> None:
        logger.info(f"Appended task\t{obj.token}; ttl = {obj.ttl} seconds")
        await self.queue.put(obj)

    async def get_task(self) -> Pair:
        task: Pair = await self.queue.get()
        return task

    @property
    def _queue_length(self) -> int:
        return self.queue.qsize()

    def register_task(self, obj: Pair) -> None:
        self.startdt_tasks[obj.token] = datetime.now()
        self.remaining_tasks[obj.token] = obj.ttl
        self.task_objects[obj.token] = obj

    def task_complete(self, obj: Pair) -> None:
        logger.info(f"Completed task\t{obj.token}")
        del self.startdt_tasks[obj.token]
        del self.remaining_tasks[obj.token]
        del self.task_objects[obj.token]
        self.queue.task_done()

    async def process(self):
        while self.available:
            if self._queue_length == 0 and len(self.remaining_tasks.keys()) == 0:
                await asyncio.sleep(0.5)
                continue

            for _ in range(self._queue_length):
                task_obj: Pair = await self.get_task()
                self.register_task(task_obj)
            [
                self.pool.submit(self._ttl_calc, task)
                for task in self.task_objects.keys()
            ]
            await asyncio.sleep(1)

    def _ttl_calc(self, task_token: str):
        task_obj = self.task_objects[task_token]
        self.calc_remaining(task_obj, self.startdt_tasks[task_token])
        if self.remaining_tasks[task_token] <= 0:
            self.task_complete(task_obj)

    def calc_remaining(self, obj: Pair, start_dt: datetime) -> None:
        self.remaining_tasks[obj.token] = int(
            (start_dt + timedelta(seconds=obj.ttl) - datetime.now()).total_seconds()
        )

    def shutdown(self) -> None:
        logger.info("Shutting down ttl task queue")
        self.available = False
        self.pool.shutdown(wait=False)
