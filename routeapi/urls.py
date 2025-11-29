# routeapi/urls.py
from django.urls import path
from .views import route_plan, api_index

urlpatterns = [
    path("", api_index, name="api_index"),   # GET /api/
    path("route/", route_plan, name="route_plan"),  # POST /api/route/
]
