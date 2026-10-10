# Spotter Trip Planner

Assessment-ready Django + React MVP for planning a property-carrying truck trip under the FMCSA-style assumptions in the brief.

## What is included

- Location, pickup, drop-off, and current cycle-used inputs.
- Django JSON API at `POST /api/trip-plan/`.
- OSRM routing and Nominatim geocoding with a deterministic fallback when the public services are unavailable.
- HOS planner covering 11-hour driving, 14-hour duty window, 30-minute break after 8 driving hours, 10-hour reset, and 70/8 cycle tracking.
- Fuel planning at no more than 1,000-mile intervals.
- Responsive React dashboard with route visualization, stop milestones, compliance summary, and printable daily ELD-style logs.

## Run locally

### Backend

```powershell
cd backend
C:/Users/aradh/anaconda3/python.exe -m pip install -r requirements.txt
C:/Users/aradh/anaconda3/python.exe manage.py runserver
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Set `VITE_API_URL` if the API is deployed separately.

## Deploy for the assessment

### 1. Deploy the Django API to Render

Push this folder to GitHub, then create a new **Web Service** on [Render](https://render.com):

- Repository: your GitHub repository
- Root directory: `backend`
- Runtime: `Python`
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn spotter.wsgi:application --bind 0.0.0.0:$PORT`
- Health check path: `/api/health/`
- Add these Render environment variables:

```text
DJANGO_SECRET_KEY=<generate-a-long-random-value>
DJANGO_DEBUG=False
ALLOWED_HOSTS=YOUR-RENDER-SERVICE.onrender.com
```

After deployment, verify:

```text
https://YOUR-RENDER-SERVICE.onrender.com/api/health/
```

It should return `{"status":"ok","service":"Spotter trip planner"}`.

### 2. Deploy the React frontend to Vercel

Create a new project on [Vercel](https://vercel.com) from the same GitHub repository:

- Framework preset: `Vite`
- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable:

```text
VITE_API_URL=https://YOUR-RENDER-SERVICE.onrender.com/api
```

Deploy the Vercel project and open its URL. Submit that URL as the hosted assessment version.

The included `render.yaml` can also be used as a Render Blueprint. The frontend environment variable must still be configured in Vercel.

## Scope note

This is a planning aid, not a certified electronic logging device. The calculations intentionally use the assessment's simplified assumptions and should be reviewed by a qualified carrier safety specialist before operational use.
