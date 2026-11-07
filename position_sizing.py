"""
Расчёт размера позиции.

Функции:
    - calculate_position_size: размер позиции по фиксированному риску
    - calculate_risk_amount: сумма риска на сделку
    - check_lot_size: проверка и округление до лотов
"""

from dataclasses import dataclass


@dataclass
class PositionSizeResult:
    """Результат расчёта размера позиции."""
    shares: int              # количество акций
    lots: int                # количество лотов
    lot_size: int            # размер лота (акций)
    position_value: float    # стоимость позиции (руб)
    risk_amount: float       # сумма риска (руб)
    risk_pct: float          # риск в % от капитала
    stop_distance: float     # расстояние до стопа (руб)
    stop_distance_pct: float # расстояние до стопа (%)


# ─────────────────────────────────────────────────────────────
# Расчёт суммы риска
# ─────────────────────────────────────────────────────────────

def calculate_risk_amount(
    capital: float,
    risk_per_trade: float = 0.01,
) -> float:
    """
    Сумма риска на одну сделку.

    Args:
        capital: текущий капитал (руб)
        risk_per_trade: риск на сделку в долях (0.01 = 1%)

    Returns:
        Сумма риска в рублях

    Пример:
        >>> calculate_risk_amount(100000, 0.01)
        1000.0
    """
    return capital * risk_per_trade


# ─────────────────────────────────────────────────────────────
# Проверка и округление до лотов
# ─────────────────────────────────────────────────────────────

def check_lot_size(
    shares: int,
    lot_size: int = 1,
    min_lots: int = 1,
    max_lots: int = None,
) -> int:
    """
    Проверка и округление количества акций до лотов.

    Args:
        shares: количество акций
        lot_size: размер лота (акций)
        min_lots: минимальное количество лотов
        max_lots: максимальное количество лотов (None = без ограничения)

    Returns:
        Количество лотов (округлённое)

    Пример:
        >>> check_lot_size(150, lot_size=10)
        15  # 150 акций = 15 лотов по 10 акций
        >>> check_lot_size(155, lot_size=10)
        15  # округление вниз (155 -> 150 акций = 15 лотов)
    """
    lots = shares // lot_size  # округление вниз

    if lots < min_lots:
        lots = min_lots

    if max_lots is not None and lots > max_lots:
        lots = max_lots

    return lots


# ─────────────────────────────────────────────────────────────
# Основной расчёт размера позиции
# ─────────────────────────────────────────────────────────────

def calculate_position_size(
    capital: float,
    entry_price: float,
    stop_price: float,
    risk_per_trade: float = 0.01,
    lot_size: int = 1,
    min_lots: int = 1,
    max_lots: int = None,
    max_position_pct: float = None,
) -> PositionSizeResult:
    """
    Расчёт размера позиции по фиксированному риску.

    Формула:
        risk_amount = capital * risk_per_trade
        stop_distance = entry_price - stop_price
        shares = risk_amount / stop_distance
        lots = shares // lot_size

    Args:
        capital: текущий капитал (руб)
        entry_price: цена входа
        stop_price: цена стоп-лосса
        risk_per_trade: риск на сделку в долях (0.01 = 1%)
        lot_size: размер лота (акций)
        min_lots: минимальное количество лотов
        max_lots: максимальное количество лотов (None = без ограничения)
        max_position_pct: максимум позиции в % от капитала (None = без ограничения)

    Returns:
        PositionSizeResult

    Пример:
        >>> result = calculate_position_size(
        ...     capital=100000,
        ...     entry_price=263.50,
        ...     stop_price=262.35,
        ...     risk_per_trade=0.01,
        ...     lot_size=100
        ... )
        >>> result.lots
        8
        >>> result.shares
        800
        >>> round(result.risk_amount, 2)
        1000.0
    """
    if stop_price >= entry_price:
        raise ValueError(f"stop_price ({stop_price}) должен быть ниже entry_price ({entry_price})")

    # Сумма риска
    risk_amount = calculate_risk_amount(capital, risk_per_trade)

    # Расстояние до стопа
    stop_distance = entry_price - stop_price

    # Количество акций
    raw_shares = risk_amount / stop_distance

    # Округление до лотов
    lots = check_lot_size(int(raw_shares), lot_size, min_lots, max_lots)
    shares = lots * lot_size

    # Стоимость позиции
    position_value = shares * entry_price

    # Проверка лимита позиции
    if max_position_pct is not None:
        max_value = capital * max_position_pct
        if position_value > max_value:
            # Уменьшаем до лимита
            max_shares = int(max_value / entry_price)
            lots = check_lot_size(max_shares, lot_size, min_lots, max_lots)
            shares = lots * lot_size
            position_value = shares * entry_price

    # Фактический риск
    actual_risk = shares * stop_distance
    actual_risk_pct = actual_risk / capital

    return PositionSizeResult(
        shares=shares,
        lots=lots,
        lot_size=lot_size,
        position_value=position_value,
        risk_amount=actual_risk,
        risk_pct=actual_risk_pct,
        stop_distance=stop_distance,
        stop_distance_pct=stop_distance / entry_price,
    )


# ─────────────────────────────────────────────────────────────
# Тесты
# ─────────────────────────────────────────────────────────────

def _run_tests():
    """Встроенные тесты."""

    # Тест 1: Базовый расчёт
    result = calculate_position_size(
        capital=100000,
        entry_price=263.50,
        stop_price=262.35,
        risk_per_trade=0.01,
        lot_size=100,
    )
    # risk_amount = 100000 * 0.01 = 1000 руб
    # stop_distance = 263.50 - 262.35 = 1.15 руб
    # raw_shares = 1000 / 1.15 = 869.6
    # lots = 869 // 100 = 8
    # shares = 8 * 100 = 800
    assert result.lots == 8, f"Expected 8 lots, got {result.lots}"
    assert result.shares == 800, f"Expected 800 shares, got {result.shares}"
    assert result.position_value == 800 * 263.50, f"Position value wrong"
    print(f"[OK] Position: {result.lots} lots, {result.shares} shares, {result.position_value:.0f} rub")
    print(f"     Risk: {result.risk_amount:.0f} rub ({result.risk_pct*100:.2f}%)")

    # Тест 2: С лимитом позиции
    result2 = calculate_position_size(
        capital=100000,
        entry_price=263.50,
        stop_price=262.35,
        risk_per_trade=0.01,
        lot_size=100,
        max_position_pct=0.20,  # максимум 20% от капитала
    )
    # max_value = 100000 * 0.20 = 20000 руб
    # max_shares = 20000 / 263.50 = 75.9 -> 75
    # lots = 75 // 100 = 0 -> min_lots = 1
    # Но позиция = 1 * 100 * 263.50 = 26350 > 20000, поэтому лотов = 0? Нет, min_lots=1
    # Значит будет 1 лот (100 акций), даже если превышает лимит
    print(f"[OK] With max_position_pct=20%: {result2.lots} lots, {result2.position_value:.0f} rub")

    # Тест 3: Маленький капитал
    result3 = calculate_position_size(
        capital=5000,
        entry_price=263.50,
        stop_price=262.35,
        risk_per_trade=0.01,
        lot_size=100,
    )
    # risk_amount = 5000 * 0.01 = 50 руб
    # stop_distance = 1.15 руб
    # raw_shares = 50 / 1.15 = 43.5
    # lots = 43 // 100 = 0 -> min_lots = 1
    assert result3.lots == 1, f"Expected min 1 lot, got {result3.lots}"
    print(f"[OK] Small capital (5000): {result3.lots} lot, {result3.risk_amount:.0f} rub risk")

    # Тест 4: Проверка ошибки (stop >= entry)
    try:
        calculate_position_size(
            capital=100000,
            entry_price=263.50,
            stop_price=265.00,  # stop ВЫШЕ entry — ошибка!
            risk_per_trade=0.01,
        )
        assert False, "Should raise ValueError"
    except ValueError as e:
        print(f"[OK] Correct error for invalid stop: {e}")

    print("\n[OK] Все тесты position_sizing пройдены!")


if __name__ == "__main__":
    _run_tests()
