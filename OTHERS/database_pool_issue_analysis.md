# Database Connection Pool Exhaustion Analysis Report

**Generated:** 2026-05-24  
**Issue:** sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached

## Executive Summary

The application is suffering from **severe database connection pool exhaustion**. The SQLAlchemy `QueuePool` is frequently hitting its limits, causing timeouts across multiple parts of the system:
- API endpoints
- Middlewares (especially tenant activation)
- Background scheduler jobs

This is a **critical performance and stability issue** that will degrade user experience and may cause cascading failures under load.

---

## Key Error Details

```python
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out, timeout 30.00
```

- **Pool Size**: 5
- **Max Overflow**: 10
- **Total Max Connections**: ~15
- **Timeout**: 30 seconds

---

## Observed Problems from Logs

### 1. Connection Pool Saturation
- Multiple components competing for the limited connections simultaneously.
- Middlewares requiring DB access on almost every request.
- Background jobs holding connections for extended periods.

### 2. Affected Components
- **tenant_activation_middleware**: Fails when loading user from DB
- **Send class reminder emails** (APScheduler job running every 60s)
- **Platform analytics endpoints** (`/api/v1/system/analytics/...`)
- General request handling (CORS, exception handlers, etc.)

### 3. Scheduler Issues
- Job skipped due to `maximum number of running instances reached (1)`
- Job failing with pool timeout
- Indicates long-running operations inside the email reminder task

### 4. High-Privilege Requests
- System SuperAdmin token being used
- Triggers more database activity (analytics, auditing)

---

## Root Causes (Ranked by Likelihood)

| Priority | Cause | Probability | Impact |
|----------|------|-------------|--------|
| 1 | Synchronous SQLAlchemy in async FastAPI app | Very High | Severe |
| 2 | Poor session management (connections not closed properly) | Very High | Severe |
| 3 | Too small connection pool configuration | High | High |
| 4 | Heavy middleware chain with DB calls | High | High |
| 5 | Long-running background tasks | High | Medium |
| 6 | Missing `pool_pre_ping`, `pool_recycle` | Medium | Medium |

---

## Recommended Fixes

### Immediate Actions (Quick Wins)

1. **Increase Pool Configuration**
   ```python
   engine = create_engine(
       DATABASE_URL,
       pool_size=30,           # Higher base connections
       max_overflow=50,
       pool_timeout=60,
       pool_recycle=1800,      # Recycle every 30 mins
       pool_pre_ping=True,     # Test connections before use
       echo_pool=True          # For debugging
   )
   ```

2. **Optimize tenant_activation_middleware**
   - Reduce DB queries
   - Cache user data when possible
   - Make it more lightweight

3. **Fix Session Management**
   - Ensure proper `try/finally` or context managers for sessions
   - Use dependency injection with `yield`

### Medium-term Improvements

- Migrate to **Async SQLAlchemy** (`AsyncSession` + `asyncpg`)
- Implement connection monitoring and metrics
- Optimize APScheduler jobs (add proper session handling)
- Consider PgBouncer or similar proxy for better pooling

---

## Action Plan

1. **Today**: Increase pool size + add `pool_pre_ping=True`
2. **This Week**: Review and fix middleware session usage
3. **Next Week**: Start migration to async SQLAlchemy
4. **Ongoing**: Add monitoring for active DB connections

---

## Files to Review / Modify

- `app/database/engine.py` (or wherever engine is created)
- `app/middleware/tenant_activation_middleware.py`
- Scheduler job: `Send class reminder emails`
- All database dependencies

---

**Status**: Critical - Needs immediate attention to prevent outages.

**Note**: This report was auto-generated based on the provided log analysis.
