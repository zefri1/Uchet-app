"""
Скрипт наполнения БД тестовыми данными для УК Учёт.
Запуск: .venv\Scripts\python.exe seed_data.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date
from decimal import Decimal

from app.db import Base, SessionLocal, engine
from app.models import (
    PropertyObject, Tenant, LeasePlacement,
    BillingPeriod, UtilityCharge, AllocationRule, Tariff,
    ChargeAllocation,
)
from app.services.calculations import recalculate_period
from sqlalchemy import delete, func, select, text

Base.metadata.create_all(bind=engine, checkfirst=True)

# Патч схемы: если utility_charge_id NOT NULL — пересоздаём таблицу с nullable
with engine.begin() as conn:
    cols = conn.execute(text("PRAGMA table_info(charge_allocations)")).fetchall()
    col_map = {c[1]: c for c in cols}
    utility_col = col_map.get("utility_charge_id")
    # notnull == 1 означает NOT NULL constraint
    if utility_col and utility_col[3] == 1:
        print("Обновляю схему charge_allocations (utility_charge_id -> nullable)...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS charge_allocations_new (
                id INTEGER PRIMARY KEY,
                billing_period_id INTEGER NOT NULL REFERENCES billing_periods(id),
                utility_charge_id INTEGER REFERENCES utility_charges(id),
                object_id INTEGER NOT NULL REFERENCES property_objects(id),
                tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                placement_id INTEGER REFERENCES lease_placements(id),
                base_area NUMERIC(12,2) NOT NULL DEFAULT 0,
                share_value NUMERIC(12,6) NOT NULL DEFAULT 0,
                amount NUMERIC(12,2) NOT NULL DEFAULT 0,
                mode VARCHAR(20) NOT NULL,
                manual_override BOOLEAN DEFAULT 0,
                audit_payload TEXT,
                created_at DATETIME
            )
        """))
        conn.execute(text("INSERT INTO charge_allocations_new SELECT * FROM charge_allocations"))
        conn.execute(text("DROP TABLE charge_allocations"))
        conn.execute(text("ALTER TABLE charge_allocations_new RENAME TO charge_allocations"))
        print("  OK Схема обновлена")

db = SessionLocal()

# ─── Очистка ──────────────────────────────────────────────────────────────────
print("Очищаю базу данных...")
db.execute(delete(ChargeAllocation))
db.execute(delete(UtilityCharge))
db.execute(delete(AllocationRule))
db.execute(delete(Tariff))
db.execute(delete(LeasePlacement))
db.execute(delete(BillingPeriod))
db.execute(delete(Tenant))
db.execute(delete(PropertyObject))
db.commit()

# ─── Объекты ──────────────────────────────────────────────────────────────────
print("Создаю объекты...")
obj1 = PropertyObject(
    name="БЦ Восток",
    address="г. Москва, ул. Ленина, 42",
    total_area=Decimal("520.00"),
    note="Бизнес-центр класса B, 4 этажа"
)
obj2 = PropertyObject(
    name="Склад Север",
    address="г. Москва, Промышленный проезд, 7",
    total_area=Decimal("850.00"),
    note="Складской комплекс с офисной частью"
)
db.add_all([obj1, obj2])
db.flush()

# ─── Арендаторы ───────────────────────────────────────────────────────────────
print("Создаю арендаторов...")
t1 = Tenant(tenant_type="ООО", display_name='ООО "Альфа Трейд"',   phone="+7 495 111-22-33", note="Основной арендатор, 3 помещения")
t2 = Tenant(tenant_type="ИП",  display_name="ИП Семёнов Д.В.",     phone="+7 916 444-55-66", note="Малый бизнес, бухгалтерия")
t3 = Tenant(tenant_type="ООО", display_name='ООО "Логистик Плюс"', phone="+7 495 777-88-99", note="Склад + офис")
t4 = Tenant(tenant_type="ИП",  display_name="ИП Карпова М.С.",     phone="+7 926 222-33-44", note="Розничная торговля")
db.add_all([t1, t2, t3, t4])
db.flush()

# ─── Размещения ───────────────────────────────────────────────────────────────
print("Создаю размещения...")
placements = [
    # БЦ Восток
    LeasePlacement(object_id=obj1.id, tenant_id=t1.id, rental_address="Офис 101",
        occupied_area=Decimal("80.00"), start_date=date(2026, 1, 1), end_date=None,
        rent_tariff=Decimal("900.00"), is_active=True, status="active", comment="Долгосрочная аренда"),
    LeasePlacement(object_id=obj1.id, tenant_id=t1.id, rental_address="Офис 205",
        occupied_area=Decimal("45.00"), start_date=date(2026, 1, 1), end_date=None,
        rent_tariff=Decimal("900.00"), is_active=True, status="active", comment="Переговорная комната"),
    LeasePlacement(object_id=obj1.id, tenant_id=t2.id, rental_address="Офис 110",
        occupied_area=Decimal("30.00"), start_date=date(2026, 3, 1), end_date=None,
        rent_tariff=Decimal("850.00"), is_active=True, status="active", comment="Новый договор с марта"),
    LeasePlacement(object_id=obj1.id, tenant_id=t4.id, rental_address="Офис 102",
        occupied_area=Decimal("25.00"), start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
        rent_tariff=Decimal("800.00"), is_active=True, status="active", comment="Договор до июня"),
    # Склад Север
    LeasePlacement(object_id=obj2.id, tenant_id=t3.id, rental_address="Склад А-1",
        occupied_area=Decimal("420.00"), start_date=date(2026, 1, 1), end_date=None,
        rent_tariff=Decimal("350.00"), is_active=True, status="active", comment="Основная складская площадь"),
    LeasePlacement(object_id=obj2.id, tenant_id=t3.id, rental_address="Офис 001",
        occupied_area=Decimal("60.00"), start_date=date(2026, 1, 1), end_date=None,
        rent_tariff=Decimal("700.00"), is_active=True, status="active", comment="Офис при складе"),
]
db.add_all(placements)
db.flush()

# ─── Тарифы ───────────────────────────────────────────────────────────────────
print("Создаю тарифы...")
tariffs = [
    # БЦ Восток
    Tariff(object_id=obj1.id, tenant_id=None, utility_type="heat",        value=Decimal("120.00"), unit_name="руб/м2", start_date=date(2026, 1, 1), is_active=True),
    Tariff(object_id=obj1.id, tenant_id=None, utility_type="electricity",  value=Decimal("55.00"),  unit_name="руб/м2", start_date=date(2026, 1, 1), is_active=True),
    Tariff(object_id=obj1.id, tenant_id=None, utility_type="water",        value=Decimal("18.00"),  unit_name="руб/м2", start_date=date(2026, 1, 1), is_active=True),
    Tariff(object_id=obj1.id, tenant_id=None, utility_type="cleaning",     value=Decimal("25.00"),  unit_name="руб/м2", start_date=date(2026, 1, 1), is_active=True),
    # Склад Север
    Tariff(object_id=obj2.id, tenant_id=None, utility_type="heat",        value=Decimal("80.00"),  unit_name="руб/м2", start_date=date(2026, 1, 1), is_active=True),
    Tariff(object_id=obj2.id, tenant_id=None, utility_type="electricity",  value=Decimal("40.00"),  unit_name="руб/м2", start_date=date(2026, 1, 1), is_active=True),
    Tariff(object_id=obj2.id, tenant_id=None, utility_type="water",        value=Decimal("12.00"),  unit_name="руб/м2", start_date=date(2026, 1, 1), is_active=True),
]
db.add_all(tariffs)
db.flush()

# ─── Правила распределения ────────────────────────────────────────────────────
print("Создаю правила распределения...")
rules = [
    AllocationRule(object_id=obj1.id, utility_type="heat",        mode="area", base_area_mode="active_leases", is_active=True),
    AllocationRule(object_id=obj1.id, utility_type="electricity",  mode="area", base_area_mode="active_leases", is_active=True),
    AllocationRule(object_id=obj1.id, utility_type="water",        mode="area", base_area_mode="active_leases", is_active=True),
    AllocationRule(object_id=obj1.id, utility_type="cleaning",     mode="area", base_area_mode="active_leases", is_active=True),
    AllocationRule(object_id=obj2.id, utility_type="heat",        mode="area", base_area_mode="active_leases", is_active=True),
    AllocationRule(object_id=obj2.id, utility_type="electricity",  mode="area", base_area_mode="active_leases", is_active=True),
    AllocationRule(object_id=obj2.id, utility_type="water",        mode="area", base_area_mode="active_leases", is_active=True),
]
db.add_all(rules)
db.commit()

# ─── Период 1: Апрель 2026 ────────────────────────────────────────────────────
print("Создаю период Апрель 2026...")
period1 = BillingPeriod(period_type="month", month_label="2026-04",
    start_date=date(2026, 4, 1), end_date=date(2026, 4, 30))
db.add(period1)
db.flush()

db.add_all([
    # БЦ Восток — по тарифу
    UtilityCharge(object_id=obj1.id, billing_period_id=period1.id, utility_type="heat",       input_mode="tariff", allocation_mode="area", tariff=Decimal("120.00"), unit_name="руб/м2", comment="Тепло апрель"),
    UtilityCharge(object_id=obj1.id, billing_period_id=period1.id, utility_type="electricity", input_mode="tariff", allocation_mode="area", tariff=Decimal("55.00"),  unit_name="руб/м2", comment="Электричество апрель"),
    UtilityCharge(object_id=obj1.id, billing_period_id=period1.id, utility_type="water",       input_mode="tariff", allocation_mode="area", tariff=Decimal("18.00"),  unit_name="руб/м2", comment="Вода апрель"),
    UtilityCharge(object_id=obj1.id, billing_period_id=period1.id, utility_type="cleaning",    input_mode="tariff", allocation_mode="area", tariff=Decimal("25.00"),  unit_name="руб/м2", comment="Уборка апрель"),
    # Склад Север — общей суммой и по счётчику
    UtilityCharge(object_id=obj2.id, billing_period_id=period1.id, utility_type="heat",       input_mode="amount", allocation_mode="area", amount=Decimal("38400.00"), comment="Тепло апрель"),
    UtilityCharge(object_id=obj2.id, billing_period_id=period1.id, utility_type="electricity", input_mode="meter",  allocation_mode="area", meter_from=Decimal("12540.0"), meter_to=Decimal("13180.0"), tariff=Decimal("6.50"), unit_name="кВтч", comment="Электро по счётчику"),
    UtilityCharge(object_id=obj2.id, billing_period_id=period1.id, utility_type="water",       input_mode="amount", allocation_mode="area", amount=Decimal("5760.00"),  comment="Вода апрель"),
])
db.commit()

# ─── Период 2: Май 2026 ───────────────────────────────────────────────────────
print("Создаю период Май 2026...")
period2 = BillingPeriod(period_type="month", month_label="2026-05",
    start_date=date(2026, 5, 1), end_date=date(2026, 5, 31))
db.add(period2)
db.flush()

db.add_all([
    # БЦ Восток
    UtilityCharge(object_id=obj1.id, billing_period_id=period2.id, utility_type="heat",       input_mode="tariff", allocation_mode="area", tariff=Decimal("120.00"), unit_name="руб/м2", comment="Тепло май"),
    UtilityCharge(object_id=obj1.id, billing_period_id=period2.id, utility_type="electricity", input_mode="tariff", allocation_mode="area", tariff=Decimal("55.00"),  unit_name="руб/м2", comment="Электричество май"),
    UtilityCharge(object_id=obj1.id, billing_period_id=period2.id, utility_type="water",       input_mode="tariff", allocation_mode="area", tariff=Decimal("18.00"),  unit_name="руб/м2", comment="Вода май"),
    UtilityCharge(object_id=obj1.id, billing_period_id=period2.id, utility_type="cleaning",    input_mode="tariff", allocation_mode="area", tariff=Decimal("25.00"),  unit_name="руб/м2", comment="Уборка май"),
    # Склад Север
    UtilityCharge(object_id=obj2.id, billing_period_id=period2.id, utility_type="heat",       input_mode="amount", allocation_mode="area", amount=Decimal("35200.00"), comment="Тепло май"),
    UtilityCharge(object_id=obj2.id, billing_period_id=period2.id, utility_type="electricity", input_mode="meter",  allocation_mode="area", meter_from=Decimal("13180.0"), meter_to=Decimal("13870.0"), tariff=Decimal("6.50"), unit_name="кВтч", comment="Электро по счётчику"),
    UtilityCharge(object_id=obj2.id, billing_period_id=period2.id, utility_type="water",       input_mode="amount", allocation_mode="area", amount=Decimal("5400.00"),  comment="Вода май"),
])
db.commit()

# ─── Расчёт ───────────────────────────────────────────────────────────────────
for label, period in [("Апрель", period1), ("Май", period2)]:
    print(f"Рассчитываю {label}...")
    try:
        recalculate_period(db, period.id)
        print(f"  OK {label} рассчитан")
    except ValueError as e:
        print(f"  WARN {label}: {e}")

# ─── Итог ─────────────────────────────────────────────────────────────────────
print(f"""
=== База заполнена! ===
  Объектов:    {db.scalar(select(func.count(PropertyObject.id)))}
  Арендаторов: {db.scalar(select(func.count(Tenant.id)))}
  Размещений:  {db.scalar(select(func.count(LeasePlacement.id)))}
  Тарифов:     {db.scalar(select(func.count(Tariff.id)))}
  Правил:      {db.scalar(select(func.count(AllocationRule.id)))}
  Периодов:    {db.scalar(select(func.count(BillingPeriod.id)))}
  Начислений:  {db.scalar(select(func.count(ChargeAllocation.id)))}
""")
db.close()
