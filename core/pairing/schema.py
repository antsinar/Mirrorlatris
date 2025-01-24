import secrets
from functools import partial
from typing import Dict, List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, PositiveInt


class Device(BaseModel):
    deviceId: UUID = Field(default_factory=uuid4)
    available: bool = Field(default=False)


class Pair(BaseModel):
    token: str = Field(default_factory=partial(secrets.token_urlsafe, 36))
    ttl: PositiveInt = Field(default=600)


class PairComplete(BaseModel):
    pairToken: str
    device: Device


class PairInner(BaseModel):
    pair: Pair
    nodes: List[Device] = Field(default_factory=list)


class PlaybackInfo(BaseModel):
    pairToken: str = Field(default_factory=str)
    node: Device
    shareUrl: str


class Mirror(BaseModel):
    pairToken: str = Field(default_factory=str)
    nodeSource: Device
    nodeDest: List[Device] = Field(default_factory=list)
    shareUrl: str
    platformArgs: Dict[str, str] = Field(default_factory=dict)


class PairCtx(BaseModel):
    page_title: str = Field(default_factory=str)
