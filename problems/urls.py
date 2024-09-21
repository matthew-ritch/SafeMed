from django.urls import path

from problems import views

urlpatterns = [
    # ex: /polls/
    path("", views.home, name="index"),
    path("device_info/<str:mn>", views.device_info, name="device_info",),
    path("device_search", views.device_search, name="device_search",)
]