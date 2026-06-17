# 🧠 ML Model Serving API — Flask + PostgreSQL + Nginx on Docker

A production-style machine learning inference platform built from scratch. Trains a scikit-learn classification model, serves predictions via a Flask REST API, persists every request to PostgreSQL, and orchestrates the full stack with Docker Compose — complete with Nginx load balancing across two API replicas, automated health checks, and resilience testing.

> **Author:** [saadcnx](https://github.com/saadcnx)

---

## 🏗️ Architecture

```
                        ┌─────────────────────────────────┐
                        │         Nginx (Port 80)          │
                        │      Round-Robin Load Balancer   │
                        └────────────┬──────────┬──────────┘
                                     │          │
                          ┌──────────▼──┐   ┌───▼──────────┐
                          │  ml-api:1   │   │   ml-api:2   │
                          │  Port 5001  │   │   Port 5002  │
                          │             │   │              │
                          │ Flask + sklearn model (iris)   │
                          └──────┬──────┘   └──────┬───────┘
                                 │                 │
                          ┌──────▼─────────────────▼───────┐
                          │         PostgreSQL 15           │
                          │      predictions table          │
                          │   (persists all /predict calls) │
                          └─────────────────────────────────┘
```

---

## 🗂️ Project Structure

```
.
├── api/
│   ├── Dockerfile                  # python:3.11-slim based image
│   ├── app.py                      # Flask REST API (predict, health, history)
│   ├── train_model.py              # scikit-learn iris classifier + serialization
│   ├── model.pkl                   # Serialized trained model (fixed seed)
│   └── requirements.txt            # Pinned Python dependencies
├── db/
│   └── init.sql                    # PostgreSQL schema — predictions table
├── nginx/
│   └── nginx.conf                  # Round-robin upstream config
├── tests/
│   └── test_api.py                 # End-to-end validation script (plain requests)
└── docker-compose.yml              # Full stack orchestration
```

---

## 🔌 API Reference

### `GET /health`
Returns service status and model load confirmation.

```json
{
  "status": "healthy",
  "model_loaded": true,
  "container_id": "a3f9c1d..."
}
```

### `POST /predict`
Accepts four iris feature floats, returns class prediction with probabilities.

```bash
curl -X POST http://localhost/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [5.1, 3.5, 1.4, 0.2]}'
```

```json
{
  "predicted_class": "setosa",
  "prediction": 0,
  "probabilities": {
    "setosa": 0.97,
    "versicolor": 0.02,
    "virginica": 0.01
  }
}
```

Returns `HTTP 400` if fewer than four features are provided.

### `GET /predictions/history?limit=N`
Returns the last N prediction records from PostgreSQL.

```json
[
  {
    "id": 12,
    "timestamp": "2025-06-10T14:23:01Z",
    "features": [5.1, 3.5, 1.4, 0.2],
    "predicted_class": "setosa",
    "probabilities": { "setosa": 0.97, "versicolor": 0.02, "virginica": 0.01 }
  }
]
```

---

## 🐳 Docker Compose Services

| Service | Image | Port | Role |
|---|---|---|---|
| `postgres` | `postgres:15` | 5432 | Prediction persistence |
| `ml-api-1` | `ml-api:v1` | 5001 | API replica 1 |
| `ml-api-2` | `ml-api:v1` | 5002 | API replica 2 |
| `nginx` | `nginx:alpine` | 80 | Load balancer |

---

## 🚀 Quick Start

**Prerequisites:** Docker Engine 24.0+, Docker Compose v2

```bash
git clone https://github.com/saadcnx/ml-model-serving-docker.git
cd ml-model-serving-docker

# Build and start the full stack
docker compose up -d

# Verify all containers are healthy
docker compose ps

# Health check through Nginx
curl -s http://localhost/health

# Make a prediction
curl -s -X POST http://localhost/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [5.1, 3.5, 1.4, 0.2]}'

# View prediction history
curl -s "http://localhost/predictions/history?limit=5"
```

---

## ✅ End-to-End Test Suite

A plain Python test script (no framework) validates the full API surface and exits `0` on success, `1` on any failure.

```bash
python3 tests/test_api.py
```

**Test cases covered:**

| Test | Expected Result |
|---|---|
| `GET /health` | `status: healthy`, `model_loaded: true` |
| Predict `[5.1, 3.5, 1.4, 0.2]` | `setosa` |
| Predict `[6.2, 2.9, 4.3, 1.3]` | `versicolor` |
| Predict `[7.3, 2.9, 6.3, 1.8]` | `virginica` |
| Malformed request (3 features) | `HTTP 400` |
| `GET /predictions/history` | Returns array with correct fields |

All three class predictions are deterministic — guaranteed by a fixed random seed in the training script.

---

## 🔄 Load Balancing Verification

```bash
# Hit /health 10 times — container_id rotates between the two replicas
for i in $(seq 1 10); do
  curl -s http://localhost/health | python3 -m json.tool | grep container_id
done
```

---

## 💥 Resilience Testing

```bash
# Stop one replica
docker compose stop ml-api-1

# All 10 requests still return HTTP 200 (Nginx routes to surviving replica)
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost/predict \
    -H "Content-Type: application/json" \
    -d '{"features":[5.1,3.5,1.4,0.2]}'
done

# Restart and verify recovery within 60 seconds
docker compose start ml-api-1
curl -s http://localhost:5001/health

# Confirm no data loss in PostgreSQL
docker exec -it <postgres-container> psql -U postgres -d ml_predictions \
  -c "SELECT COUNT(*) FROM predictions;"
```

---

## 🗄️ Database Schema

```sql
CREATE TABLE predictions (
    id            SERIAL PRIMARY KEY,
    timestamp     TIMESTAMPTZ DEFAULT NOW(),
    features      JSONB NOT NULL,
    predicted_class TEXT NOT NULL,
    prediction    INTEGER NOT NULL,
    probabilities JSONB NOT NULL,
    container_id  TEXT
);
```

---

## ✅ Production Patterns Applied

- [x] Model trained and serialized at image build time — zero runtime training
- [x] Stateless API replicas — any replica can serve any request
- [x] PostgreSQL for durable prediction history — survives container restarts
- [x] Nginx round-robin — traffic distributed evenly across replicas
- [x] Health checks on all services — Compose waits for readiness before routing
- [x] `HTTP 400` on malformed input — input validation at API boundary
- [x] Fixed random seed — deterministic, reproducible predictions
- [x] Single-command stack startup via `docker compose up -d`

---

## 🧰 Tech Stack

- **ML:** scikit-learn (Iris classifier), joblib, numpy
- **API:** Flask, psycopg2
- **Database:** PostgreSQL 15
- **Proxy:** Nginx (alpine)
- **Containerization:** Docker Engine, Docker Compose v2
- **Base Image:** `python:3.11-slim`

---

## 📖 Further Reading

- [Flask Quickstart](https://flask.palletsprojects.com/en/3.0.x/quickstart/)
- [scikit-learn Model Persistence](https://scikit-learn.org/stable/model_persistence.html)
- [Nginx Upstream Load Balancing](https://nginx.org/en/docs/http/load_balancing.html)
- [Docker Compose Health Checks](https://docs.docker.com/compose/compose-file/05-services/#healthcheck)
- [PostgreSQL Docker Official Image](https://hub.docker.com/_/postgres)
