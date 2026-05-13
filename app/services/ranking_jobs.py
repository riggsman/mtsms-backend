import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Dict, Optional, Set, Tuple

from app.database.sessionManager import create_standalone_db_session
from app.services.ranking_service import rank_students_per_course

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ranking-worker")
_enqueued_keys: Set[Tuple[int, str, str, str]] = set()
_enqueue_lock = Lock()


def _compute_scope_key(
    institution_id: int, course_code: str, academic_year: str, semester_or_term: str
) -> Tuple[int, str, str, str]:
    return (int(institution_id), str(course_code), str(academic_year), str(semester_or_term))


def enqueue_rank_recompute(
    *,
    institution_id: int,
    course_code: str,
    academic_year: str,
    semester_or_term: str,
    reason: str = "score_updated",
    tenant_name: Optional[str] = None,
) -> Dict[str, str]:
    scope_key = _compute_scope_key(institution_id, course_code, academic_year, semester_or_term)
    correlation_id = str(uuid.uuid4())
    with _enqueue_lock:
        if scope_key in _enqueued_keys:
            return {"status": "deduplicated", "correlation_id": correlation_id}
        _enqueued_keys.add(scope_key)
    _executor.submit(
        _run_recompute_job,
        institution_id,
        course_code,
        academic_year,
        semester_or_term,
        reason,
        correlation_id,
        tenant_name,
    )
    return {"status": "enqueued", "correlation_id": correlation_id}


def _run_recompute_job(
    institution_id: int,
    course_code: str,
    academic_year: str,
    semester_or_term: str,
    reason: str,
    correlation_id: str,
    tenant_name: Optional[str],
) -> None:
    scope_key = _compute_scope_key(institution_id, course_code, academic_year, semester_or_term)
    db = None
    try:
        db = create_standalone_db_session(tenant_name=tenant_name)
        result = rank_students_per_course(
            db=db,
            institution_id=institution_id,
            course_code=course_code,
            semester_or_term=semester_or_term,
            academic_year=academic_year,
        )
        logger.info(
            "[ranking-job] success correlation_id=%s reason=%s scope=%s rows_upserted=%s",
            correlation_id,
            reason,
            scope_key,
            result.get("rows_upserted"),
        )
    except Exception as exc:
        logger.exception(
            "[ranking-job] failed correlation_id=%s reason=%s scope=%s error=%s",
            correlation_id,
            reason,
            scope_key,
            exc,
        )
    finally:
        if db is not None:
            db.close()
        with _enqueue_lock:
            _enqueued_keys.discard(scope_key)
