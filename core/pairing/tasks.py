import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, Protocol

from pydantic import BaseModel

from .schema import Pair

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskState[T](BaseModel):
    startdt: datetime
    remaining_ttl: int
    object: T


class ITaskQueue[T](Protocol):
    queue: asyncio.Queue[T]
    pool: ThreadPoolExecutor
    available: bool
    task_states: Dict[str, TaskState[T]]

    def __init__(self): ...

    async def add_task(self, obj: T) -> None: ...

    async def get_task(self) -> T: ...

    def get_task_state(self, token: str) -> TaskState: ...

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
        self.task_states: Dict[str, TaskState[Pair]] = dict()

    async def add_task(self, obj: Pair) -> None:
        logger.info(f"Appended task\t{obj.token}; ttl = {obj.ttl} seconds")
        await self.queue.put(obj)

    async def get_task(self) -> Pair:
        task: Pair = await self.queue.get()
        return task

    def get_task_state(self, token: str) -> TaskState:
        return self.task_states[token]

    @property
    def _queue_length(self) -> int:
        return self.queue.qsize()

    def register_task(self, obj: Pair) -> None:
        self.task_states[obj.token] = TaskState(
            startdt=datetime.now(), remaining_ttl=obj.ttl, object=obj
        )

    def task_complete(self, token: str) -> None:
        logger.info(f"Completed task\t{token}")
        del self.task_states[token]
        self.queue.task_done()

    async def process(self):
        while self.available:
            if self._queue_length == 0 and len(self.task_states.keys()) == 0:
                await asyncio.sleep(0.5)
                continue

            for _ in range(self._queue_length):
                task_obj: Pair = await self.get_task()
                self.register_task(task_obj)
            [_ for _ in self.pool.map(self._ttl_calc, self.task_states.keys())]
            await asyncio.sleep(1)

    def _ttl_calc(self, task_token: str):
        self.calc_remaining(task_token, self.task_states[task_token].startdt)
        if self.task_states[task_token].remaining_ttl <= 0:
            self.task_complete(task_token)

    def calc_remaining(self, task_token: str, start_dt: datetime) -> None:
        self.task_states[task_token].remaining_ttl = int(
            (
                start_dt
                + timedelta(seconds=self.task_states[task_token].object.ttl)
                - datetime.now()
            ).total_seconds()
        )

    def shutdown(self) -> None:
        logger.info("Shutting down ttl task queue")
        self.available = False
        self.pool.shutdown(wait=False)
