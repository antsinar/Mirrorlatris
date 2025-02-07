import orjson
from asgiref.sync import sync_to_async
from django.apps import apps
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseNotFound,
)
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from pydantic import ValidationError

from core.cacheManager.tasks import ICacheTaskHandler

from .schema import Device, DeviceId, Pair, PairComplete, PairCtx, PairInner
from .tasks import ITaskQueue

ttl_task_queue: ITaskQueue[Pair] = apps.get_app_config("pairing").ttl_task_queue
cache_handler: ICacheTaskHandler = apps.get_app_config("cacheManager").cache_handler


@csrf_exempt
async def pairing_initialize(
    request, permitted_methods=["OPTIONS", "POST"]
) -> HttpResponse | HttpResponseBadRequest | HttpResponseNotAllowed:
    if request.method not in permitted_methods:
        return HttpResponseNotAllowed(permitted_methods=permitted_methods)
    try:
        device = Device(**orjson.loads(request.body))
    except ValidationError as ve:
        return HttpResponseBadRequest(
            content=ve.json(include_input=False, include_url=False),
            content_type="application/json",
        )
    except orjson.JSONDecodeError as je:
        return HttpResponseBadRequest(
            content=orjson.dumps({"reason": je.msg}),
            content_type="application/json",
        )

    if str(device.deviceId) in cache_handler.deviceIndex.keys():
        return HttpResponse(
            content=orjson.dumps(
                {"reason": "Device already in another pairing session"}
            ),
            status=409,
            content_type="application/json",
        )
    pair = Pair()
    pairInner = PairInner(**pair.model_dump(), openToJoin=True, nodes=[device])
    cache_handler.set_pairing(pair=pairInner)
    await ttl_task_queue.add_task(pair)
    return HttpResponse(
        content=pair.model_dump_json(),
        content_type="application/json",
    )


@csrf_exempt
def pairing_complete(
    request, permitted_methods=["OPTIONS", "POST"]
) -> HttpResponse | HttpResponseBadRequest | HttpResponseNotAllowed:
    if request.method not in permitted_methods:
        return HttpResponseNotAllowed(permitted_methods=permitted_methods)
    try:
        pair_complete = PairComplete(**orjson.loads(request.body))
    except ValidationError as ve:
        return HttpResponseBadRequest(
            content=ve.json(include_input=False, include_url=False)
        )
    except orjson.JSONDecodeError as je:
        return HttpResponseBadRequest(
            content=orjson.dumps({"reason": je.msg}),
            content_type="application/json",
        )
    deviceId = str(pair_complete.device.deviceId)
    if deviceId in cache_handler.deviceIndex.keys():
        return HttpResponse(
            content=orjson.dumps(
                {"reason": "Device already in another pairing session"}
            ),
            status=409,
            content_type="application/json",
        )

    if pair_complete.token not in cache_handler.pairingIndex:
        return HttpResponse(
            content=orjson.dumps({"reason": "Pairing token not found"}),
            status=404,
            content_type="application/json",
        )
    replacement: PairInner = cache_handler.get_pairing(pair_complete.token)
    if not replacement.openToJoin:
        return HttpResponse(
            content=orjson.dumps({"reason": "Pairing not open to join"}),
            status=409,
            content_type="application/json",
        )
    replacement.nodes.append(pair_complete.device)
    replacement.openToJoin = False
    cache_handler.update_pairing_devices(pair_complete.token, replacement.nodes)
    return HttpResponse(
        content=replacement.model_dump_json(),
        content_type="application/json",
        status=200,
    )


@csrf_exempt
async def pairing_refresh(
    request,
) -> HttpResponse | HttpResponseBadRequest | HttpResponseNotAllowed:
    # return HttpResponseBadRequest(content="Not Implemented")
    if request.method not in ["OPTIONS", "POST"]:
        return HttpResponseNotAllowed(permitted_methods=["OPTIONS", "POST"])
    try:
        pair_complete = PairComplete(**orjson.loads(request.body))
    except ValidationError as ve:
        return HttpResponseBadRequest(
            content=ve.json(include_input=False, include_url=False)
        )
    except orjson.JSONDecodeError as je:
        return HttpResponseBadRequest(
            content=orjson.dumps({"reason": je.msg}),
            content_type="application/json",
        )
    deviceId = str(pair_complete.device.deviceId)

    if pair_complete.token not in cache_handler.pairingIndex:
        return HttpResponse(
            content=orjson.dumps({"reason": "Pairing token not found"}),
            status=404,
            content_type="application/json",
        )

    if pair_complete.token not in cache_handler.deviceIndex[deviceId]:
        return HttpResponseForbidden(
            content=orjson.dumps({"reason": "Device not part of pairing"}),
            content_type="application/json",
        )

    replacement = Pair()
    await ttl_task_queue.add_task(replacement)
    cache_handler.transfer_pairing(
        pair_complete.token, replacement.token, replacement.ttl
    )

    return HttpResponse(
        content=replacement.model_dump_json(),
        content_type="application/json",
        status=200,
    )


async def get_remaining_ttl(request) -> HttpResponse:
    if request.method not in ["OPTIONS", "GET"]:
        return HttpResponseNotAllowed(permitted_methods=["OPTIONS", "GET"])
    try:
        token = request.GET.get("token")
    except Exception:
        return HttpResponseBadRequest(
            content=orjson.dumps({"reason": "No `token` query parameter found"}),
            content_type="application/json",
        )
    try:
        remaining_ttl = ttl_task_queue.get_task_state(token).remaining_ttl
        return HttpResponse(
            content=Pair(token=token, ttl=remaining_ttl).model_dump_json(),
            content_type="application/json",
        )
    except KeyError:
        return HttpResponseNotFound(
            content=orjson.dumps({"reason": "Pairing token not found"}),
            content_type="application/json",
        )


def device_toggle(
    request, permitted_methods=["OPTIONS", "PUT"]
) -> HttpResponse | HttpResponseNotAllowed | HttpResponseBadRequest:
    if request.method not in permitted_methods:
        return HttpResponseNotAllowed(permitted_methods=permitted_methods)
    try:
        deviceId = DeviceId(**orjson.loads(request.body))
    except ValidationError as ve:
        return HttpResponseBadRequest(
            content=ve.json(include_input=False, include_url=False)
        )
    except orjson.JSONDecodeError as je:
        return HttpResponseBadRequest(
            content=orjson.dumps({"reason": je.msg}),
            content_type="application/json",
        )
    deviceId = str(deviceId.deviceId)
    if deviceId not in cache_handler.deviceIndex.keys():
        return HttpResponseNotFound(
            content=orjson.dumps({"reason": "Device id not found"}),
            content_type="application/json",
        )
    cache_handler.remove_device(deviceId)
    return HttpResponseBadRequest(
        content=orjson.dumps({"reason": "Not implemented"}),
        content_type="application/json",
    )


class PairView(TemplateView):
    template_name = "pairing/index.html"

    async def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return dict(ctx, **(PairCtx(page_title="Device Pairing").model_dump()))

    async def get(self, request, *args, **kwargs):
        ctx = await self.get_context_data(**kwargs)
        return await sync_to_async(render)(request, self.template_name, context=ctx)
