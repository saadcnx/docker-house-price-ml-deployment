# 🏠 House Price Prediction API — ML Model Deployment with Docker & Kubernetes

A production-style MLOps project that trains a scikit-learn regression model, wraps it in a Flask REST API, containerizes it with Docker, persists predictions to PostgreSQL, and deploys the full stack to Kubernetes with auto-scaling, liveness probes, and load balancing.

> **Author:** [saadcnx](https://github.com/saadcnx)

---

## 🏗️ Architecture

```
                    ┌──────────────────────────────────┐
                    │     Kubernetes / Docker Network   │
                    │                                   │
                    │   ┌────────────────────────────┐  │
  HTTP Requests ───────▶│  Flask REST API (Gunicorn) │  │
                    │   │  ml-house-predictor:v1.1   │  │
                    │   │  Replicas: 2 (K8s: 3)      │  │
                    │   └───────────┬────────────────┘  │
                    │               │ writes predictions │
                    │   ┌───────────▼────────────────┐  │
                    │   │      PostgreSQL 13          │  │
                    │   │   predictions table         │  │
                    │   └────────────────────────────┘  │
                    └──────────────────────────────────┘
```

---

## 🗂️ Project Structure

```
.
├── app.py                          # HousePricePredictor class (train, load, predict)
├── flask_app.py                    # Flask REST API with DB integration
├── requirements.txt                # Pinned Python dependencies
├── Dockerfile                      # python:3.9-slim based container image
├── k8s-manifests/
│   ├── postgres-deployment.yaml    # PostgreSQL Deployment + ClusterIP Service
│   ├── ml-deployment.yaml          # ML API Deployment (2 replicas) + LoadBalancer
│   └── db-init-configmap.yaml      # SQL schema init via ConfigMap
└── house_price_model.pkl           # Serialized trained model (generated on first run)
```

---

## 🔌 API Reference

### `GET /`
Returns full API documentation and example request.

### `GET /health`
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

### `POST /predict`
Accepts house features and returns a price prediction. Persists the result to PostgreSQL.

```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"size": 2500, "bedrooms": 3, "age": 10}'
```

```json
{
  "prediction": 287450.75,
  "input": { "size": 2500, "bedrooms": 3, "age": 10 }
}
```

Returns `HTTP 400` if any of `size`, `bedrooms`, or `age` are missing.

### `GET /predictions`
Returns the 10 most recent predictions from PostgreSQL.

```json
{
  "predictions": [
    {
      "id": 4,
      "size": 2500.0,
      "bedrooms": 3,
      "age": 10,
      "predicted_price": 287450.75,
      "created_at": "2025-06-10T14:23:01"
    }
  ]
}
```

### `POST /train`
Triggers a full model retrain on new synthetic data and overwrites `house_price_model.pkl`.

---

## 🐳 Docker — Quick Start

**Prerequisites:** Docker Engine 24.0+

```bash
git clone https://github.com/saadcnx/house-price-ml-deployment.git
cd house-price-ml-deployment

# Build the image
docker build -t ml-house-predictor:v1.1 .

# Create shared network
docker network create ml-network

# Start PostgreSQL
docker run -d \
  --name postgres-ml \
  --network ml-network \
  -e POSTGRES_DB=mldata \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  postgres:13

# Initialize schema
docker exec -i postgres-ml psql -U postgres -d mldata <<'EOF'
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    size REAL NOT NULL,
    bedrooms INTEGER NOT NULL,
    age INTEGER NOT NULL,
    predicted_price REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOF

# Start the ML API
docker run -d \
  --name ml-predictor \
  --network ml-network \
  -p 5000:5000 \
  -e DB_HOST=postgres-ml \
  -e DB_NAME=mldata \
  -e DB_USER=postgres \
  -e DB_PASSWORD=password \
  ml-house-predictor:v1.1

# Test it
curl http://localhost:5000/health
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"size": 2200, "bedrooms": 3, "age": 8}'
```

---

## ☸️ Kubernetes Deployment

**Prerequisites:** `kubectl`, `minikube` (or any K8s cluster)

```bash
# Start minikube and load image
minikube start
minikube image load ml-house-predictor:v1.1

# Deploy all resources
kubectl apply -f k8s-manifests/db-init-configmap.yaml
kubectl apply -f k8s-manifests/postgres-deployment.yaml
kubectl apply -f k8s-manifests/ml-deployment.yaml

# Watch pods come up
kubectl get pods -w

# Wait for PostgreSQL readiness
kubectl wait --for=condition=ready pod -l app=postgres --timeout=60s

# Initialize database schema
kubectl exec -i deployment/postgres-deployment -- \
  psql -U postgres -d mldata -c "
    CREATE TABLE IF NOT EXISTS predictions (
      id SERIAL PRIMARY KEY, size REAL, bedrooms INTEGER,
      age INTEGER, predicted_price REAL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );"

# Get the service URL and test
SERVICE_URL=$(minikube service ml-predictor-service --url)
curl $SERVICE_URL/health
curl -X POST $SERVICE_URL/predict \
  -H "Content-Type: application/json" \
  -d '{"size": 2400, "bedrooms": 3, "age": 7}'

# Scale up
kubectl scale deployment ml-predictor-deployment --replicas=3
kubectl get pods
```

---

## ⚙️ Kubernetes Manifests Overview

### ML API Deployment (`ml-deployment.yaml`)
```yaml
replicas: 2
livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### PostgreSQL Service (`postgres-deployment.yaml`)
- Type: `ClusterIP` — only reachable within the cluster
- ML API connects via `DB_HOST=postgres-service` env variable

### ML API Service (`ml-deployment.yaml`)
- Type: `LoadBalancer` — externally accessible on port 80 → container port 5000

---

## 🧠 Model Details

| Property | Value |
|---|---|
| Algorithm | Linear Regression (scikit-learn) |
| Features | `size` (sq ft), `bedrooms` (count), `age` (years) |
| Target | `predicted_price` (USD) |
| Training data | 1000 synthetic samples (seed=42) |
| Serialization | `joblib` → `house_price_model.pkl` |
| Reproducibility | Fixed `np.random.seed(42)` |

---

## 🗄️ Database Schema

```sql
CREATE TABLE predictions (
    id             SERIAL PRIMARY KEY,
    size           REAL NOT NULL,
    bedrooms       INTEGER NOT NULL,
    age            INTEGER NOT NULL,
    predicted_price REAL NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## ✅ Production Patterns Applied

- [x] Non-root container user (`mluser`, UID 1000)
- [x] Gunicorn WSGI server (2 workers) — not Flask dev server
- [x] Docker health check on `/health`
- [x] Kubernetes liveness + readiness probes
- [x] Environment variable–based database config (no hardcoded secrets)
- [x] Docker network isolation between services
- [x] K8s ConfigMap for database init script
- [x] Horizontal scaling via `kubectl scale`
- [x] `HTTP 400` on missing input fields
- [x] Graceful DB failure handling (API stays up if DB is unavailable)

---

## 🧹 Cleanup

```bash
# Docker
docker stop ml-predictor postgres-ml
docker rm ml-predictor postgres-ml
docker network rm ml-network

# Kubernetes
kubectl delete -f k8s-manifests/
minikube stop
```

---

## 🧰 Tech Stack

- **ML:** scikit-learn, pandas, numpy, joblib
- **API:** Flask, Gunicorn
- **Database:** PostgreSQL 13, psycopg2
- **Containerization:** Docker Engine, Docker networks
- **Orchestration:** Kubernetes (Deployments, Services, ConfigMaps)
- **Base Image:** `python:3.9-slim`

---

## 📖 Further Reading

- [scikit-learn — Model Persistence](https://scikit-learn.org/stable/model_persistence.html)
- [Flask Deployment with Gunicorn](https://flask.palletsprojects.com/en/3.0.x/deploying/gunicorn/)
- [Kubernetes Liveness & Readiness Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [PostgreSQL Docker Official Image](https://hub.docker.com/_/postgres)
- [Docker Networking](https://docs.docker.com/network/)
