from django.urls import path

from problems import views

urlpatterns = [
    # ex: /polls/
    path("", views.list_devices_by_manufacturer, name="index"),
    path("list", views.list_devices_by_manufacturer, name="list_devices_by_manufacturer",),
    path("device_info/<str:mn>", views.device_info, name="device_info",)
]