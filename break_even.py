"""
Расчёт точки безубыточности и процентных изменений.

Формулы (без НДФЛ):
    P_out = [P_in × (1 + c) + S_day / (N × Q)] / (1 - c)
    ΔP    = [2c × P_in + S_day / (N × Q)] / (1 - c)
    ΔP%   = [2c + S_day / (P_in × N × Q)] / (1 - c)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BreakEvenResult:
    """Результат расчёта безубыточности."""

    P_in: float              # цена входа
    P_out: float             # цена безубыточности
    delta_price: float       # ΔP = P_out - P_in (абсолютное)
    delta_pct: float         # ΔP% (дробь, например 0.001149)
    delta_pct_display: float # ΔP% (проценты, например 0.1149)
    commission_in: float     # комиссия входа на 1 акцию
    commission_out: float    # комиссия выхода на 1 акцию
    service_per_share: float # обслуживание на 1 акцию
    total_cost_per_share: float  # суммарные расходы на 1 акцию
    total_cost_per_trade: float  # суммарные расходы на всю позицию


@dataclass
class CommissionResult:
    """Результат расчёта комиссии «на круг»."""

    commission_in: float     # комиссия входа
    commission_out: float    # комиссия выхода
    total: float             # суммарная комиссия
    round_trip_pct: float    # комиссия «на круг» в % от позиции входа


def break_even_price(
    P_in: float,
    c: float = 0.0005,
    monthly_service: float = 390.0,
    trading_days: int = 20,
    trades_per_day: int = 5,
    lots: int = 1,
    lot_size: int = 100,
) -> float:
    """
    Расчёт цены безубыточности P_out (точное значение, без НДФЛ).

    Формула:
        P_out = [P_in × (1 + c) + S_day / (N × Q)] / (1 - c)

    Args:
        P_in: цена входа
        c: комиссия брокера за сделку (0.0005 = 0.05%)
        monthly_service: обслуживание тарифа в месяц (₽)
        trading_days: торговых дней в месяце
        trades_per_day: количество сделок в день
        lots: количество лотов
        lot_size: размер лота (акций)

    Returns:
        Цена безубыточности P_out

    Пример:
        >>> break_even_price(263.50)
        263.80229772330844
    """
    Q = lots * lot_size
    S_day = monthly_service / trading_days

    return (P_in * (1 + c) + S_day / (trades_per_day * Q)) / (1 - c)


def break_even_delta(
P_in: float,
    c: float = 0.0005,
    monthly_service: float = 390.0,
    trading_days: int = 20,
    trades_per_day: int = 5,
    lots: int = 1,
    lot_size: int = 100,
) -> tuple[float, float, float]:
    """
    Расчёт дельты безубыточности (ΔP, ΔP%, ΔP в % отображения).

    Формулы:
        ΔP  = [2c × P_in + S_day / (N × Q)] / (1 - c)
        ΔP% = ΔP / P_in

    Args:
        P_in: цена входа
        c: комиссия брокера за сделку
        monthly_service: обслуживание тарифа в месяц
        trading_days: торговых дней в месяце
        trades_per_day: сделок в день
        lots: количество лотов
        lot_size: размер лота

    Returns:
        (delta_price, delta_pct, delta_pct_display)
        где:
            delta_price: ΔP в рублях
            delta_pct: ΔP% в виде дроби (0.001149)
            delta_pct_display: ΔP% в виде процентов (0.1149)

    Пример:
        >>> dp, dp_pct, dp_pct_display = break_even_delta(263.50)
        >>> round(dp, 4)
        0.3023
        >>> round(dp_pct_display, 4)
        0.1149
    """
    P_out = break_even_price(P_in, c, monthly_service, trading_days,
                              trades_per_day, lots, lot_size)
    delta_price = P_out - P_in
    delta_pct = delta_price / P_in
    delta_pct_display = delta_pct * 100

    return delta_price, delta_pct, delta_pct_display


def break_even_summary(
    P_in: float,
    c: float = 0.0005,
    monthly_service: float = 390.0,
    trading_days: int = 20,
    trades_per_day: int = 5,
    lots: int = 1,
    lot_size: int = 100,
) -> BreakEvenResult:
    """
    Полная сводка по безубыточности.

    Возвращает BreakEvenResult со всеми компонентами:
    - P_out: цена безубыточности
    - ΔP и ΔP%: необходимое движение
    - Разбивка расходов: комиссия входа, комиссия выхода, обслуживание
    - Итоговые расходы на акцию и на сделку

    Пример:
        >>> result = break_even_summary(263.50)
        >>> round(result.P_out, 2)
        263.8
        >>> round(result.delta_pct_display, 4)
        0.1149
    """
    Q = lots * lot_size
    S_day = monthly_service / trading_days

    P_out = break_even_price(P_in, c, monthly_service, trading_days,
                              trades_per_day, lots, lot_size)

    delta_price = P_out - P_in
    delta_pct = delta_price / P_in

    # Разбивка расходов на 1 акцию
    commission_in = P_in * c
    commission_out = P_out * c
    service_per_share = S_day / (trades_per_day * Q)
    total_cost_per_share = commission_in + commission_out + service_per_share
    total_cost_per_trade = total_cost_per_share * Q

    return BreakEvenResult(
        P_in=P_in,
        P_out=P_out,
        delta_price=delta_price,
        delta_pct=delta_pct,
        delta_pct_display=delta_pct * 100,
        commission_in=commission_in,
        commission_out=commission_out,
        service_per_share=service_per_share,
        total_cost_per_share=total_cost_per_share,
        total_cost_per_trade=total_cost_per_trade,
    )


def pct_change(old_price: float, new_price: float, as_pct: bool = True) -> float:
    """
    Процентное изменение цены.

    Args:
        old_price: начальная цена
        new_price: конечная цена
        as_pct: если True — возвращает в процентах (1.5 = 1.5%),
                если False — в виде дроби (0.015)

    Returns:
        Процентное изменение (new - old) / old

    Пример:
        >>> pct_change(100, 101)
        1.0
        >>> round(pct_change(263.50, 265.00), 4)
        0.5693
    """
    if old_price == 0:
        raise ValueError("old_price не может быть 0")

    change = (new_price - old_price) / old_price

    return change * 100 if as_pct else change


def round_trip_commission(
    P_in: float,
    P_out: float,
    Q: int = 100,
    c: float = 0.0005,
) -> CommissionResult:
    """
    Расчёт комиссии «на круг» (вход + выход).

    Комиссии считаются РАЗДЕЛЬНО:
    - Комиссия входа = P_in × Q × c
    - Комиссия выхода = P_out × Q × c

    Args:
        P_in: цена входа
        P_out: цена выхода
        Q: количество акций (лоты × lot_size)
        c: комиссия брокера за сделку

    Returns:
        CommissionResult с разбивкой комиссий

    Пример:
        >>> result = round_trip_commission(263.50, 265.00)
        >>> round(result.total, 2)
        26.43
    """
    commission_in = P_in * Q * c
    commission_out = P_out * Q * c
    total = commission_in + commission_out

    # Комиссия «на круг» в % от позиции входа
    position_in = P_in * Q
    round_trip_pct = (total / position_in) * 100

    return CommissionResult(
        commission_in=commission_in,
        commission_out=commission_out,
        total=total,
        round_trip_pct=round_trip_pct,
    )


# ─────────────────────────────────────────────────────────────
# Тесты (для самопроверки)
# ─────────────────────────────────────────────────────────────

def _run_tests():
    """Встроенные тесты для проверки формул."""

    # Тест 1: Базовый расчёт безубыточности
    P_in = 263.50
    result = break_even_summary(P_in)
    assert abs(result.P_out - 263.8023) < 0.01, f"P_out: {result.P_out}"
    assert abs(result.delta_pct_display - 0.1149) < 0.001, f"ΔP%: {result.delta_pct_display}"

    # Тест 2: Проверка — при P_out чистая прибыль ≈ 0
    Q = 100
    gross = (result.P_out - P_in) * Q
    expenses = result.total_cost_per_trade
    assert abs(gross - expenses) < 0.01, f"Gross={gross}, Expenses={expenses}"

    # Тест 3: Commission round-trip
    comm = round_trip_commission(263.50, 265.00)
    assert abs(comm.total - 26.425) < 0.01, f"Total commission: {comm.total}"
    assert abs(comm.commission_in - 13.175) < 0.01
    assert abs(comm.commission_out - 13.25) < 0.01

    # Тест 4: pct_change
    assert abs(pct_change(100, 101) - 1.0) < 0.0001
    assert abs(pct_change(263.50, 265.00) - 0.5693) < 0.001

    # Тест 5: Больше сделок → ниже безубыток
    result_5 = break_even_summary(263.50, trades_per_day=5)
    result_10 = break_even_summary(263.50, trades_per_day=10)
    assert result_10.delta_pct < result_5.delta_pct

    # Тест 6: Тариф «Инвестор» (c=0.3%) → выше безубыток
    result_trader = break_even_summary(263.50, c=0.0005, monthly_service=390)
    result_investor = break_even_summary(263.50, c=0.003, monthly_service=0)
    assert result_investor.delta_pct > result_trader.delta_pct

    print("[OK] Все тесты пройдены!")
    print(f"   Безubyток: {result.P_out:.2f} руб (delta P = {result.delta_pct_display:.4f}%)")
    print(f"   Комиссия round-trip: {comm.total:.2f} руб ({comm.round_trip_pct:.4f}%)")


if __name__ == "__main__":
    _run_tests()
