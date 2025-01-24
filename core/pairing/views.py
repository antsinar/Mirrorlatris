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
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from pydantic import ValidationError

from .schema import Device, Pair, PairComplete, PairCtx, PairInner
from .tasks import ITaskQueue


@csrf_exempt
async def pairing_initialize(
    request,
) -> HttpResponse | HttpResponseBadRequest | HttpResponseNotAllowed:
    if request.method != "POST":
        return HttpResponseNotAllowed(permitted_methods=["POST"])
    try:
        device = Device(**orjson.loads(request.body))
    except ValidationError as ve:
        return HttpResponseBadRequest(
            content=ve.json(include_input=False, include_url=False)
        )
    except orjson.JSONDecodeError as je:
        return HttpResponseBadRequest(content=f"Bad JSON formatted data; {je.msg}")
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
    request,
) -> HttpResponse | HttpResponseBadRequest | HttpResponseNotAllowed:
    if request.method != "POST":
        return HttpResponseNotAllowed(permitted_methods=["POST"])
    try:
        pair_complete = PairComplete(**orjson.loads(request.data))
    except ValidationError as ve:
        return HttpResponseBadRequest(
            content=ve.json(include_input=False, include_url=False)
        )
    except orjson.JSONDecodeError as je:
        return HttpResponseBadRequest(content=f"Bad JSON formatted data; {je.msg}")

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


async def get_remaining_ttl(request, token: str) -> HttpResponse:
    ttl_task_queue: ITaskQueue[Pair] = apps.get_app_config("pairing").ttl_task_queue
    try:
        remaining_ttl = ttl_task_queue.get_task_state(token).remaining_ttl
        return HttpResponse(
            content=Pair(token=token, ttl=remaining_ttl).model_dump_json(),
            content_type="application/json",
        )
    except KeyError:
        return HttpResponseNotFound(content="Pairing token not found")


class PairView(TemplateView):
    template_name = "pairing/index.html"

    async def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return dict(ctx, **(PairCtx(page_title="Device Pairing").model_dump()))

    async def get(self, request, *args, **kwargs):
        ctx = await self.get_context_data(**kwargs)
        return await sync_to_async(render)(request, self.template_name, context=ctx)


class DeviceToggleView(View):
    http_method_names = ["options", "PUT"]

    async def options(self, request, *args, **kwargs):
        return super().options(request, *args, **kwargs)

    async def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
