from django.urls import path

from .views import (DeviceToggleView, PairView, get_remaining_ttl,
                    pairing_complete, pairing_initialize, pairing_refresh)

jsonResponsePatterns = [
    path("initialize/", pairing_initialize, name="pairing_initialize"),
    path("complete/", pairing_complete, name="pairing_complete"),
    path("refresh/", pairing_refresh, name="pairing_refresh"),
    path("remaining/<str:token>/", get_remaining_ttl, name="pairing_remaining"),
    path("<str:deviceId>/toggle/", DeviceToggleView.as_view(), name="device_toggle"),
]

vuePatterns = [
    path("", PairView.as_view(), name="pairing_index"),
]

urlpatterns = jsonResponsePatterns + vuePatterns
