import secrets
from functools import partial
from pathlib import Path
from typing import Dict, List
from uuid import UUID, uuid4

import orjson
from django.conf import settings
from pydantic import BaseModel, Field, PositiveInt


def get_static_manifest_contents(
    path: Path = settings.STATIC_ROOT / "manifest.json",
) -> dict:
    try:
        return orjson.loads(path.read_text())
    except orjson.JSONDecodeError:
        return dict()


static_file_info = get_static_manifest_contents()


class DeviceId(BaseModel):
    deviceId: UUID


class Device(BaseModel):
    deviceId: UUID = Field(default_factory=uuid4)
    available: bool = Field(default=False)


class Pair(BaseModel):
    token: str = Field(default_factory=partial(secrets.token_urlsafe, 36))
    ttl: PositiveInt = Field(default=600)


class PairInner(Pair):
    openToJoin: bool = Field(default=True)
    nodes: List[Device] = Field(default_factory=list)


class PairComplete(BaseModel):
    token: str
    device: Device


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
    js_file: str = Field(
        default_factory=lambda x: static_file_info["src/pairing/main.ts"]["file"]
    )
    css_file: str = Field(
        default_factory=lambda x: static_file_info["src/pairing/main.ts"]["css"][0]
    )
