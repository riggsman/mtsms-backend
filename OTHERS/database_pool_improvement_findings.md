# Database Connection Pool — Codebase Scan & Improvement Plan

**Generated:** 2026-05-24  
**Reference:** [database_pool_issue_analysis.md](./database_pool_issue_analysis.md)  
**Scope:** Full scan of `mtsms-backend` for pool exhaustion causes, session management risks, and recommended fixes.

---

## Executive Summary

The production error `QueuePool limit of size 5 overflow 10 reached` is consistent with the current codebase. The global SQLAlchemy engine uses **default pool limits (5 base + 10 overflow = 15 max connections)** with no explicit `pool_size` or `max_overflow` configured. Multiple layers compete for those connections on every request:

- HTTP middleware (tenant activation + analytics)
- FastAPI dependency chain (`get_tenant`, `get_db`, auth)
- JWT token creation (DB lookup on every token issued)
- APScheduler background jobs
- Heavy platform analytics queries (N+1 patterns)

**Correction to the original analysis:** `pool_pre_ping=True` and `pool_recycle=3600` are **already implemented**. The primary gaps are **undersized pool configuration**, **connection churn**, **sync ORM in async handlers**, and **one confirmed session leak** in the class reminder scheduler.

---

## Current Pool Configuration

| Setting | Global engine | Tenant engines (multi-tenant) | Source |
|---------|---------------|-------------------------------|--------|
| `pool_size` | **5 (SQLAlchemy default)** | **5 (default)** | Not set in code |
| `max_overflow` | **10 (default)** | **10 (default)** | Not set in code |
| `pool_timeout` | 30 | 30 | Explicit |
| `pool_pre_ping` | ✅ True | ✅ True | Explicit |
| `pool_recycle` | ✅ 3600s | ✅ 3600s | Explicit |

**Files:**
- `app/database/base.py` — lines 12–17, 27
- `app/database/sessionManager.py` — lines 39–47, 169–195 (`tenant_engine` cache)

---

## Findings (Ranked by Severity)

### F1 — Default pool size too small — **CRITICAL**

**Location:** `app/database/base.py:12–17`, `app/database/sessionManager.py:42–47`

**Problem:** Only 15 connections per engine. Under normal load (middleware + dependencies idempotent API calls + analytics dashboard), the pool saturates quickly.

**Evidence:**
```python
engine = create_engine(
    url,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
    # pool_size and max_overflow omitted → defaults 5 + 10
)
```

**Recommended fix:**
```python
# app/conf/config.py — add env-driven settings
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "30"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "60"))

# app/database/base.py — centralize engine kwargs
ENGINE_KWARGS = {
    "pool_pre_ping": True,
    "pool_recycle": 3600,
    "pool_timeout": settings.DB_POOL_TIMEOUT,
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_MAX_OVERFLOW,
}
```

**Also:** Apply the same kwargs in both `create_engine_with_retry` implementations (`base.py` and `sessionManager.py`). Document total MySQL `max_connections` budget: `(workers × (pool_size + max_overflow)) + tenant engines`.

---

### F2 — Class reminder job session leak — **CRITICAL**

**Location:** `app/tasks/schedule_reminder_task.py:18–55`

**Problem:** `db.close()` is only called on the success path (line 53). Any exception before that leaks a connection until pool recycle/timeout.

**Evidence:**
```python
def send_class_reminders():
    try:
        db: Session = next(get_db_session())
        # ... long-running work including asyncio.run() ...
        db.close()  # ← never reached on exception
    except Exception as e:
        logger.error(...)
```

**Recommended fix:**
```python
def send_class_reminders():
    db = None
    try:
        db = next(get_db_session())
        reminder_service = ScheduleReminderService(db)
        # ... work ...
    except Exception as e:
        logger.error(f"Error in send_class_reminders task: {str(e)}", exc_info=True)
    finally:
        if db is not None:
            db.close()
```

**Additional scheduler fixes (same file, lines 69–75):**
- Add `max_instances=1`, `coalesce=True`, `misfire_grace_time=30`
- Consider interval of 2–5 minutes if jobs routinely exceed 60s
- Release DB session **before** SMTP/email I/O (see F8)

---

### F3 — Per-tenant engines multiply pool capacity — **CRITICAL** (multi-tenant mode)

**Location:** `app/database/sessionManager.py:34, 169–195`

**Problem:** Each tenant gets a cached engine with its own 5+10 pool. With N tenants, theoretical max connections ≈ **N × 15**, which can exceed MySQL limits.

**Recommended fix:**
- Short term: use smaller per-tenant pools (`pool_size=2`, `max_overflow=3`)
- Medium term: PgBouncer or MySQL connection proxy
- Long term: consolidate to shared DB mode where possible, or lazy-evict unused tenant engines

---

### F4 — Sync SQLAlchemy inside async FastAPI — **HIGH**

**Locations (representative):**
- `app/routes/platform_analytics.py` — all endpoints
- `app/routes/system_admin.py:133–169` — `/system/analytics`
- Most route files using `async def` + `Session = Depends(get_db)`

**Problem:** Synchronous `db.query()` blocks the event loop. Under load, requests queue up while holding DB connections, increasing pool pressure and latency.

**Recommended fix:**
- **Short term:** Wrap heavy sync query blocks in `await run_in_threadpool(fn, db, ...)`
- **Medium term:** Migrate to `AsyncSession` + `asyncmy`/`aiomysql`
- **Immediate:** Mark read-heavy analytics routes as `def` (sync) so FastAPI runs them in a thread pool automatically

---

### F5 — Tenant activation middleware DB on most requests — **HIGH**

**Location:** `app/middleware/tenant_activation_middleware.py:61–124`  
**Registered:** `server.py:119–121`

**Problem:** Every authenticated `/api/v1/*` request (non-exempt) opens a global DB session and runs:
1. JWT decode + `User` lookup (`_load_user_from_request`, line 58)
2. `resolve_tenant_for_user` (line 86)
3. `is_tenant_suspended` / `is_tenant_services_activated` (lines 90–101)

This duplicates work already done in route dependencies (`get_tenant`, `require_tenant_services_activated`).

**Positive:** Session is closed in `finally` before `call_next` (lines 121–124) — no hold during handler execution.

**Recommended fix:**
1. Cache activation status per `(tenant_id, feature_version)` with 60–300s TTL (Redis or in-memory)
2. Avoid full `User` query — decode `institution_id` from JWT claims directly
3. Merge middleware logic into a single dependency to eliminate duplicate DB round-trips
4. Expand exempt list for read-only health/status endpoints if safe

---

### F6 — `get_tenant()` opens up to 3 ad-hoc sessions per request — **HIGH**

**Location:** `app/dependencies/tenantDependency.py:97–113, 140–164, 178–222`

**Problem:** `get_tenant()` is a FastAPI dependency used by `get_db`. It may open separate `DefaultSessionLocal()` sessions for:
- JWT institution_id → tenant lookup (lines 97–113)
- Header validation in shared mode (lines 140–164)
- Tenant existence check in multi-tenant mode (lines 178–222)

Each opens and closes correctly (`finally: db.close()`), but causes **2–3 extra connection acquisitions per request** before the route handler even runs.

**Recommended fix:**
- Refactor to a single lookup per request; pass resolved tenant via `request.state`
- Cache tenant records by `(name|domain)` with short TTL
- In shared mode, trust JWT `institution_id` when header matches (already partially done)

---

### F7 — JWT creation queries DB on every token — **HIGH**

**Location:** `app/authentication/authenticator.py:76–87, 107–118, 126–137`

**Problem:** `_get_effective_access_token_expire_minutes()` and `_get_effective_refresh_token_expire_days()` each open a DB session and query `SystemSettings` on **every** `create_access_token` / `create_refresh_token` call. Login can trigger **4 DB round-trips** for token expiry alone.

**Recommended fix:**
```python
# Load once at startup + invalidate on settings update
_settings_cache: Optional[tuple[float, SystemSettings]] = None
_SETTINGS_TTL = 300  # seconds

def _get_cached_system_settings(db_factory=DefaultSessionLocal):
    global _settings_cache
    now = time.time()
    if _settings_cache and now - _settings_cache[0] < _SETTINGS_TTL:
        return _settings_cache[1]
    with db_factory() as db:
        settings = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
        _settings_cache = (now, settings)
        return settings
```

Invalidate cache when system settings are updated via admin API.

---

### F8 — Class reminder job holds connection during email I/O — **HIGH**

**Locations:**
- `app/tasks/schedule_reminder_task.py:47–51` — `asyncio.run(...)` inside job while session open
- `app/services/schedule_reminder_service.py:441–448` — nested `next(get_db_session())` per institution in loop

**Problem:**
1. One DB connection held for the entire job duration including SMTP sends
2. Per-institution tenant name lookup opens additional sessions inside the loop
3. `asyncio.run()` called multiple times per minute (once per reminder time)

**Recommended fix:**
1. Prefetch all tenant names in one query before the institution loop
2. Close DB session before email sending; reopen only for reminder status writes
3. Use a single event loop for the job instead of repeated `asyncio.run()`
4. Replace `next(get_db_session())` with `create_standalone_db_session()` (already exists at `sessionManager.py:218`)

**Comparison:** `app/tasks/tenant_billing_reminder_task.py:14–23` uses correct `try/finally: db.close()` pattern — use as template.

---

### F9 — Platform analytics N+1 queries — **HIGH**

**Location:** `app/services/platform_analytics_queries.py:535–608` (`get_tenants_matrix`)

**Problem:** Loads all tenants, then runs **5 separate `.count()` queries per tenant** (login failures, emails sent/failed, API requests, OTP generated). With 50 tenants = **1 + 250 queries**, holding one session for the entire duration.

**Similar patterns:**
- `get_summary()` — lines 58–104 (multiple separate count queries)
- `get_tenant_growth_series` / `get_user_activity_series` — day/month loops with per-bucket counts

**Recommended fix:**
```sql
-- Example: aggregate login failures by tenant in one query
SELECT tenant_id, COUNT(*) 
FROM login_audit_events 
WHERE outcome = 'failure' AND created_at BETWEEN :start AND :end
GROUP BY tenant_id
```

- Add composite indexes: `(tenant_id, created_at)` on analytics tables
- Paginate `tenants-matrix` endpoint
- Run heavy analytics in background job with cached results

---

### F10 — Analytics middleware adds 1–2 writes per API request — **MEDIUM**

**Locations:**
- `app/middleware/analytics_middleware.py:34–93`
- `app/services/analytics_service.py:21–30` (`_session_write`)
- `app/helpers/analytics_context.py:24–42` (optional DB lookup for tenant name)

**Problem:** After every `/api/*` and `/auth/*` request, `record_api_request` opens a new session. 4xx/5xx responses trigger a second session via `record_platform_error`.

**Positive:** `_session_write` correctly uses `try/finally: db.close()`.

**Recommended fix:**
- Buffer analytics events in memory queue; flush via background worker
- Or batch inserts every N seconds
- Resolve tenant name from JWT `institution_id` without DB lookup in `analytics_context.py`

---

### F11 — Widespread `next(get_db_session())` anti-pattern — **MEDIUM**

**Locations (non-exhaustive):**
| File | Lines | Has `finally` close? |
|------|-------|----------------------|
| `app/tasks/schedule_reminder_task.py` | 24 | ❌ (leak risk) |
| `app/tasks/tenant_billing_reminder_task.py` | 16 | ✅ |
| `app/authentication/authenticator.py` | 80, 111 | ✅ |
| `app/apis/login.py` | 25, 131 | ✅ |
| `app/apis/users.py` | 117, 413, 505, 655, 721, 866 | ✅ |
| `app/apis/students.py` | various | ✅ |
| `app/apis/teachers.py` | 125 | ✅ |
| `app/routes/uploads.py` | 98 | ✅ |
| `app/routes/register_user.py` | 136 | ✅ |
| `app/services/schedule_reminder_service.py` | 442 | ✅ |

**Problem:** Bypassing FastAPI's `yield`-based DI is fragile; new code may omit `finally`.

**Recommended fix:** Standardize on:
```python
from app.database.sessionManager import create_standalone_db_session

db = create_standalone_db_session()
try:
  ...
finally:
  db.close()
```
Or use context manager: `with DefaultSessionLocal() as db:`

---

### F12 — Multi-tenant API opens many tenant sessions — **MEDIUM**

**Location:** `app/apis/tenant.py` — lines 206, 284, 398, 443, 508, 575, 795, 842, 960

**Problem:** Tenant provisioning/management opens separate `TenantSessionLocal()` sessions per operation. Some code paths may not close sessions on all branches.

**Recommended fix:** Audit each block for `try/finally: db.close()`. Prefer `create_standalone_db_session(tenant_name)` with explicit lifecycle.

---

### F13 — Two independent BackgroundSchedulers — **LOW–MEDIUM**

**Locations:**
- `app/tasks/schedule_reminder_task.py:15` — runs every 1 minute
- `app/tasks/tenant_billing_reminder_task.py:11` — runs daily at 08:00 UTC
- `server.py:347–368` — both started on app startup

**Problem:** Two scheduler threads compete for the same connection pool. Class reminder job has no `max_instances` guard beyond APScheduler default.

**Recommended fix:** Consolidate into one `BackgroundScheduler` with multiple jobs, or run schedulers in a separate worker process.

---

### F14 — Background ranking jobs — **LOW** (good pattern)

**Location:** `app/services/ranking_jobs.py:63–88`

**Positive:** Uses `create_standalone_db_session()` with `finally: db.close()` in thread pool workers. Use as reference implementation.

---

## Per-Request Connection Budget (Typical Authenticated API)

| Step | Connections (approx.) | Held during handler? |
|------|----------------------|----------------------|
| `tenant_activation_middleware` | 1 | No (closed before handler) |
| `get_tenant()` | 0–2 | No |
| `get_current_user` / `get_db` | 1 | Yes (entire handler) |
| `get_institution_id_from_header` | 0–1 | No |
| Route handler | 0 (reuses `get_db`) | — |
| `analytics_middleware` (post-response) | 1–2 | No |

**Peak:** 2–4 simultaneous acquisitions from the global pool per request. A dashboard firing 6 parallel analytics endpoints can consume **6+ connections** concurrently.

---

## Alignment with Original Analysis

| Original claim | Code scan result |
|----------------|------------------|
| Pool 5 / overflow 10 | ✅ Confirmed (SQLAlchemy defaults) |
| Missing `pool_pre_ping`, `pool_recycle` | ❌ **Already present** in `base.py` and `sessionManager.py` |
| `tenant_activation_middleware` heavy | ✅ Confirmed — 1 session + multiple queries per request |
| Class reminder scheduler issues | ✅ Confirmed — leak risk + long job duration |
| Platform analytics endpoints | ✅ Confirmed — especially `get_tenants_matrix` N+1 |
| Poor session management | ⚠️ Mostly correct `yield`/`finally` in DI; **one confirmed leak** in scheduler |
| Sync SQLAlchemy in async app | ✅ Confirmed across routes and jobs |

---

## Prioritized Action Plan

### Immediate (today)

| # | Action | File(s) | Effort |
|---|--------|---------|--------|
| 1 | Add explicit `pool_size` / `max_overflow` via env config | `app/database/base.py`, `app/database/sessionManager.py`, `app/conf/config.py` | Low |
| 2 | Fix `send_class_reminders()` with `finally: db.close()` | `app/tasks/schedule_reminder_task.py` | Low |
| 3 | Add scheduler job guards (`max_instances=1`, `coalesce=True`) | `app/tasks/schedule_reminder_task.py` | Low |
| 4 | Cache `SystemSettings` for token expiry (remove per-token DB hits) | `app/authentication/authenticator.py` | Low |

### This week

| # | Action | File(s) | Effort |
|---|--------|---------|--------|
| 5 | Refactor `get_tenant()` to single session / request.state cache | `app/dependencies/tenantDependency.py` | Medium |
| 6 | Add activation-status cache to tenant middleware | `app/middleware/tenant_activation_middleware.py` | Medium |
| 7 | Rewrite `get_tenants_matrix` with aggregated SQL | `app/services/platform_analytics_queries.py` | Medium |
| 8 | Prefetch tenant names in reminder service; close DB before SMTP | `app/services/schedule_reminder_service.py` | Medium |
| 9 | Add DB indexes on analytics tables `(tenant_id, created_at)` | Alembic migration | Low |

### Medium term

| # | Action | Effort |
|---|--------|--------|
| 10 | Async SQLAlchemy migration or consistent `run_in_threadpool` | High |
| 11 | Analytics write-behind queue (reduce per-request DB writes) | Medium |
| 12 | PgBouncer / connection proxy | Medium |
| 13 | Pool monitoring endpoint / metrics (`engine.pool.status()`) | Low |
| 14 | Consolidate schedulers into single process or external worker | Medium |

---

## Files Requiring Modification

### Must change (pool / leaks / schedulers)

- `app/database/base.py`
- `app/database/sessionManager.py`
- `app/conf/config.py`
- `app/tasks/schedule_reminder_task.py`
- `app/services/schedule_reminder_service.py`
- `app/authentication/authenticator.py`

### High impact (middleware / dependencies / analytics)

- `app/middleware/tenant_activation_middleware.py`
- `app/dependencies/tenantDependency.py`
- `app/middleware/analytics_middleware.py`
- `app/services/analytics_service.py`
- `app/helpers/analytics_context.py`
- `app/services/platform_analytics_queries.py`
- `app/routes/platform_analytics.py`
- `app/routes/system_admin.py`
- `app/dependencies/institutionDependency.py`

### Secondary (schedulers / tenant API cleanup)

- `app/tasks/tenant_billing_reminder_task.py`
- `server.py`
- `app/apis/tenant.py`

### Optional standardization (`next(get_db_session())` → context manager)

- `app/apis/login.py`
- `app/apis/users.py`
- `app/apis/students.py`
- `app/apis/teachers.py`
- `app/routes/uploads.py`
- `app/routes/register_user.py`

---

## Suggested Engine Configuration (Production Starting Point)

```python
# app/conf/config.py
DB_POOL_SIZE: int = 20          # tune based on worker count
DB_MAX_OVERFLOW: int = 30
DB_POOL_TIMEOUT: int = 60
DB_POOL_RECYCLE: int = 1800     # 30 min (reduce from 3600 if stale conn issues)

# Budget check:
# max_connections_needed ≈ uvicorn_workers × (DB_POOL_SIZE + DB_MAX_OVERFLOW)
# Must stay below MySQL max_connections (leave headroom for admin/migrations)
```

Enable `echo_pool=True` temporarily in staging to observe checkout/checkin patterns before tuning.

---

## Monitoring Checklist

- [ ] Log `engine.pool.status()` periodically (checked out, overflow, checked in)
- [ ] Alert when pool checkout wait exceeds 5s
- [ ] Track APScheduler job duration vs interval (class reminder must finish < 60s)
- [ ] Monitor MySQL `Threads_connected` vs configured max
- [ ] Add integration test that simulates concurrent requests and verifies no pool timeout

---

**Status:** Critical — pool exhaustion is actively impacting production stability.  
**Next step:** Implement Immediate actions (#1–#4) before load increases further.

---

## Implementation Log (2026-05-24)

The following fixes from this document were implemented in code:

| # | Fix | Status |
|---|-----|--------|
| F1 | Env-driven `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` via `app/database/engine_config.py` | ✅ Done |
| F2 | Class reminder scheduler `finally: db.close()` + job guards | ✅ Done |
| F3 | Smaller per-tenant pools (`TENANT_DB_POOL_SIZE=2`) | ✅ Done |
| F5 | Tenant activation middleware TTL cache (120s) | ✅ Done |
| F6 | `get_tenant()` consolidated to single DB session per path | ✅ Done |
| F7 | SystemSettings cache for token expiry + invalidation on PUT | ✅ Done |
| F8 | Reminder service: prefetch tenant names, single `asyncio.run` | ✅ Done |
| F9 | `get_tenants_matrix` aggregated GROUP BY queries | ✅ Done |

**New env vars:** `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`, `TENANT_DB_POOL_SIZE`, `TENANT_DB_MAX_OVERFLOW`, `SYSTEM_SETTINGS_CACHE_TTL`, `TENANT_ACTIVATION_CACHE_TTL`

**Tests added:** `app/tests/test_database_pool_fixes.py` (4 unit tests; run with `pytest app/tests/test_database_pool_fixes.py --noconftest`)
