# Operational Runbook — Global Horizon Bank Platform

Primary on-call reference for incident response, routine operations, and DR procedures.

---

## 1. Daily Health Checks

| Check | Command | Expected |
|---|---|---|
| SQL Server reachable | `docker compose ps sql-server` | `running` |
| Latest ETL run | `SELECT TOP 1 * FROM dbo.ETL_Audit_Log ORDER BY StartedAtUTC DESC` | `Status = SUCCESS` within last 6 h |
| Dashboard health | `curl -fsS http://localhost:8501/_stcore/health` | HTTP 200 |
| Disk usage | `df -h /var/opt/mssql` | < 80% |

---

## 2. Standard Operating Procedures

### 2.1 Bootstrap a fresh environment
```bash
docker-compose up -d sql-server
python src/data_generation.py        # synthetic data
python src/setup_sqlserver.py        # creates DBs, loads, runs ETL
streamlit run dashboard/app_executive.py
```

### 2.2 Refresh the warehouse
```sql
EXEC dbo.usp_RunMasterPipeline;
```

### 2.3 Refresh aggregates
```sql
EXEC dbo.usp_RefreshAggregates;
```

### 2.4 Train ML models
```bash
python -m src.ml.churn_model
python -m src.ml.fraud_model
python -m src.ml.forecast
```

---

## 3. Incident Playbooks

### IR-01: ETL pipeline failure
1. Inspect `ETL_Audit_Log`:
   ```sql
   SELECT TOP 20 * FROM dbo.ETL_Audit_Log
   WHERE Status = 'FAILED' ORDER BY StartedAtUTC DESC;
   ```
2. Identify failed step and `ErrorMessage`.
3. If transient → re-run `EXEC dbo.usp_RunMasterPipeline;`.
4. If logical → check the source data; do not blindly retry.
5. File post-mortem ticket if duration exceeded SLA.

### IR-02: Dashboard slow / unresponsive
1. `docker compose logs dashboard --tail=200`.
2. Check latest aggregate refresh time.
3. Restart container: `docker compose restart dashboard`.
4. If still slow, check SQL CPU and `sys.dm_exec_requests`.

### IR-03: Suspected data corruption
1. **Do not** truncate or delete. Snapshot current state.
2. Compare row counts vs. ETL audit log.
3. Restore from latest verified backup.
4. Replay incremental load from Bronze.

### IR-04: Security incident — leaked credential
1. Rotate password in env / secret manager.
2. Force re-deploy of all services using the secret.
3. Audit `audit.AccountChanges` and `audit.TransactionLog` for the time window.
4. Open ticket; notify CISO if PII access is suspected.

---

## 4. Disaster Recovery Procedure

1. Provision target host with Docker.
2. `docker compose up -d sql-server`.
3. Restore the latest full backup of `GlobalHorizon_OLTP` and `GlobalHorizon_DWH`.
4. Validate row counts vs. backup metadata.
5. Run `EXEC dbo.usp_RunMasterPipeline;` to bring DWH up to date.
6. Smoke-test the dashboard.
7. Update DNS / load balancer.

Target RTO: 4 h. Target RPO: 4 h (warm tier) / 15 min (hot tier).

---

## 5. Backup Strategy

| Type | Cadence | Retention |
|---|---|---|
| Full | Nightly | 30 days |
| Differential | Every 6 h | 7 days |
| Transaction log | Every 15 min | 24 h |
| Off-site (S3/Azure Blob) | Daily | 90 days |

---

## 6. Routine Maintenance

| Task | Cadence |
|---|---|
| Index reorganize/rebuild | Weekly |
| Statistics update | Weekly |
| Audit log purge (> 7 years) | Monthly |
| DR drill | Quarterly |
| Security review | Quarterly |
| Schema migration window | Monthly maintenance window |

---

## 7. Useful Diagnostic Queries

```sql
-- Top wait stats
SELECT TOP 10 wait_type, wait_time_ms, waiting_tasks_count
FROM sys.dm_os_wait_stats ORDER BY wait_time_ms DESC;

-- Currently running queries
SELECT session_id, status, command, total_elapsed_time, blocking_session_id
FROM sys.dm_exec_requests WHERE session_id > 50;

-- Largest tables
SELECT TOP 10 t.name, p.rows
FROM sys.tables t
JOIN sys.partitions p ON t.object_id = p.object_id
WHERE p.index_id IN (0, 1)
ORDER BY p.rows DESC;
```

---

## 8. Escalation Matrix

| Severity | Definition | Response | Escalation |
|---|---|---|---|
| **P1** | Production down, data corruption, security breach | < 15 min | Head of Data + CISO |
| **P2** | Degraded performance, single-tab failure | < 1 h | On-call engineer |
| **P3** | Cosmetic, non-blocking | Next business day | Backlog |
