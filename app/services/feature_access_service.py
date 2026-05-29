"""
Feature catalog + subscription_services merge for admin matrix and tenant entitlements.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.subscription_service import SubscriptionService
from app.models.service_configuration import ServiceConfiguration
from app.models.tenant import Tenant
from app.models.tenant_feature_entitlement import TenantFeatureEntitlement

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "feature_catalog.json"
_CATALOG_CACHE: Optional[List[Dict[str, Any]]] = None


def load_feature_catalog(*, force_reload: bool = False) -> List[Dict[str, Any]]:
    global _CATALOG_CACHE
    if force_reload:
        _CATALOG_CACHE = None
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    if not _CATALOG_PATH.is_file():
        _CATALOG_CACHE = []
        return _CATALOG_CACHE
    with open(_CATALOG_PATH, encoding="utf-8") as f:
        data = json.load(f)
    _CATALOG_CACHE = list(data.get("features") or [])
    return _CATALOG_CACHE


def invalidate_feature_catalog_cache() -> None:
    global _CATALOG_CACHE
    _CATALOG_CACHE = None


def normalize_plan(subscription_plan: Optional[str]) -> str:
    s = (subscription_plan or "").strip().lower()
    if "premium" in s:
        return "premium"
    return "freemium"


def _find_service_by_button(db: Session, button_id: str) -> Optional[SubscriptionService]:
    row = (
        db.query(SubscriptionService)
        .filter(
            SubscriptionService.deleted_at.is_(None),
            SubscriptionService.button_id == button_id,
        )
        .first()
    )
    if row:
        return row
    return (
        db.query(SubscriptionService)
        .filter(
            SubscriptionService.deleted_at.is_(None),
            SubscriptionService.name == button_id,
        )
        .first()
    )


def _find_service_for_feature(db: Session, feat: Dict[str, Any]) -> Optional[SubscriptionService]:
    """Match catalog feature to an existing row by button_id, display name, or aliases."""
    button_id = feat["id"]
    row = _find_service_by_button(db, button_id)
    if row:
        return row
    names_to_try: List[str] = []
    display = (feat.get("name") or "").strip()
    if display:
        names_to_try.append(display)
    for alias in feat.get("nameAliases") or []:
        alias = (alias or "").strip()
        if alias and alias not in names_to_try:
            names_to_try.append(alias)
    for name in names_to_try:
        row = (
            db.query(SubscriptionService)
            .filter(
                SubscriptionService.deleted_at.is_(None),
                SubscriptionService.name == name,
            )
            .first()
        )
        if row:
            return row
    return None


def _find_service_by_name_or_alias(db: Session, name: str) -> Optional[SubscriptionService]:
    key = (name or "").strip()
    if not key:
        return None
    row = (
        db.query(SubscriptionService)
        .filter(
            SubscriptionService.deleted_at.is_(None),
            SubscriptionService.name == key,
        )
        .first()
    )
    if row:
        return row
    for feat in load_feature_catalog():
        aliases = feat.get("nameAliases") or []
        if key in aliases or feat.get("name") == key:
            return _find_service_by_button(db, feat["id"])
        if feat.get("id") == key:
            return _find_service_by_button(db, feat["id"])
    return (
        db.query(SubscriptionService)
        .filter(
            SubscriptionService.deleted_at.is_(None),
            SubscriptionService.button_id == key,
        )
        .first()
    )


def _flags_from_service(service: Optional[SubscriptionService], feat: Dict[str, Any]) -> Dict[str, bool]:
    if service:
        return {
            "enabled": bool(service.is_active),
            "freemium": bool(service.is_freemium_enabled),
            "premium": bool(service.is_premium_enabled),
            "monetized": bool(service.is_monetized_enabled),
        }
    return {
        "enabled": bool(feat.get("service_state_enabled", False)),
        "freemium": bool(feat.get("freemium_enabled", False)),
        "premium": bool(feat.get("premium_enabled", False)),
        "monetized": bool(feat.get("monetization_enabled", False)),
    }


def _amount_from_service(service: Optional[SubscriptionService]) -> Optional[float]:
    if not service or service.price is None:
        return None
    try:
        value = float(service.price)
        return value if value >= 0 else None
    except (TypeError, ValueError):
        return None


def _tenant_amount_override(
    db: Session,
    service: Optional[SubscriptionService],
    tenant: Optional[Tenant],
) -> Optional[float]:
    if not service or not tenant:
        return None
    service_keys = []
    if service.button_id:
        service_keys.append(service.button_id)
    if service.name and service.name not in service_keys:
        service_keys.append(service.name)
    if not service_keys:
        return None
    row = (
        db.query(ServiceConfiguration)
        .filter(
            ServiceConfiguration.tenant_id == tenant.id,
            ServiceConfiguration.service_name.in_(service_keys),
            ServiceConfiguration.configuration_key == "tenant_price_override",
            ServiceConfiguration.is_active.is_(True),
            ServiceConfiguration.deleted_at.is_(None),
        )
        .order_by(ServiceConfiguration.updated_at.desc(), ServiceConfiguration.created_at.desc())
        .first()
    )
    if not row or row.configuration_value is None:
        return None
    raw = row.configuration_value
    value = None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            value = parsed.get("amount")
        elif isinstance(parsed, (int, float, str)):
            value = parsed
    except (TypeError, ValueError, json.JSONDecodeError):
        value = raw
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return amount if amount >= 0 else None


def get_feature_matrix(db: Session) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for feat in load_feature_catalog(force_reload=True):
        button_id = feat["id"]
        service = _find_service_for_feature(db, feat)
        flags = _flags_from_service(service, feat)
        amount = _amount_from_service(service)
        items.append(
            {
                "button_id": button_id,
                "name": feat.get("name"),
                "description": feat.get("description"),
                "category": feat.get("category"),
                "service_id": service.id if service else None,
                "enabled": flags["enabled"],
                "freemium": flags["freemium"],
                "premium": flags["premium"],
                "monetized": flags["monetized"],
                "amount": amount,
                "menuIds": feat.get("menuIds") or [],
                "nameAliases": feat.get("nameAliases") or [],
            }
        )
    return items


def sync_catalog_to_db(db: Session) -> int:
    invalidate_feature_catalog_cache()
    created = 0
    updated = 0
    for feat in load_feature_catalog(force_reload=True):
        button_id = feat["id"]
        existing = _find_service_for_feature(db, feat)
        if existing:
            if existing.button_id and existing.button_id != button_id:
                continue
            changed = False
            if not existing.button_id:
                existing.button_id = button_id
                changed = True
            if feat.get("description") and not existing.description:
                existing.description = feat.get("description")
                changed = True
            if changed:
                db.add(existing)
                updated += 1
            continue
        svc = SubscriptionService(
            button_id=button_id,
            name=feat.get("name") or button_id,
            description=feat.get("description"),
            price=Decimal("0"),
            currency="USD",
            billing_period="monthly",
            is_active=bool(feat.get("service_state_enabled", True)),
            is_freemium_enabled=bool(feat.get("freemium_enabled", False)),
            is_premium_enabled=bool(feat.get("premium_enabled", False)),
            is_monetized_enabled=bool(feat.get("monetization_enabled", False)),
        )
        db.add(svc)
        created += 1
    if created or updated:
        db.commit()
    return created


def save_feature_matrix(
    db: Session,
    updates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    sync_catalog_to_db(db)
    for item in updates:
        button_id = str(item.get("button_id") or "").strip()
        if not button_id:
            continue
        feat = next((f for f in load_feature_catalog() if f["id"] == button_id), None)
        service = _find_service_for_feature(db, feat) if feat else _find_service_by_button(db, button_id)
        if not service:
            if not feat:
                continue
            service = SubscriptionService(
                button_id=button_id,
                name=feat.get("name") or button_id,
                description=feat.get("description"),
                price=Decimal("0"),
                currency="USD",
                billing_period="monthly",
            )
            db.add(service)
            db.flush()
        service.button_id = button_id
        service.is_active = bool(item.get("enabled", False))
        service.is_freemium_enabled = bool(item.get("freemium", False))
        service.is_premium_enabled = bool(item.get("premium", False))
        service.is_monetized_enabled = bool(item.get("monetized", False))
        if item.get("amount") is not None:
            try:
                service.price = Decimal(str(item.get("amount") or 0))
            except (TypeError, ValueError):
                pass
        db.add(service)
    db.commit()
    return get_feature_matrix(db)


def resolve_tenant(db: Session, institution_id: Optional[int], domain: Optional[str] = None) -> Optional[Tenant]:
    if institution_id:
        t = db.query(Tenant).filter(Tenant.id == institution_id).first()
        if t:
            return t
    if domain:
        d = domain.strip().lower()
        return (
            db.query(Tenant)
            .filter(
                (Tenant.domain == domain) | (Tenant.name == domain),
            )
            .first()
        )
    return None


def feature_allowed_for_plan(
    service: Optional[SubscriptionService],
    feat: Dict[str, Any],
    plan: str,
) -> bool:
    flags = _flags_from_service(service, feat)
    if not flags["enabled"]:
        return False
    if plan == "premium":
        return flags["premium"]
    return flags["freemium"]


def _load_tenant_entitlement_map(db: Session, tenant_id: int) -> Dict[str, bool]:
    rows = (
        db.query(TenantFeatureEntitlement)
        .filter(TenantFeatureEntitlement.tenant_id == tenant_id)
        .all()
    )
    return {row.button_id: bool(row.is_enabled) for row in rows}


def resolve_tenant_feature_access(
    service: Optional[SubscriptionService],
    feat: Dict[str, Any],
    plan: str,
    entitlement_map: Dict[str, bool],
) -> Dict[str, bool]:
    button_id = feat["id"]
    flags = _flags_from_service(service, feat)
    global_enabled = bool(flags["enabled"])
    plan_allowed = feature_allowed_for_plan(service, feat, plan)
    if button_id in entitlement_map:
        enabled_for_tenant = bool(entitlement_map[button_id])
    else:
        enabled_for_tenant = plan_allowed
    effective = plan_allowed and enabled_for_tenant
    return {
        "global_enabled": global_enabled,
        "plan_allowed": plan_allowed,
        "enabled_for_tenant": enabled_for_tenant,
        "effective": effective,
    }


def get_tenant_feature_matrix(db: Session, tenant: Tenant) -> Dict[str, Any]:
    plan = normalize_plan(tenant.subscription_plan)
    entitlement_map = _load_tenant_entitlement_map(db, tenant.id)
    items: List[Dict[str, Any]] = []
    for feat in load_feature_catalog(force_reload=True):
        button_id = feat["id"]
        service = _find_service_for_feature(db, feat)
        access = resolve_tenant_feature_access(service, feat, plan, entitlement_map)
        items.append(
            {
                "button_id": button_id,
                "name": feat.get("name"),
                "description": feat.get("description"),
                "category": feat.get("category"),
                "global_enabled": access["global_enabled"],
                "plan_allowed": access["plan_allowed"],
                "enabled_for_tenant": access["enabled_for_tenant"],
                "effective": access["effective"],
                "menuIds": feat.get("menuIds") or [],
            }
        )
    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "plan": plan,
        "items": items,
    }


def save_tenant_feature_matrix(
    db: Session,
    tenant: Tenant,
    updates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    plan = normalize_plan(tenant.subscription_plan)
    existing = {
        row.button_id: row
        for row in db.query(TenantFeatureEntitlement)
        .filter(TenantFeatureEntitlement.tenant_id == tenant.id)
        .all()
    }

    for item in updates:
        button_id = str(item.get("button_id") or "").strip()
        if not button_id:
            continue
        feat = next((f for f in load_feature_catalog() if f["id"] == button_id), None)
        if not feat:
            continue
        service = _find_service_for_feature(db, feat)
        plan_allowed = feature_allowed_for_plan(service, feat, plan)
        enabled_for_tenant = bool(item.get("enabled_for_tenant", False))

        row = existing.get(button_id)
        if enabled_for_tenant:
            if not plan_allowed:
                continue
            if row:
                row.is_enabled = True
                db.add(row)
            else:
                db.add(
                    TenantFeatureEntitlement(
                        tenant_id=tenant.id,
                        button_id=button_id,
                        is_enabled=True,
                    )
                )
        else:
            if row:
                row.is_enabled = False
                db.add(row)
            else:
                db.add(
                    TenantFeatureEntitlement(
                        tenant_id=tenant.id,
                        button_id=button_id,
                        is_enabled=False,
                    )
                )

    db.commit()
    return get_tenant_feature_matrix(db, tenant)


def get_tenant_features(
    db: Session,
    tenant: Optional[Tenant],
) -> Dict[str, bool]:
    if not tenant:
        return {}
    plan = normalize_plan(tenant.subscription_plan)
    entitlement_map = _load_tenant_entitlement_map(db, tenant.id)
    out: Dict[str, bool] = {}
    for feat in load_feature_catalog():
        button_id = feat["id"]
        service = _find_service_for_feature(db, feat)
        access = resolve_tenant_feature_access(service, feat, plan, entitlement_map)
        out[button_id] = access["effective"]
    return out


def check_service_access(
    db: Session,
    service_name: str,
    tenant: Optional[Tenant],
) -> Dict[str, Any]:
    service = _find_service_by_name_or_alias(db, service_name)
    plan = normalize_plan(tenant.subscription_plan if tenant else None)
    feat = None
    if service and service.button_id:
        feat = next((f for f in load_feature_catalog() if f["id"] == service.button_id), None)
    if not feat:
        feat = next(
            (f for f in load_feature_catalog() if f.get("name") == service_name or service_name in (f.get("nameAliases") or [])),
            None,
        )
    if not service and feat:
        service = _find_service_by_button(db, feat["id"])
    if not feat and not service:
        return {"service_name": service_name, "has_access": False}
    entitlement_map = (
        _load_tenant_entitlement_map(db, tenant.id) if tenant else {}
    )
    access = resolve_tenant_feature_access(
        service, feat or {}, plan, entitlement_map
    )
    allowed = access["effective"]
    response: Dict[str, Any] = {
        "service_name": service_name,
        "has_access": allowed,
        "plan": plan,
    }
    if service:
        response["button_id"] = service.button_id
        amount = _amount_from_service(service)
        override_amount = _tenant_amount_override(db, service, tenant)
        if override_amount is not None:
            amount = override_amount
            response["tenant_price_override"] = True
        if amount is not None:
            response["amount"] = amount
        response["is_monetized"] = bool(service.is_monetized_enabled)
        response["max_free_download"] = getattr(service, "max_free_download", None)
        response["requires_payment"] = bool(
            service.is_monetized_enabled and amount is not None and amount > 0
        )
        if plan == "freemium" and service.is_freemium_enabled:
            response["is_freemium_enabled"] = True
    elif feat:
        response["is_monetized"] = bool(feat.get("monetization_enabled", False))
    return response
