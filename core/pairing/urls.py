from django.urls import path

from .views import (
    PairView,
    device_toggle,
    get_remaining_ttl,
    pairing_complete,
    pairing_initialize,
    pairing_refresh,
)

jsonResponsePatterns = [
    path("initialize/", pairing_initialize, name="pairing_initialize"),
    path("complete/", pairing_complete, name="pairing_complete"),
    path("refresh/", pairing_refresh, name="pairing_refresh"),
    path("remaining/", get_remaining_ttl, name="pairing_remaining"),
    path("device/toggle/", device_toggle, name="device_toggle"),
]

vuePatterns = [
    path("", PairView.as_view(), name="pairing_index"),
]

urlpatterns = jsonResponsePatterns + vuePatterns
