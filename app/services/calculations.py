from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
UTC = timezone.utc
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from collections import defaultdict

from sqlalchemy import delete, select, or_
from sqlalchemy.orm import Session, joinedload

from ..models import (
    AllocationRule,
    BillingPeriod,
    ChargeAllocation,
    LeasePlacement,
    UtilityCharge,
    Tariff,
)


TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")

UTILITY_LABELS_CALC = {
    "heat": "Теплоэнергия",
    "electricity": "Электричество",
    "water": "Водоснабжение",
    "cleaning": "Уборка",
    "rent": "Аренда",
}


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class RuleContext:
    mode: str
    base_area_mode: str
    overrides: dict[int, tuple[str, Decimal]]


def overlaps(start_date: date, end_date: Optional[date], period_start: date, period_end: date) -> bool:
    actual_end = end_date or date.max
    return start_date <= period_end and actual_end >= period_start


def get_charge_amount(charge: UtilityCharge) -> Decimal:
    if charge.input_mode in ("amount", "tariff"):
        return quantize_money(Decimal(charge.amount or 0))
    if charge.meter_from is None or charge.meter_to is None or charge.tariff is None:
        return ZERO
    consumed = Decimal(charge.meter_to) - Decimal(charge.meter_from)
    if consumed < 0:
        return ZERO
    return quantize_money(consumed * Decimal(charge.tariff))


def resolve_rule_context(db: Session, charge: UtilityCharge) -> RuleContext:
    rules = db.scalars(
        select(AllocationRule)
        .where(
            AllocationRule.object_id == charge.object_id,
            AllocationRule.utility_type == charge.utility_type,
            AllocationRule.is_active.is_(True),
        )
    ).all()

    default_rule = next((rule for rule in rules if rule.tenant_id is None), None)
    mode = charge.allocation_mode or (default_rule.mode if default_rule else "area")
    base_area_mode = default_rule.base_area_mode if default_rule else "active_leases"
    overrides: dict[int, tuple[str, Decimal]] = {}
    for rule in rules:
        if rule.tenant_id is None or rule.value is None or not rule.value_type:
            continue
        overrides[rule.tenant_id] = (rule.value_type, Decimal(rule.value))
    return RuleContext(mode=mode, base_area_mode=base_area_mode, overrides=overrides)


def collect_active_placements(db: Session, charge: UtilityCharge, period: BillingPeriod) -> List[LeasePlacement]:
    placements = db.scalars(
        select(LeasePlacement)
        .options(joinedload(LeasePlacement.tenant), joinedload(LeasePlacement.object))
        .where(
            LeasePlacement.object_id == charge.object_id,
            LeasePlacement.is_active.is_(True),
        )
    ).all()
    return [
        placement
        for placement in placements
        if overlaps(placement.start_date, placement.end_date, period.start_date, period.end_date)
    ]


def calculate_by_tariffs(
    db: Session,
    object_id: int,
    tenant_id: int,
    utility_type: str,
    active_start: date,
    active_end: date,
    days_in_period: int,
    area: Decimal,
    fallback_tariff: Optional[Decimal] = None
) -> tuple[Decimal, List[dict]]:
    tariffs = db.scalars(
        select(Tariff)
        .where(
            Tariff.object_id == object_id,
            or_(Tariff.tenant_id == tenant_id, Tariff.tenant_id.is_(None)),
            Tariff.utility_type == utility_type,
            Tariff.is_active.is_(True),
            Tariff.start_date <= active_end,
            or_(Tariff.end_date >= active_start, Tariff.end_date.is_(None))
        )
    ).all()

    total_amount = ZERO
    day_details = []
    
    current_date = active_start
    current_tariff = None
    interval_start = active_start
    interval_days = 0
    
    def get_tariff_for_date(d: date) -> Optional[Decimal]:
        tenant_tariffs = [t for t in tariffs if t.tenant_id == tenant_id and t.start_date <= d and (t.end_date is None or t.end_date >= d)]
        if tenant_tariffs:
            return sorted(tenant_tariffs, key=lambda x: x.start_date)[-1].value
        general_tariffs = [t for t in tariffs if t.tenant_id is None and t.start_date <= d and (t.end_date is None or t.end_date >= d)]
        if general_tariffs:
            return sorted(general_tariffs, key=lambda x: x.start_date)[-1].value
        return fallback_tariff

    while current_date <= active_end:
        t_val = get_tariff_for_date(current_date)
        if interval_days == 0:
            current_tariff = t_val
            interval_start = current_date
            interval_days = 1
        elif t_val == current_tariff:
            interval_days += 1
        else:
            if current_tariff is None:
                raise ValueError(
                    f"Не задан тариф для '{utility_type}' на объекте ID {object_id} для арендатора ID {tenant_id} на дату {interval_start}."
                )
            interval_amount = area * current_tariff * Decimal(interval_days) / Decimal(days_in_period)
            total_amount += interval_amount
            day_details.append({
                "start": interval_start.isoformat(),
                "end": (current_date - timedelta(days=1)).isoformat(),
                "days": interval_days,
                "tariff": str(current_tariff),
                "amount": str(quantize_money(interval_amount))
            })
            current_tariff = t_val
            interval_start = current_date
            interval_days = 1
        current_date += timedelta(days=1)
        
    if interval_days > 0:
        if current_tariff is None:
            raise ValueError(
                f"Не задан тариф для '{utility_type}' на объекте ID {object_id} для арендатора ID {tenant_id} на дату {interval_start}."
            )
        interval_amount = area * current_tariff * Decimal(interval_days) / Decimal(days_in_period)
        total_amount += interval_amount
        day_details.append({
            "start": interval_start.isoformat(),
            "end": active_end.isoformat(),
            "days": interval_days,
            "tariff": str(current_tariff),
            "amount": str(quantize_money(interval_amount))
        })
        
    return quantize_money(total_amount), day_details


def calculate_rent_allocations(db: Session, period: BillingPeriod) -> List[ChargeAllocation]:
    placements = db.scalars(
        select(LeasePlacement)
        .options(joinedload(LeasePlacement.tenant), joinedload(LeasePlacement.object))
        .where(LeasePlacement.is_active.is_(True))
    ).all()
    
    active_placements = [
        p for p in placements
        if overlaps(p.start_date, p.end_date, period.start_date, period.end_date)
    ]
    
    days_in_period = (period.end_date - period.start_date).days + 1
    allocations = []
    
    for p in active_placements:
        active_start = max(period.start_date, p.start_date)
        active_end = min(period.end_date, p.end_date or date.max)
        
        # Check if rent tariff exists
        has_tariff = db.scalar(
            select(Tariff.id)
            .where(
                Tariff.object_id == p.object_id,
                or_(Tariff.tenant_id == p.tenant_id, Tariff.tenant_id.is_(None)),
                Tariff.utility_type == "rent",
                Tariff.is_active.is_(True),
                Tariff.start_date <= active_end,
                or_(Tariff.end_date >= active_start, Tariff.end_date.is_(None))
            )
        ) is not None or p.rent_tariff is not None

        if not has_tariff:
            continue
            
        rent_amount, day_details = calculate_by_tariffs(
            db=db,
            object_id=p.object_id,
            tenant_id=p.tenant_id,
            utility_type="rent",
            active_start=active_start,
            active_end=active_end,
            days_in_period=days_in_period,
            area=Decimal(p.occupied_area),
            fallback_tariff=p.rent_tariff
        )
        
        active_days = (active_end - active_start).days + 1
        coef = Decimal(active_days) / Decimal(days_in_period)
        
        audit = {
            "charge_amount": str(rent_amount),
            "calculated_at": datetime.now(UTC).isoformat(),
            "base_area_mode": "active_leases",
            "occupied_area": str(p.occupied_area),
            "active_days": active_days,
            "days_in_period": days_in_period,
            "coefficient": str(coef),
            "tariff_details": day_details,
            "formula": f"{p.occupied_area} кв.м * тариф * {active_days}/{days_in_period} дней"
        }
        
        allocations.append(
            ChargeAllocation(
                billing_period_id=period.id,
                utility_charge_id=None,
                object_id=p.object_id,
                tenant_id=p.tenant_id,
                placement_id=p.id,
                base_area=Decimal(p.occupied_area),
                share_value=coef,
                amount=rent_amount,
                mode="tariff",
                manual_override=False,
                audit_payload=json.dumps(audit, ensure_ascii=False)
            )
        )
        
    return allocations


def calculate_tariff_utility_allocations(db: Session, period: BillingPeriod, charge: UtilityCharge) -> List[ChargeAllocation]:
    placements = db.scalars(
        select(LeasePlacement)
        .options(joinedload(LeasePlacement.tenant), joinedload(LeasePlacement.object))
        .where(
            LeasePlacement.object_id == charge.object_id,
            LeasePlacement.is_active.is_(True)
        )
    ).all()
    
    active_placements = [
        p for p in placements
        if overlaps(p.start_date, p.end_date, period.start_date, period.end_date)
    ]
    
    days_in_period = (period.end_date - period.start_date).days + 1
    allocations = []
    
    for p in active_placements:
        active_start = max(period.start_date, p.start_date)
        active_end = min(period.end_date, p.end_date or date.max)
        
        amount, day_details = calculate_by_tariffs(
            db=db,
            object_id=charge.object_id,
            tenant_id=p.tenant_id,
            utility_type=charge.utility_type,
            active_start=active_start,
            active_end=active_end,
            days_in_period=days_in_period,
            area=Decimal(p.occupied_area),
            fallback_tariff=charge.tariff
        )
        
        active_days = (active_end - active_start).days + 1
        coef = Decimal(active_days) / Decimal(days_in_period)
        
        audit = {
            "charge_amount": str(amount),
            "calculated_at": datetime.now(UTC).isoformat(),
            "base_area_mode": "active_leases",
            "occupied_area": str(p.occupied_area),
            "active_days": active_days,
            "days_in_period": days_in_period,
            "coefficient": str(coef),
            "tariff_details": day_details,
            "formula": f"{p.occupied_area} кв.м * тариф * {active_days}/{days_in_period} дней"
        }
        
        allocations.append(
            ChargeAllocation(
                billing_period_id=period.id,
                utility_charge_id=charge.id,
                object_id=charge.object_id,
                tenant_id=p.tenant_id,
                placement_id=p.id,
                base_area=Decimal(p.occupied_area),
                share_value=coef,
                amount=amount,
                mode="tariff",
                manual_override=False,
                audit_payload=json.dumps(audit, ensure_ascii=False)
            )
        )
        
    return allocations


def build_allocations(
    db: Session,
    period: BillingPeriod,
    charge: UtilityCharge,
) -> List[ChargeAllocation]:
    charge_amount = get_charge_amount(charge)
    placements = collect_active_placements(db, charge, period)
    if not placements:
        charge_label = charge.utility_type
        obj_name = getattr(charge.object, 'name', f'ID {charge.object_id}')
        raise ValueError(
            f"Нет активных арендаторов на объекте '{obj_name}' в расчётном периоде. "
            f"Распределение счёта за '{charge_label}' невозможно."
        )

    days_in_period = (period.end_date - period.start_date).days + 1
    
    placement_weights = {}
    tenant_weights = defaultdict(Decimal)
    
    for p in placements:
        active_start = max(period.start_date, p.start_date)
        active_end = min(period.end_date, p.end_date or date.max)
        active_days = (active_end - active_start).days + 1
        coef = Decimal(active_days) / Decimal(days_in_period)
        weight = Decimal(p.occupied_area) * coef
        placement_weights[p.id] = (weight, coef, active_days)
        tenant_weights[p.tenant_id] += weight

    rule_context = resolve_rule_context(db, charge)
    
    if rule_context.base_area_mode == "object_total":
        denominator = Decimal(charge.object.total_area)
    else:
        denominator = sum(weight for weight, _, _ in placement_weights.values())
        
    if denominator <= 0:
        return []

    fixed_total = ZERO
    percent_total = ZERO
    manual_amounts: dict[int, Decimal] = {}
    manual_percent: dict[int, Decimal] = {}

    for tenant_id, (value_type, value) in rule_context.overrides.items():
        if value_type == "fixed":
            fixed_total += quantize_money(value)
            manual_amounts[tenant_id] = quantize_money(value)
        elif value_type == "percent":
            percent_total += value
            manual_percent[tenant_id] = value

    if rule_context.mode == "manual" and not (manual_amounts or manual_percent):
        return []
    if fixed_total > charge_amount:
        raise ValueError(f"Сумма фиксированных правил ({fixed_total}) превышает сумму счета ({charge_amount}).")
    if percent_total > Decimal("100"):
        raise ValueError("Сумма процентных правил превышает 100%.")

    allocations: List[ChargeAllocation] = []
    auto_candidates_placements = [
        p for p in placements 
        if p.tenant_id not in manual_amounts and p.tenant_id not in manual_percent
    ]
    
    remaining_amount = charge_amount - fixed_total
    
    for tenant_id, percent in manual_percent.items():
        amount = quantize_money(charge_amount * (percent / Decimal("100")))
        remaining_amount -= amount
        manual_amounts[tenant_id] = amount

    remaining_amount = quantize_money(remaining_amount)
    if remaining_amount < Decimal("0.00"):
        raise ValueError("Сумма ручных правил (фиксированные + проценты) превышает сумму счета.")
    
    if rule_context.base_area_mode == "object_total":
        auto_denominator = denominator
    else:
        auto_denominator = sum(placement_weights[p.id][0] for p in auto_candidates_placements)

    for p in placements:
        tenant_id = p.tenant_id
        weight, coef, active_days = placement_weights[p.id]
        amount = ZERO
        share_value = ZERO
        manual_override = False

        if tenant_id in manual_amounts:
            tenant_total_weight = tenant_weights[tenant_id]
            if tenant_total_weight > 0:
                share_value = weight / tenant_total_weight
                amount = quantize_money(manual_amounts[tenant_id] * share_value)
            else:
                amount = ZERO
            manual_override = True
        else:
            if rule_context.mode == "manual":
                amount = ZERO
            else:
                if auto_denominator <= 0:
                    amount = ZERO
                else:
                    share_value = (weight / auto_denominator).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                    amount = quantize_money(remaining_amount * share_value)

        denom_used = auto_denominator if tenant_id not in manual_amounts else denominator
        share_pct = float(weight / denom_used * 100) if denom_used > 0 else 0
        formula_str = (
            f"{charge_amount} × {float(weight):.4f} / {float(denom_used):.4f} = {amount}"
            if not manual_override
            else f"Ручное правило: {amount} руб."
        )
        audit = {
            "charge_amount": str(charge_amount),
            "calculated_at": datetime.now(UTC).isoformat(),
            "base_area_mode": rule_context.base_area_mode,
            "occupied_area": str(p.occupied_area),
            "active_days": active_days,
            "days_in_period": days_in_period,
            "coefficient": str(coef),
            "weight": str(weight),
            "denominator": str(denom_used),
            "share_pct": f"{share_pct:.2f}%",
            "formula": formula_str,
        }
        allocations.append(
            ChargeAllocation(
                billing_period_id=period.id,
                utility_charge_id=charge.id,
                object_id=charge.object_id,
                tenant_id=tenant_id,
                placement_id=p.id,
                base_area=Decimal(p.occupied_area),
                share_value=share_value,
                amount=amount,
                mode=rule_context.mode if not manual_override else "manual",
                manual_override=manual_override,
                audit_payload=json.dumps(audit, ensure_ascii=False),
            )
        )

    total = sum(Decimal(a.amount) for a in allocations)
    delta = quantize_money(charge_amount - total)
    if delta != ZERO and allocations:
        target_allocation = None
        for a in reversed(allocations):
            if not a.manual_override:
                target_allocation = a
                break
        if target_allocation is not None:
            target_allocation.amount = quantize_money(Decimal(target_allocation.amount) + delta)

    return allocations


def recalculate_period(db: Session, billing_period_id: int) -> List[ChargeAllocation]:
    period = db.get(BillingPeriod, billing_period_id)
    if period is None:
        raise ValueError("Период не найден.")
    if period.status == "closed":
        raise ValueError("Закрытый период пересчитывать нельзя.")

    db.execute(delete(ChargeAllocation).where(ChargeAllocation.billing_period_id == billing_period_id))
    db.flush()

    created: List[ChargeAllocation] = []
    errors: List[str] = []

    # Calculate Rent
    try:
        created.extend(calculate_rent_allocations(db, period))
    except ValueError as e:
        errors.append(f"Аренда: {e}")

    # Calculate Charges
    charges = db.scalars(
        select(UtilityCharge)
        .options(joinedload(UtilityCharge.object))
        .where(UtilityCharge.billing_period_id == billing_period_id)
    ).all()

    for charge in charges:
        charge_label = UTILITY_LABELS_CALC.get(charge.utility_type, charge.utility_type)
        try:
            if charge.input_mode == "tariff":
                charge_allocs = calculate_tariff_utility_allocations(db, period, charge)
                charge.amount = sum(a.amount for a in charge_allocs)
                created.extend(charge_allocs)
            else:
                created.extend(build_allocations(db, period, charge))
        except ValueError as e:
            errors.append(f"{charge_label}: {e}")

    for allocation in created:
        db.add(allocation)
    period.status = "calculated"
    db.commit()

    if errors:
        raise ValueError("Расчёт завершён с предупреждениями:\n" + "\n".join(f"• {e}" for e in errors))

    return created


def close_period(db: Session, billing_period_id: int) -> BillingPeriod:
    period = db.get(BillingPeriod, billing_period_id)
    if period is None:
        raise ValueError("Период не найден.")
    if period.status == "draft":
        raise ValueError("Сначала выполните расчет периода.")
    period.status = "closed"
    period.closed_at = datetime.now(UTC)
    db.commit()
    return period


def allocation_totals_by_tenant(db: Session, billing_period_id: int) -> dict[int, Decimal]:
    totals: dict[int, Decimal] = {}
    allocations = db.scalars(
        select(ChargeAllocation).where(ChargeAllocation.billing_period_id == billing_period_id)
    ).all()
    for item in allocations:
        totals[item.tenant_id] = quantize_money(totals.get(item.tenant_id, ZERO) + Decimal(item.amount))
    return totals

