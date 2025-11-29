# fuel_route_project/urls.py
from django.contrib import admin
from django.urls import path, include
from routeapi.views import api_index

urlpatterns = [
    path("", api_index, name="site_index"),   # root URL -> friendly index page
    path("admin/", admin.site.urls),
    path("api/", include("routeapi.urls")),
]
