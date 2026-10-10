import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .services import plan_trip


def health(request):
    return JsonResponse({"status": "ok", "service": "Spotter trip planner"})


@csrf_exempt
def trip_plan(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST for trip planning."}, status=405)
    try:
        payload = json.loads(request.body)
        required = ("current_location", "pickup_location", "dropoff_location", "current_cycle_used")
        if any(not str(payload.get(field, "")).strip() for field in required[:3]):
            raise ValueError("All locations are required.")
        cycle = float(payload["current_cycle_used"])
        if cycle < 0 or cycle > 70:
            raise ValueError("Current cycle used must be between 0 and 70 hours.")
        payload["current_cycle_used"] = cycle
        return JsonResponse(plan_trip(payload))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        return JsonResponse({"error": str(error)}, status=400)
