# routeapi/views.py
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from .utils import load_stations, compute_stops

NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
OSRM_ROUTE = "https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"

# simple in-memory cache for stations (loaded once)
stations_cache = None

def geocode_address(address):
    params = {"q": address, "format": "json", "limit": 1, "countrycodes": "us"}
    headers = {"User-Agent": "fuel-route-service/1.0 (contact@example.com)"}
    r = requests.get(NOMINATIM_SEARCH, params=params, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError(f"Address not found: {address}")
    return float(data[0]["lat"]), float(data[0]["lon"])

@csrf_exempt
def route_plan(request):
    """
    POST /api/route/
    Body: {"start": "<US address>", "finish": "<US address>"}
    Response: JSON with route geometry and fuel plan.
    """
    global stations_cache
    if request.method != "POST":
        return JsonResponse({"error": "Use POST with JSON body {start, finish}"}, status=400)

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    start = body.get("start")
    finish = body.get("finish")
    if not start or not finish:
        return JsonResponse({"error": "start and finish required"}, status=400)

    # Load stations once (from CSV in project root)
    if stations_cache is None:
        try:
            stations_cache = load_stations()
        except Exception as e:
            return JsonResponse({"error": f"Failed to load stations CSV: {str(e)}"}, status=500)

    # Geocode start & finish
    try:
        s_lat, s_lon = geocode_address(start)
        f_lat, f_lon = geocode_address(finish)
    except Exception as e:
        return JsonResponse({"error": f"Geocoding failed: {str(e)}"}, status=400)

    # Single OSRM route call
    coords_param = f"{s_lon},{s_lat};{f_lon},{f_lat}"
    try:
        r = requests.get(OSRM_ROUTE.format(coords=coords_param), timeout=15)
        r.raise_for_status()
    except Exception as e:
        return JsonResponse({"error": f"Routing request failed: {str(e)}"}, status=500)

    route = r.json()
    if "routes" not in route or not route["routes"]:
        return JsonResponse({"error": "No route returned by OSRM"}, status=500)

    route_obj = route["routes"][0]
    geometry = route_obj.get("geometry", {})
    coords = geometry.get("coordinates", [])

    # Compute stops and estimate cost
    results = compute_stops(coords, stations_cache)

    response = {
        "start": {"address": start, "lat": s_lat, "lon": s_lon},
        "finish": {"address": finish, "lat": f_lat, "lon": f_lon},
        "route_summary": {
            "distance_meters": results["total_distance_m"],
            "distance_miles": results["total_distance_miles"],
            "duration_seconds": route_obj.get("duration"),
        },
        "route_geometry": geometry,
        "fuel_plan": {
            "mpg": 10.0,
            "max_range_miles": 500,
            "stops": results["stops"],
            "total_gallons": results["total_gallons"],
            "estimated_cost_usd": results["estimated_cost"]
        }
    }
    return JsonResponse(response, safe=False)

def api_index(request):
    """
    Browser-friendly information page for /api/
    """
    html = """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Fuel Route Planner — API</title>
        <style>
          body { font-family: Arial, sans-serif; max-width: 850px; margin: 30px auto; color:#222; }
          pre { background:#f5f5f5; padding:14px; border-radius:6px; overflow:auto; }
          .muted { color:#666; font-size:0.95rem; }
          a.button { display:inline-block; padding:8px 12px; background:#1976d2; color:#fff; border-radius:6px; text-decoration:none; }
        </style>
      </head>
      <body>
        <h1>Fuel Route Planner API</h1>
        <p class="muted">POST to <code>/api/route/</code> with JSON body to get route geometry and a fuel plan chosen from your station CSV.</p>

        <h3>Example request (POST /api/route/)</h3>
        <pre>{
  "start": "1600 Amphitheatre Parkway, Mountain View, CA",
  "finish": "Times Square, New York, NY"
}</pre>

        <h3>Notes</h3>
        <ul>
          <li>Uses Nominatim (OpenStreetMap) for geocoding.</li>
          <li>Uses OSRM (router.project-osrm.org) for routing — single route API call.</li>
          <li>Assumptions: <strong>500-mile tank</strong>, <strong>10 mpg</strong>, start with full tank.</li>
          <li>Make sure <code>fuel-prices-for-be-assessment.csv</code> is in the project root (next to <code>manage.py</code>).</li>
        </ul>

        <p><a class="button" href="/admin/">Admin</a> <span style="margin-left:12px" class="muted">(requires superuser)</span></p>
      </body>
    </html>
    """
    return HttpResponse(html)
