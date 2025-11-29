# Fuel Route Planner API

A Django-based backend API that calculates the optimal, cost-efficient fuel stops along a driving route in the USA.  
The route is generated using free and open APIs (Nominatim + OSRM), and fuel prices are taken from the provided CSV file.

This project is built exactly according to the assignment requirements.

---

##  Features

- **POST /api/route/** endpoint for generating route + fuel plan  
- Uses **Nominatim (OpenStreetMap)** for geocoding  
- Uses **OSRM** (router.project-osrm.org) for routing — **only one routing call**  
- Vehicle assumptions:
  - **500-mile range**
  - **10 miles per gallon**
  - **Start with a full tank**
- Greedy algorithm to select the most cost-effective stations along the route  
- CSV of fuel prices loaded from project root (`fuel-prices-for-be-assessment.csv`)  
- Returns:
  - Route geometry (GeoJSON-style `[lon, lat]` list)
  - Total distance & duration
  - Optimal fuel stops:
    - coordinates  
    - price per gallon  
    - along-route distance  
    - gallons purchased  
    - cost at stop  
  - Total cost of trip  
  - Total gallons required



## Project Structure

project-root/
│
├── manage.py
├── fuel-prices-for-be-assessment.csv ← MUST be here
├── requirements.txt
├── README.md
│
├── fuel_route_project/
│ ├── settings.py
│ ├── urls.py
│ └── ...
│
└── routeapi/
├── views.py
├── urls.py
└── ...

## Installation & Setup

### Create & activate a virtual environment


python -m venv venv
source venv/bin/activate     # macOS / Linux
# or
venv\Scripts\activate        # Windows
# Install dependencies

pip install -r requirements.txt
# Ensure CSV is in correct location
fuel-prices-for-be-assessment.csv
in the same directory as manage.py.

# Run migrations
python manage.py migrate
# (Optional) Create admin superuser

python manage.py createsuperuser
#Start development server
python manage.py runserver
The server will run at:
http://127.0.0.1:8000/
🧪 API Usage
Endpoint

POST /api/route/
JSON Request Body
