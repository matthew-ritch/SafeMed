from django.urls import path

from problems import views

urlpatterns = [
    # ex: /polls/
    path("", views.manufacturer_search, name="index"),
    path("list_manufacturers", views.list_manufacturers, name="list_manufacturers",),
    path("list_devices", views.list_devices, name="list_devices",),
    path("device_info/<str:mn>", views.device_info, name="device_info",),
    path("manufacturer_search", views.manufacturer_search, name="manufacturer_search",),
    path("device_search", views.device_search, name="device_search",)
]