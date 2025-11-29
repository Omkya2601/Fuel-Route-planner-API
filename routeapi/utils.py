import math
from typing import List, Dict
import pandas as pd
import os


def haversine_m(lat1, lon1, lat2, lon2):
    """Return great-circle distance in meters."""
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def meters_to_miles(m: float) -> float:
    return m / 1609.344


def load_stations(csv_path: str = None) -> List[Dict]:
    """
    SAFE + STABLE CSV LOADER
    - Tries UTF-8
    - If fails, tries Latin-1
    - If fails, tries Windows-1252
    - Tries multiple separators (comma, semicolon, tab, pipes)
    - Auto-detects station name / lat / lon / price columns
    """

    default = os.path.join(os.getcwd(), "fuel-prices-for-be-assessment.csv")
    path = csv_path or default

    if not os.path.exists(path):
        raise FileNotFoundError(f"Stations CSV not found at: {path}")

    # ---- detect encoding safely ----
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    df = None

    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc, engine="python")
            break
        except Exception:
            df = None
            continue

    if df is None:
        raise ValueError("Unable to decode CSV file using common encodings.")

    # Try multiple separators if needed
    if df.shape[1] == 1:
        for sep in [",", ";", "\t", "|"]:
            try:
                df = pd.read_csv(path, sep=sep, encoding=enc, engine="python")
                if df.shape[1] > 1:
                    break
            except Exception:
                continue

    if df is None or df.shape[1] < 2:
        raise ValueError("CSV parsing failed — no readable columns found.")

    # Normalize header names
    cols = [c.strip() for c in df.columns]
    lower = {c.lower(): c for c in cols}

    # Candidate column name options
    name_opts = ["station_name", "station", "name", "site"]
    lat_opts = ["lat", "latitude", "y", "gps_lat"]
    lon_opts = ["lon", "lng", "longitude", "x", "gps_lon", "long"]
    price_opts = ["price", "fuel_price", "gas_price", "price_per_gallon", "cost"]

    def find_col(options):
        for o in options:
            if o in lower:
                return lower[o]
        return None

    name_col = find_col(name_opts)
    lat_col = find_col(lat_opts)
    lon_col = find_col(lon_opts)
    price_col = find_col(price_opts)

    # Fallback: detect numeric columns if missing
    numeric_cols = []
    for c in cols:
        try:
            float(df.iloc[0][c])
            numeric_cols.append(c)
        except Exception:
            continue

    if lat_col is None and len(numeric_cols) > 0:
        lat_col = numeric_cols[0]
    if lon_col is None and len(numeric_cols) > 1:
        lon_col = numeric_cols[1]
    if price_col is None and len(numeric_cols) > 2:
        price_col = numeric_cols[-1]
    if name_col is None:
        # choose first non-numeric column
        for c in cols:
            if c not in numeric_cols:
                name_col = c
                break
        if name_col is None:
            name_col = cols[0]

    stations = []

    for _, row in df.iterrows():
        try:
            name = str(row[name_col]).strip()
            lat = float(row[lat_col])
            lon = float(row[lon_col])
            price = float(row[price_col])
            stations.append({"name": name, "lat": lat, "lon": lon, "price": price})
        except Exception:
            continue

    if not stations:
        raise ValueError("No valid station rows found in CSV.")

    stations.sort(key=lambda s: s["price"])
    return stations



def find_station_for_point(lat: float, lon: float, stations: List[Dict], radius_m: float = 50000) -> Dict:
    candidates = []
    for s in stations:
        d = haversine_m(lat, lon, s["lat"], s["lon"])
        if d <= radius_m:
            candidates.append((d, s))

    if candidates:
        candidates.sort(key=lambda x: (x[1]["price"], x[0]))
        return candidates[0][1]

    # fallback: nearest station
    stations_sorted = sorted(stations, key=lambda s: haversine_m(lat, lon, s["lat"], s["lon"]))
    return stations_sorted[0]


def cumulative_distances(coords: List[List[float]]) -> List[float]:
    cum = [0.0]
    for i in range(1, len(coords)):
        lon1, lat1 = coords[i-1]
        lon2, lat2 = coords[i]
        d = haversine_m(lat1, lon1, lat2, lon2)
        cum.append(cum[-1] + d)
    return cum


def compute_stops(coords_geojson: List[List[float]], stations: List[Dict],
                  max_range_m: float = 500 * 1609.344, mpg: float = 10.0,
                  radius_m: float = 50000) -> Dict:

    if not coords_geojson or len(coords_geojson) < 2:
        return {
            "total_distance_m": 0.0,
            "total_distance_miles": 0.0,
            "total_gallons": 0.0,
            "stops": [],
            "estimated_cost": 0.0
        }

    cum = cumulative_distances(coords_geojson)
    total_distance_m = cum[-1]
    stops = []
    last_stop_dist_m = 0.0
    remaining_range = max_range_m

    # trip fits in one tank
    if total_distance_m <= remaining_range:
        total_gallons = (total_distance_m / 1609.344) / mpg
        return {
            "total_distance_m": round(total_distance_m, 2),
            "total_distance_miles": round(meters_to_miles(total_distance_m), 3),
            "total_gallons": round(total_gallons, 3),
            "stops": [],
            "estimated_cost": 0.0
        }

    safe_counter = 0
    while last_stop_dist_m + remaining_range < total_distance_m and safe_counter < 50:
        safe_counter += 1

        target_m = last_stop_dist_m + remaining_range
        idx = next((i for i, v in enumerate(cum) if v >= target_m), len(cum)-1)
        lon, lat = coords_geojson[idx]

        station = find_station_for_point(lat, lon, stations, radius_m)
        dist_remaining = total_distance_m - cum[idx]
        fill_distance_m = min(dist_remaining, max_range_m)
        gallons = (fill_distance_m / 1609.344) / mpg
        cost = gallons * station["price"]

        stops.append({
            "station": station,
            "stop_coord": {"lat": lat, "lon": lon},
            "distance_from_start_m": round(cum[idx], 2),
            "gallons": round(gallons, 3),
            "cost": round(cost, 2)
        })

        last_stop_dist_m = cum[idx]
        remaining_range = max_range_m

    total_gallons = (total_distance_m / 1609.344) / mpg
    total_cost = sum(s["cost"] for s in stops)

    return {
        "total_distance_m": round(total_distance_m, 2),
        "total_distance_miles": round(meters_to_miles(total_distance_m), 3),
        "total_gallons": round(total_gallons, 3),
        "stops": stops,
        "estimated_cost": round(total_cost, 2)
    }
