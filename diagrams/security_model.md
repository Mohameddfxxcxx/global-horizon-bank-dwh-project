# Security Access Model

```mermaid
flowchart TD
    USER[DB Login] --> AUTHN{Authentication}
    AUTHN -->|valid| ROLE{Role mapping}
    AUTHN -->|invalid| DENY[Deny]

    ROLE -->|role_executive| EXEC[Read-only · UNMASK · all branches]
    ROLE -->|role_engineer| ENG[Full DML · UNMASK · all branches]
    ROLE -->|role_analyst| AN[Read-only · MASKED · all branches]
    ROLE -->|role_teller| TL[EXECUTE on procs · branch-bound RLS]

    EXEC & ENG & AN & TL --> RLS{RLS Predicate}
    RLS -->|allowed| DATA[(Tables / Views)]
    RLS -->|blocked| HIDE[Filtered out]

    DATA --> AUDIT[(audit.* tables<br/>ETL_Audit_Log)]
```

**Key controls**
- RLS: `rls.fn_BranchAccessPredicate` enforces branch boundary for tellers.
- Masking: Email, Phone, Address have dynamic data masks applied; analyst role does not have UNMASK.
- Audit: every DML on `Accounts` and `Transactions` is captured by triggers.
