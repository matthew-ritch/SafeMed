from django.urls import path
from django.views.generic.base import TemplateView

from problems import views

urlpatterns = [
    # ex: /polls/
    path("", views.home, name="index"),
    path("device_info/<str:mn>", views.device_info, name="device_info",),
    path("device_search", views.device_search, name="device_search",),
    path("robots.txt", TemplateView.as_view(template_name="problems/robots.txt", content_type="text/plain"), name="robots.txt"),
    path("sitemap.txt", views.sitemap, name = "sitemap.txt"),
]