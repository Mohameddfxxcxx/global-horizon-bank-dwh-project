# Deployment Guide — Global Horizon Bank Platform

End-to-end deployment instructions covering local, container, Streamlit Cloud, and enterprise targets.

---

## 1. Prerequisites

- Python 3.11+
- Docker Desktop (optional but recommended)
- A GitHub repository (for cloud deployments)

---

## 2. Local Run

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt   # adds tests + ML

# 2. Optional: regenerate synthetic data
python src/data_generation.py

# 3. Run the executive dashboard
streamlit run dashboard/app_executive.py
```

Open `http://localhost:8501`.

---

## 3. Local SQL Server (Docker)

```bash
docker compose up -d sql-server
python src/setup_sqlserver.py        # create DBs, import CSVs, run ETL
streamlit run dashboard/app_executive.py
```

The app will discover SQL Server via the env vars defined in `.env.example`.

---

## 4. Full-Stack Docker

```bash
docker compose up --build
```

| Service | Host port | Description |
|---|---|---|
| `sql-server` | `21433` | Microsoft SQL Server 2022 |
| `dashboard` | `8501` | Streamlit Executive Analytics |

---

## 5. Streamlit Cloud

1. Push the repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io/).
3. Click **Create app** and select the repo.
4. Set the **Main file path** to `dashboard/app_executive.py`.
5. (Optional) Add SQL secrets in **Settings → Secrets**:
   ```toml
   SQLSERVER_HOST = "your-database-host"
   SQLSERVER_PORT = "1433"
   SQLSERVER_USER = "your-username"
   SQLSERVER_PASSWORD = "your-password"
   SQLSERVER_DB   = "GlobalHorizon_DWH"
   ```
6. Click **Deploy**.

For backward-compatible deployments, point at `dashboard/app.py` instead.

---

## 6. AWS / Azure / GCP — Container Deployment

The Dockerfile produces a production-ready image. Standard targets:

| Platform | Service |
|---|---|
| AWS | ECS Fargate, AppRunner |
| Azure | Container Apps, App Service for Containers |
| GCP | Cloud Run |
| Kubernetes | Helm chart can wrap the image; expose via Ingress + TLS |

Sample environment variables (Kubernetes Secret recommended):

```yaml
SQLSERVER_HOST: <db host>
SQLSERVER_PORT: "1433"
SQLSERVER_USER: <user>
SQLSERVER_PASSWORD: <secret>
SQLSERVER_DB: GlobalHorizon_DWH
GHB_ENV: production
GHB_LOG_LEVEL: INFO
```

---

## 7. CI/CD

`.github/workflows/ci.yml` runs lint, type-check, and tests on every push.
`.github/workflows/docker-publish.yml` builds and pushes a tagged image to `ghcr.io/<org>/<repo>` on `vX.Y.Z` tags.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | Missing dependency | Re-run `pip install -r requirements.txt` |
| `FileNotFoundError` for CSVs | Data dir excluded from deployment | Verify `data/raw/` is in the image / repo |
| Dashboard shows **Demo** | SQL unavailable + CSVs missing | Check env vars and data path |
| `pymssql` install fails | Missing FreeTDS | `packages.txt` includes `freetds-dev` |
| Slow charts | Cold cache | Click *Refresh Data*; verify aggregates table is populated |

---

## 9. Production Checklist

- [ ] Secrets in a vault (not source)
- [ ] TLS termination enabled
- [ ] SQL Server backups + DR drills documented
- [ ] RLS policy `sp_BranchAccess` toggled `ON`
- [ ] Monitoring on `ETL_Audit_Log.Status = 'FAILED'`
- [ ] CI green on `main`
- [ ] DR runbook validated with a quarterly drill
