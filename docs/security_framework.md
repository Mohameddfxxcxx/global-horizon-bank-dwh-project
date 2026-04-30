# Security Framework — Global Horizon Bank

Defense-in-depth security across identity, data access, encryption, and audit.

---

## 1. Identity & Access Management

### Database Roles
| Role | Permissions |
|---|---|
| `role_executive` | Read-only across analytical surface; UNMASK granted |
| `role_engineer` | Full DML, EXECUTE on stored procs, UNMASK granted |
| `role_analyst` | Read-only with masked PII |
| `role_teller` | EXECUTE on `usp_OpenAccount`, `usp_PostTransaction`, `usp_TransferFunds` only |

Defined in `sql/oltp/06_security_rbac.sql`.

### Principle of Least Privilege
- No login uses `db_owner` outside DBA emergency.
- Service accounts are scoped per environment (dev / staging / prod).
- DDL is restricted to migration accounts.

---

## 2. Row-Level Security (RLS)

Branch-bounded access for tellers via `rls.fn_BranchAccessPredicate` policy `rls.sp_BranchAccess`.

```sql
ALTER SECURITY POLICY rls.sp_BranchAccess WITH (STATE = ON);
INSERT INTO rls.UserBranch (UserName, BranchID) VALUES ('teller_cairo_01', 100);
```

A teller logged in as `teller_cairo_01` will see rows in `Accounts`, `Loans`, and `Employees` only for `BranchID = 100`. Executives and engineers bypass via `IS_MEMBER` check.

---

## 3. Dynamic Data Masking

| Column | Mask | Visible to |
|---|---|---|
| `Customers.Email` | `email()` (e.g., `aXXX@XXXX.com`) | UNMASK roles only |
| `Customers.Phone` | partial, last 4 digits | UNMASK roles only |
| `Customers.Address` | full default mask | UNMASK roles only |

`role_analyst` sees masked values; `role_engineer` and `role_executive` have `UNMASK` granted.

---

## 4. Encryption

| Layer | Mechanism |
|---|---|
| **At Rest** | SQL Server TDE recommended (out-of-scope of this repo's scripts but documented) |
| **In Transit** | TLS for SQL Server connections; Streamlit served via TLS in production |
| **Backups** | Encrypted backup files using SQL Server BACKUP encryption certificates |

---

## 5. Audit & Lineage

### Trigger-Based Audit
- `tr_Accounts_Audit` records every INSERT/UPDATE/DELETE on `Accounts` to `audit.AccountChanges`.
- `tr_Transactions_Audit` records every transaction to `audit.TransactionLog`.

### ETL Audit
`dbo.ETL_Audit_Log` captures every pipeline step with RunID, timestamps, row counts, status, error message, and DQ score.

### DDL Audit (recommended)
Enable SQL Server Server-Audit specs to capture DDL across both databases.

---

## 6. PII Catalog

| Field | Classification | Treatment |
|---|---|---|
| Customers.Email | PII | Masked + UNMASK gated |
| Customers.Phone | PII | Masked |
| Customers.Address | PII | Masked |
| Customers.DateOfBirth | PII | Range-validated; not masked but restricted via RBAC |
| Customers.FullName | PII | Restricted via RBAC |

---

## 7. GDPR-style Controls

- **Right to access** — `CustomerID` enables retrieval of all linked rows via FK chain.
- **Right to erasure** — soft-delete pattern; future enhancement: cryptographic shredding.
- **Retention** — Audit logs retained 7 years; transactional history retained 10 years per banking regulation.
- **Lineage** — `_ingested_at`, `_source_file` on Bronze; `RunID` on `ETL_Audit_Log`.

---

## 8. Disaster Recovery (DR)

| Tier | RPO | RTO | Mechanism |
|---|---|---|---|
| **Hot** | 15 min | 1 h | SQL Server Always On AG (production) |
| **Warm** | 4 h | 4 h | Nightly full backup + log shipping |
| **Cold** | 24 h | 24 h | Geo-replicated container registry + scripted re-bootstrap from CSV |

DR drill cadence: quarterly. Steps in [`runbook.md`](runbook.md).

---

## 9. Secrets Management

- All credentials referenced via env vars (`SQLSERVER_PASSWORD` etc.).
- `.env` is in `.gitignore`; `.env.example` is the template.
- For Streamlit Cloud: use the Secrets panel.
- For Kubernetes: use `Secret` objects; never bake credentials into images.

---

## 10. Compliance Checklist

| Control | Status |
|---|---|
| RBAC | ✅ |
| RLS | ✅ (toggle ON in prod) |
| PII masking | ✅ |
| TDE | 📋 Documented; enable in prod |
| Backup strategy | ✅ Documented in runbook |
| Audit trail | ✅ |
| Lineage | ✅ |
| Secrets out of source | ✅ |
| Data classification catalog | ✅ |
| DR drill | 📋 Quarterly |
