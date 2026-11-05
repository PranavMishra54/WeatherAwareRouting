# Weather-Aware Truck Routing

Compare truck routes using weather forecasts and load-aware risk analysis. Explore route conditions on a map, forecast timeline, and checkpoint list.

## Features

- Compare driving routes by risk and travel time.
- View weather and risk at route checkpoints.
- Explore forecast conditions along the route.
- Adjust checkpoint spacing and account for cargo weight.

## Run locally

You need Python 3.12+, Node.js, npm, and a Mapbox access token for live routing.

Start the backend in PowerShell:

```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DJANGO_DEBUG = "true"
$env:MAPBOX_TOKEN = "your-mapbox-token"
python manage.py migrate
python manage.py runserver
```

In a second terminal, start the frontend:

```powershell
cd frontend
npm install
$env:VITE_API_URL = "http://127.0.0.1:8000/api"
npm run dev
```

To run the frontend with sample data instead, set `$env:VITE_USE_MOCK = "true"` and omit `VITE_API_URL`.

## Tests

```powershell
cd backend
python manage.py test routing.tests
```

```powershell
cd frontend
npm run build
npm run lint
```