from django.urls import path
from django.views.generic.base import TemplateView
from django.contrib.sitemaps.views import sitemap

from problems import views

sitemaps = {
    "static": views.StaticViewSitemap,
    "devices": views.DeviceSitemap
}

urlpatterns = [
    # ex: /polls/
    path("", views.home, name="index"),
    path("device_info/<str:mn>", views.device_info, name="device_info",),
    path("device_search", views.device_search, name="device_search",),
    path("robots.txt", TemplateView.as_view(template_name="problems/robots.txt", content_type="text/plain"), name="robots.txt"),
    path("sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    )
]