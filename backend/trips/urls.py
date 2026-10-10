from django.urls import path
from .views import health, trip_plan

urlpatterns = [
    path("health/", health),
    path("trip-plan/", trip_plan),
]
