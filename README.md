# Weather-Aware Truck Routing

Compare driving routes by forecast weather and load-aware risk, then inspect checkpoint conditions and an hourly corridor heatmap.

- **Live demo:** `<add live demo URL>`
- **Loom walkthrough:** `<add Loom URL>`
- **Screenshot:** `<add screenshot URL or embed>`

## Features

- Compare up to three routes, ranked by weather risk and duration.
- Estimate checkpoint ETAs from route duration and assess hourly wind, rain, and snow.
- Apply wind-related load rules to checkpoint risk.
- View route risk summaries, reasons, checkpoint details, and an hourly corridor heatmap.
- Run with live API data or the frontend's mock mode.

## How it works

1. Geocode the origin and destination with Mapbox.
2. Request three distinct driving routes from Mapbox Directions, adding waypoint-corridor routes when the provider returns fewer alternatives.
3. Place checkpoints along each full route at the selected 10-, 25-, or 50-mile interval; estimate ETAs from the route duration.
4. Fetch hourly Open-Meteo forecasts for all checkpoints and select the hour nearest each ETA.
5. Classify wind, rain, and snow risk, then apply load rules and summarize risk miles.
6. Rank routes and explain the recommendation.
7. Return simplified route paths, checkpoint data, and a load-independent hourly corridor heatmap for the map.

## Risk rules

Each weather measure is classified independently. Comparisons are continuous at the boundaries shown:

| Level | Wind (mph) | Rain (in/hr) | Snow (in/hr) |
|---|---:|---:|---:|
| Low | `< 25` | `< 0.10` | `< 0.5` |
| Moderate | `25 to < 35` | `0.10 to 0.25` | `0.5 to 1.0` |
| High | `35 to < 45` | `> 0.25 to 0.50` | `> 1.0 to 2.0` |
| Severe | `45 to < 55` | `> 0.50 to 1.00` | `> 2.0 to 3.0` |
| No travel | `>= 55` | `> 1.00` | `> 3.0` |

The checkpoint risk is the worst (highest) level among wind, rain, and snow. Load rules can only raise it:

- Wind from 45 to under 55 mph with a load **over 30,000 lb** raises risk to no travel.
- Wind from 35 to under 45 mph with a load **over 40,000 lb** raises risk to at least severe.
- The load comparisons are strict; exactly 30,000 or 40,000 lb does not trigger its rule.

Checkpoint segment miles divide the distance between adjacent checkpoints in half: interior checkpoints receive half of each neighboring gap, and endpoints receive half of their one adjacent gap. The resulting segment miles sum to the route length. Average risk is the segment-mile-weighted mean of risk levels 1–5, rounded to two decimals; if total segment miles are zero, the code uses a plain checkpoint average.

## Recommendation order

Routes are sorted ascending by **no-travel miles**, then **severe miles**, **high-risk miles**, **average risk**, and **duration**. Route ID breaks any remaining tie.

No-travel miles rank first because the recommendation prioritizes avoiding route segments classified as unsafe for travel before optimizing less severe risks or speed.

## Architecture

```text
backend/
  config/                 Django settings and URL configuration
  routing/
    serializers.py        Analyze request validation
    views.py              Health check and analysis API
    services/
      routing.py          Mapbox geocoding and driving routes
      checkpoints.py      Distance, interpolation, checkpoint ETAs
      weather.py          Open-Meteo forecasts and cache
      risk.py             Thresholds, load rules, route summaries
      recommend.py        Route ordering and explanation text
      heatmap.py          Corridor sampling and hourly frames
      geo.py              Route path simplification
      analyze.py          Analysis pipeline and response assembly
    tests/                Django service and API tests
frontend/
  src/
    api/client.ts         Live API request and mock-mode switch
    components/           Trip form, route cards, map, checkpoints, slider
    hooks/useAnalyze.ts   Request, loading, and cancellation state
    types.ts              API request and response types
```

`POST /api/analyze/` accepts an origin, destination, ISO departure time, load, and checkpoint interval. It returns the recommended route ID, routes with summaries and checkpoints, and heatmap data.

Request:

```json
{
  "origin": "Chicago, IL",
  "destination": "Dallas, TX",
  "departure_time": "2026-11-03T08:00:00Z",
  "load_weight_lb": 42000,
  "interval_miles": 25
}
```

Response shape (route and frame arrays abbreviated):

```json
{
  "recommended_route_id": 0,
  "routes": [{
    "id": 0,
    "distance_miles": 925.4,
    "duration_hours": 13.8,
    "arrival_time": "2026-11-03T21:48:00Z",
    "path": [[41.88, -87.63], [32.78, -96.80]],
    "summary": {
      "no_travel_miles": 0.0, "severe_miles": 0.0, "high_miles": 0.0,
      "moderate_miles": 0.0, "low_miles": 925.4,
      "avg_risk": 1.0, "max_risk": "low"
    },
    "recommendation_reason": "Only one route available.",
    "checkpoints": [{
      "mile": 0.0, "lat": 41.88, "lon": -87.63,
      "eta": "2026-11-03T08:00:00Z",
      "wind_mph": 12.0, "rain_in_hr": 0.0, "snow_in_hr": 0.0,
      "risk": "low", "reasons": ["Conditions normal"]
    }]
  }],
  "heatmap": {
    "hours": [0, 1],
    "frames": [[[41.88, -87.63, 0.22]]],
    "start_time": "2026-11-03T08:00:00Z"
  }
}
```

The numeric values above illustrate the response format; live results depend on the routing and forecast providers. The API returns route objects in route-ID order and may return fewer than three routes.

## Tech choices

- **Mapbox Geocoding and Directions:** geocodes locations and provides driving alternatives, distance, duration, and route geometry. Low-relevance geocoding matches are rejected. If Directions returns fewer than three alternatives, the backend requests distinct routes through nearby waypoint corridors; analysis reports an error if three distinct routes cannot be obtained.
- **Open-Meteo:** free hourly forecast API without an API key; requests wind in mph and precipitation in inches. Responses are cached for 30 minutes and coordinates are rounded and deduplicated.
- **Leaflet and leaflet.heat:** interactive route map and weather intensity overlay.
- **Django REST Framework:** request validation, JSON API responses, throttling, and health endpoint.

The current routing service uses Mapbox Geocoding. `ORS_API_KEY` appears in the deployment environment template but is not used by the current application code.

## Local setup

Prerequisites: Python 3.12 or newer, Node.js (22 recommended), npm, and a Mapbox access token. Open-Meteo requires no key.

### Backend

From the repository root:

```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `SECRET_KEY` and `MAPBOX_TOKEN` in `backend/.env`; set `DJANGO_DEBUG=true` for local development. Then:

```powershell
python manage.py migrate
python manage.py runserver
```

The API is served at `http://127.0.0.1:8000/api/`.

### Frontend

In another terminal:

```powershell
cd frontend
npm install
```

Set `VITE_API_URL=http://127.0.0.1:8000/api` and `VITE_USE_MOCK=false` in `frontend/.env.development`, then run:

```powershell
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`.

### Environment variables

| Variable | Component | Purpose |
|---|---|---|
| `SECRET_KEY` | Backend | Django secret; required when `DJANGO_DEBUG` is not true |
| `DJANGO_DEBUG` | Backend | Set to `true` for local development; defaults to false |
| `MAPBOX_TOKEN` | Backend | Mapbox Geocoding and Directions access token |
| `ALLOWED_HOSTS` | Backend | Comma-separated allowed hostnames |
| `CORS_ALLOWED_ORIGINS` | Backend | Comma-separated frontend origins |
| `CSRF_TRUSTED_ORIGINS` | Backend | Comma-separated trusted origins |
| `ORS_API_KEY` | Deployment template | Reserved/configured in Render; not currently used by code |
| `VITE_API_URL` | Frontend | API base URL, ending in `/api` |
| `VITE_USE_MOCK` | Frontend | Set to `true` to use mock results instead of the API |

### Tests and mock mode

```powershell
cd backend
python manage.py test routing.tests
```

```powershell
cd frontend
npm run build
npm run lint
```

For frontend-only work without the backend, set `VITE_USE_MOCK=true`. Mock mode returns frontend-generated sample analysis; it does not call the API.

## Deployment

### Render (backend)

1. Create a Render web service from the repository; `render.yaml` sets `rootDir: backend`, `build.sh`, Gunicorn, and `/api/health/`.
2. Configure `MAPBOX_TOKEN`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS` for the deployed domains. Render generates `SECRET_KEY`; keep `DJANGO_DEBUG=false`.
3. `ORS_API_KEY` is listed as a non-synced environment variable in the blueprint but is not presently required by application code.

### Vercel (frontend)

1. Import the repository and set the Vercel project root to `frontend`.
2. `vercel.json` configures the Vite build, `dist` output, and SPA rewrite.
3. Set `VITE_API_URL` to `https://<render-service>.onrender.com/api` and `VITE_USE_MOCK=false` for production. Vite embeds these values at build time.
4. Add the deployed Vercel origin to the backend's `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.

## Assumptions and limitations

- Route durations come from the routing API; there is no live traffic adjustment or truck-specific restriction handling.
- Forecast availability is limited to the dates and data Open-Meteo provides (the checkpoint service enforces its forecast window).
- Checkpoints and risk miles are estimates based on segment distances and interpolated positions along the route.
- Weather is hourly; checkpoint weather uses the forecast hour nearest the estimated arrival time.
- Heatmap weather is sampled along the route corridor, not at every route geometry point; output paths are simplified for the response.
- Free-tier hosting may have cold starts. The frontend pings the health endpoint at startup and shows a wake-up message if analysis takes more than five seconds.
- When the routing provider returns fewer than three alternatives, the service tries waypoint corridors to obtain three distinct routes; analysis fails explicitly if it cannot.

## Possible improvements

- Add truck-aware routing restrictions and configurable vehicle profiles.
- Add traffic-aware departure and arrival estimates.
- Show forecast confidence and data freshness in the UI.
- Add route comparison and forecast-history benchmarks.
- Add integration monitoring for provider latency, quotas, and errors.
