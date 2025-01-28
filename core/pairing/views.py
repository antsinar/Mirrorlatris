import orjson
from asgiref.sync import sync_to_async
from django.apps import apps
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
    HttpResponseNotFound,
)
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from pydantic import ValidationError

from .schema import Device, DeviceId, Pair, PairComplete, PairCtx, PairInner
from .tasks import ITaskQueue


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
    # TODO: Check if the device is already in another active pairing session
    pair = Pair()
    pairInner = PairInner(pair=pair, nodes=[device])
    # TODO: Append the pairing session to the cache
    ttl_task_queue: ITaskQueue[Pair] = apps.get_app_config("pairing").ttl_task_queue
    await ttl_task_queue.add_task(pair)
    return HttpResponse(
        content=pair.model_dump_json(),
        content_type="application/json",
    )


@csrf_exempt
async def pairing_complete(
    request, permitted_methods=["OPTIONS", "POST"]
) -> HttpResponse | HttpResponseBadRequest | HttpResponseNotAllowed:
    if request.method not in permitted_methods:
        return HttpResponseNotAllowed(permitted_methods=permitted_methods)
    try:
        pair_complete = PairComplete(**orjson.loads(request.data))
    except ValidationError as ve:
        return HttpResponseBadRequest(
            content=ve.json(include_input=False, include_url=False)
        )
    except orjson.JSONDecodeError as je:
        return HttpResponseBadRequest(
            content=orjson.dumps({"reason": je.msg}),
            content_type="application/json",
        )

    # TODO: Get pair matching the given id
    if not pair_complete["pairToken"]:
        return HttpResponseNotFound(content="Pair token does not exist")

    # TODO: append new device to pair object
    pair = Pair()
    return HttpResponse(
        content=pair.model_dump_json(), content_type="appplication/json"
    )


@csrf_exempt
async def pairing_refresh(
    request,
) -> HttpResponse | HttpResponseBadRequest | HttpResponseNotAllowed:
    return HttpResponseBadRequest(content="Not Implemented")


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
    ttl_task_queue: ITaskQueue[Pair] = apps.get_app_config("pairing").ttl_task_queue
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


async def device_toggle(
    request, permitted_methods=["OPTIONS", "PUT"]
) -> HttpResponse | HttpResponseNotAllowed | HttpResponseBadRequest:
    if request.method not in permitted_methods:
        return HttpResponseNotAllowed(permitted_methods=permitted_methods)
    try:
        deviceId = DeviceId(**orjson.loads(request.data))
    except ValidationError as ve:
        return HttpResponseBadRequest(
            content=ve.json(include_input=False, include_url=False)
        )
    except orjson.JSONDecodeError as je:
        return HttpResponseBadRequest(
            content=orjson.dumps({"reason": je.msg}),
            content_type="application/json",
        )
    # TODO: Match device with a pairing session
    # TODO: Remove device from any active pairing session
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
