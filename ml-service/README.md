# QuickClean service-mix ML (weather + season)

Joins Jobber jobs from your n8n webhook with **Open-Meteo** (no API key) historical and forecast daily series for Montreal, then fits a small **Ridge** multi-output model on weekly **service mix** (same categories as the dashboard `detectSvc`).

## Environment

| Variable | Description |
|----------|-------------|
| `WEBHOOK_URL` | Full n8n webhook URL. Required for `GET /ingest`. |
| `MTL_LAT` | Default `45.5017` |
| `MTL_LON` | Default `-73.5673` |
| `MIN_WEEKS_ML` | Minimum ISO weeks with at least one job to train ML (default `8`; raise when you have more history) |

## Run

```powershell
cd ml-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:WEBHOOK_URL="https://your-instance.app.n8n.cloud/webhook/..."
uvicorn app.main:app --host 127.0.0.1 --port 8788
```

Then:

1. `GET http://127.0.0.1:8788/ingest` — pulls JSON from `WEBHOOK_URL` into `data/last_snapshot.json`
2. `GET http://127.0.0.1:8788/predict/service-mix` — trains (in-memory) and returns next-week mix vs seasonal baseline

Set `C.mlApi = 'http://127.0.0.1:8788'` in `index.html` so the dashboard calls the service.

## Optional

`POST /ingest` with the same JSON body the webhook returns — avoids the server needing `WEBHOOK_URL`.
