import logging
from typing import Dict, List, Protocol

import orjson
from django.apps import apps
from pymemcache.client.base import PooledClient
from pymemcache.exceptions import MemcacheError

from core.pairing.schema import Device, PairInner
from core.pairing.tasks import ITaskQueue

from .connection import generateClient

logger = logging.getLogger(__name__)


class ICacheTaskHandler(Protocol):
    task_client: PooledClient
    ttl_task_queue: ITaskQueue
    pairingIndex: List[str]
    deviceIndex: Dict[str, List[str]]

    def initIndexes(self) -> None: ...

    def add_device(self, deviceId: str, pairToken: str) -> None: ...

    def add_pairing(self, pairToken: str) -> None: ...

    def get_pairing(self, pairToken: str) -> PairInner:
        """Return pairing information of a known pairing token"""
        ...

    def set_pairing(self, pair: PairInner) -> None: ...

    def update_pairing_ttl(self, pairToken: str) -> None: ...

    def update_pairing_devices(self, pairToken: str, devices: List[Device]) -> None: ...

    def toggle_pairing_open(self, pairToken: str) -> None:
        """Toggle pairing availability to join a new device"""
        ...

    def cancel_pairing(self, pairToken: str) -> None:
        """Removes pairing token from the pairing index.
        The pairing object will be left to expire on its own
        """
        ...

    def transfer_pairing(self, oldPairToken: str, newPairToken: str, ttl: int) -> None:
        """Transfer pairing information from one token to another"""
        ...

    def remove_device(self, deviceId: str) -> None: ...


class CacheTaskHandler:
    def __init__(self):
        self.task_client: PooledClient = next(generateClient())
        self.ttl_task_queue: ITaskQueue = apps.get_app_config("pairing").ttl_task_queue
        self.pairingIndex: List[str] = list()
        self.deviceIndex: Dict[str, List[str]] = dict()

    def initIndexes(self) -> None:
        self._initDeviceIndex()
        self._initPairingIndex()

    def _initDeviceIndex(self) -> None:
        try:
            self.task_client.set(
                "deviceIndex",
                orjson.dumps({"deviceId": ["pairingToken"]}),
            )
        except MemcacheError:
            logger.error("Device Index initiation failed")

    def _initPairingIndex(self) -> None:
        try:
            self.task_client.set(
                "pairingIndex",
                orjson.dumps(["pairingToken"]),
            )
        except MemcacheError:
            logger.error("Pairing Index initiation failed")

    def add_device(self, deviceId: str, pairToken: str) -> None:
        self.deviceIndex[deviceId] = (
            list()
            if deviceId not in self.deviceIndex.keys()
            else self.deviceIndex[deviceId]
        )
        self.deviceIndex[deviceId].append(pairToken)
        self.task_client.replace("deviceIndex", orjson.dumps(self.deviceIndex))

    def add_pairing(self, pairToken: str) -> None:
        self.pairingIndex.append(pairToken)
        self.task_client.replace("pairingIndex", self.pairingIndex)

    def get_pairing(self, pairToken: str) -> PairInner:
        return PairInner(**orjson.loads(self.task_client.get(pairToken)))

    def set_pairing(self, pair: PairInner) -> None:
        self.add_pairing(pair.token)
        [
            self.add_device(str(node.deviceId), pairToken=pair.token)
            for node in pair.nodes
        ]
        self.task_client.set(
            pair.token,
            pair.model_dump_json(),
            expire=pair.ttl,
        )

    def update_pairing_ttl(self, pairToken: str) -> None:
        if not self._check_pairToken_exists(pairToken):
            logger.error("Token not in pairing index")
            return
        pair_obj = PairInner(**orjson.loads(self.task_client.get(pairToken)))
        pair_obj.ttl = self.ttl_task_queue.get_task_state(pairToken).remaining_ttl
        self.task_client.replace(
            pairToken,
            pair_obj.model_dump_json(),
            expire=pair_obj.ttl,
        )

    def update_pairing_devices(self, pairToken: str, devices: List[Device]) -> None:
        if not self._check_pairToken_exists(pairToken):
            logger.error("Token not in pairing index")
            return
        pair_obj = PairInner(**orjson.loads(self.task_client.get(pairToken)))
        if not pair_obj.openToJoin:
            logger.info("Pairing not open to add new devices")
            return
        [
            self.add_device(str(device.deviceId), pairToken)
            for device in devices
            if str(device.deviceId) not in self.deviceIndex
        ]
        pair_obj.nodes = devices
        self.task_client.replace(
            pairToken,
            pair_obj.model_dump_json(),
            expire=self.ttl_task_queue.get_task_state(pairToken).remaining_ttl,
        )

    def toggle_pairing_open(self, pairToken: str) -> None:
        if not self._check_pairToken_exists(pairToken):
            logger.error("Token not in pairing index")
            return
        pair_obj = PairInner(**orjson.loads(self.task_client.get(pairToken)))
        pair_obj.openToJoin != pair_obj.openToJoin
        self.task_client.replace(
            pairToken,
            pair_obj.model_dump_json,
            expire=self.ttl_task_queue.get_task_state(pairToken).remaining_ttl,
        )

    def cancel_pairing(self, pairToken: str) -> None:
        if not self._check_pairToken_exists(pairToken):
            logger.error("Token not in pairing index")
            return
        pair_obj = PairInner(**orjson.loads(self.task_client.get(pairToken)))
        [
            self.deviceIndex[str(node.deviceId)].remove(pairToken)
            for node in pair_obj.nodes
        ]
        self.pairingIndex.remove(pairToken)
        self.task_client.replace("pairingIndex", orjson.dumps(self.pairingIndex))

    def transfer_pairing(self, oldPairToken: str, newPairToken: str, ttl: int) -> None:
        if not self._check_pairToken_exists(oldPairToken):
            logger.error("Token not in pairing index")
            return
        self.add_pairing(newPairToken)
        replacement: PairInner = self.get_pairing(oldPairToken)
        replacement.token = newPairToken
        replacement.ttl = ttl
        self.task_client.set(newPairToken, replacement.model_dump_json())
        [
            self.add_device(str(device.deviceId), newPairToken)
            for device in replacement.nodes
        ]
        self.cancel_pairing(oldPairToken)

    def remove_device(self, deviceId: str) -> None:
        if not self._check_deviceId_exists(deviceId):
            logger.error("DeviceId not in device index")
            return
        try:
            pair_objects = [
                PairInner(**orjson.loads(self.task_client.get(obj)))
                for obj in self.task_client.get_many(self.deviceIndex[deviceId])
            ]
            pair_json_objects = {
                pair.token: pair.model_dump_json()
                for pair in pair_objects
                for node in pair.nodes
                if self._check_pairToken_exists(pair.token)
                and str(node.deviceId) != deviceId
            }
            self.task_client.set_many(pair_json_objects)
            del self.deviceIndex[str(deviceId)]
            self.task_client.replace("deviceIndex", orjson.dumps(self.deviceIndex))
        except KeyError as ke:
            logger.error(ke)
        except MemcacheError as me:
            logger.error(me)

    def _check_pairToken_exists(self, pairToken: str) -> bool:
        return pairToken in self.pairingIndex

    def _check_deviceId_exists(self, deviceId: str) -> bool:
        return deviceId in self.deviceIndex.keys()
