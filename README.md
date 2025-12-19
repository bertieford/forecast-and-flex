# forecast-and-flex

## Setup

### 1) Create/activate your environment
This repo uses pyenv (see `.python-version`).
Activate your existing env (example):
```bash
pyenv activate forecast-and-flex
```

### Quick start for loading in data locally

1. Create Kaggle API credentials:
   https://www.kaggle.com/account → API → Create Token

2. Save locally:
   ~/.kaggle/kaggle.json

3. Run:
   make setup
   make data

## API

Run the FastAPI service from this folder:
```bash
uvicorn app.api:app --reload --port 8000
```

Example:
- Forecast data: http://localhost:8000/forecast
- Metrics: http://localhost:8000/metrics

## Dashboard

Run the Streamlit dashboard from this folder:
```bash
streamlit run app/dashboard.py
```
