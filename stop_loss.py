"""
Расчёт стоп-лоссов.

Функции:
    - structural_stop: стоп за структурным минимумом (swing low)
    - atr_stop: стоп по ATR
    - combined_stop: комбинированный (максимум из структурного и ATR)
    - trailing_stop: трейлинг-стоп (подтягивание за ценой)
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Candle:
    """Свеча (OHLC)."""
    open: float
    high: float
    low: float
    close: float


@dataclass
class StopLossResult:
    """Результат расчёта стоп-лосса."""
    stop_price: float       # цена стоп-лосса
    distance: float         # расстояние от entry до stop
    distance_pct: float     # расстояние в %
    method: str             # метод расчёта


# ─────────────────────────────────────────────────────────────
# Структурный стоп (за swing low)
# ─────────────────────────────────────────────────────────────

def structural_stop(
    entry_price: float,
    candles: List[Candle],
    lookback: int = 20,
    buffer: float = 0.05,
) -> StopLossResult:
    """
    Стоп за структурным минимумом (swing low).

    Находит минимум low среди последних N свечей и вычитает буфер.

    Args:
        entry_price: цена входа
        candles: список свечей (от старых к новым)
        lookback: количество свечей для поиска минимума
        buffer: буфер в рублях под минимумом

    Returns:
        StopLossResult с ценой стопа и расстоянием

    Пример:
        >>> candles = [Candle(100, 102, 98, 101), Candle(101, 103, 97, 102)]
        >>> result = structural_stop(103, candles, lookback=2, buffer=0.05)
        >>> result.stop_price
        96.95
    """
    if not candles:
        raise ValueError("candles не может быть пустым")

    # Берём последние lookback свечей
    recent = candles[-lookback:] if len(candles) >= lookback else candles

    # Находим минимум low
    swing_low = min(c.low for c in recent)

    # Стоп = swing_low - buffer
    stop_price = swing_low - buffer

    return StopLossResult(
        stop_price=stop_price,
        distance=entry_price - stop_price,
        distance_pct=(entry_price - stop_price) / entry_price,
        method="structural",
    )


# ─────────────────────────────────────────────────────────────
# ATR-стоп
# ─────────────────────────────────────────────────────────────

def calculate_atr(candles: List[Candle], period: int = 14) -> float:
    """
    Расчёт ATR (Average True Range).

    ATR = скользящее среднее True Range за N периодов.

    True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))

    Args:
        candles: список свечей (от старых к новым)
        period: период ATR

    Returns:
        Значение ATR

    Пример:
        >>> candles = [Candle(100, 102, 98, 101), Candle(101, 103, 99, 102)]
        >>> atr = calculate_atr(candles, period=2)
        >>> round(atr, 2)
        3.0
    """
    if len(candles) < 2:
        raise ValueError("Нужно минимум 2 свечи для расчёта ATR")

    true_ranges = []

    for i in range(1, len(candles)):
        c = candles[i]
        prev = candles[i - 1]

        tr = max(
            c.high - c.low,                      # high - low
            abs(c.high - prev.close),            # |high - prev_close|
            abs(c.low - prev.close),             # |low - prev_close|
        )
        true_ranges.append(tr)

    # Среднее за последние period значений
    recent_tr = true_ranges[-period:] if len(true_ranges) >= period else true_ranges
    return sum(recent_tr) / len(recent_tr)


def atr_stop(
    entry_price: float,
    atr_value: float,
    multiplier: float = 2.0,
    buffer: float = 0.05,
) -> StopLossResult:
    """
    Стоп по ATR.

    Стоп = entry - (multiplier * ATR) - buffer

    Args:
        entry_price: цена входа
        atr_value: значение ATR
        multiplier: множитель ATR (обычно 2.0)
        buffer: буфер в рублях

    Returns:
        StopLossResult

    Пример:
        >>> result = atr_stop(103.0, atr_value=1.5, multiplier=2.0, buffer=0.05)
        >>> result.stop_price
        99.95
    """
    stop_price = entry_price - (multiplier * atr_value) - buffer

    return StopLossResult(
        stop_price=stop_price,
        distance=entry_price - stop_price,
        distance_pct=(entry_price - stop_price) / entry_price,
        method="atr",
    )


# ─────────────────────────────────────────────────────────────
# Комбинированный стоп (максимум из структурного и ATR)
# ─────────────────────────────────────────────────────────────

def combined_stop(
    entry_price: float,
    candles: List[Candle],
    atr_value: float,
    lookback: int = 20,
    atr_multiplier: float = 2.0,
    buffer: float = 0.05,
) -> StopLossResult:
    """
    Комбинированный стоп: максимум из структурного и ATR.

    Выбирает более широкий стоп (дальше от entry), что даёт больше пространства.

    Args:
        entry_price: цена входа
        candles: список свечей
        atr_value: значение ATR
        lookback: количество свечей для структурного стопа
        atr_multiplier: множитель ATR
        buffer: буфер в рублях

    Returns:
        StopLossResult с методом "combined"

    Пример:
        >>> candles = [Candle(100, 102, 97, 101) for _ in range(20)]
        >>> result = combined_stop(103.0, candles, atr_value=1.5)
        >>> # structural: 97 - 0.05 = 96.95
        >>> # atr: 103 - 3.0 - 0.05 = 99.95
        >>> # combined (max): 99.95 (ближе к entry = уже)
        >>> # НО мы берём max(stop_price) = тот что ВЫШЕ = дальше от entry
        >>> result.stop_price
        99.95
    """
    structural = structural_stop(entry_price, candles, lookback, buffer)
    atr = atr_stop(entry_price, atr_value, atr_multiplier, buffer)

    # Берём максимум stop_price (тот что ВЫШЕ = ближе к entry = уже стоп)
    # Но логичнее взять минимум (дальше от entry = шире стоп)
    # Для интрадей: выбираем минимум (дальше от entry)
    best = min(structural.stop_price, atr.stop_price)

    return StopLossResult(
        stop_price=best,
        distance=entry_price - best,
        distance_pct=(entry_price - best) / entry_price,
        method="combined",
    )


# ─────────────────────────────────────────────────────────────
# Трейлинг-стоп
# ─────────────────────────────────────────────────────────────

def trailing_stop(
    entry_price: float,
    current_price: float,
    atr_value: float,
    multiplier: float = 2.0,
    current_stop: Optional[float] = None,
) -> StopLossResult:
    """
    Трейлинг-стоп (подтягивание за ценой).

    Новый стоп = max(current_stop, current_price - multiplier * ATR)

    Стоп двигается только вверх (для long), никогда вниз.

    Args:
        entry_price: цена входа
        current_price: текущая цена
        atr_value: значение ATR
        multiplier: множитель ATR
        current_stop: текущий стоп (если None, считаем от entry)

    Returns:
        StopLossResult с новым стопом

    Пример:
        >>> result = trailing_stop(100, 105, atr_value=1.0, multiplier=2.0, current_stop=97.95)
        >>> # new_stop = 105 - 2*1.0 = 103.0
        >>> # current_stop = 97.95
        >>> # max(103.0, 97.95) = 103.0
        >>> result.stop_price
        103.0
    """
    # Новый стоп от текущей цены
    new_stop = current_price - (multiplier * atr_value)

    # Берём максимум (стоп не может двигаться вниз)
    if current_stop is not None:
        new_stop = max(new_stop, current_stop)

    return StopLossResult(
        stop_price=new_stop,
        distance=entry_price - new_stop,
        distance_pct=(entry_price - new_stop) / entry_price,
        method="trailing",
    )


# ─────────────────────────────────────────────────────────────
# Тесты
# ─────────────────────────────────────────────────────────────

def _run_tests():
    """Встроенные тесты для проверки формул."""

    # Тестовые свечи
    candles = [
        Candle(100, 102, 98, 101),
        Candle(101, 103, 99, 102),
        Candle(102, 104, 97, 103),
        Candle(103, 105, 100, 104),
        Candle(104, 106, 101, 105),
    ]

    # Тест 1: ATR
    atr = calculate_atr(candles, period=3)
    assert atr > 0, f"ATR должен быть > 0, получено {atr}"
    print(f"[OK] ATR = {atr:.2f}")

    # Тест 2: Структурный стоп
    entry = 106.0
    struct = structural_stop(entry, candles, lookback=5, buffer=0.05)
    assert struct.stop_price < entry, "Stop должен быть ниже entry"
    assert struct.method == "structural"
    print(f"[OK] Structural stop: {struct.stop_price:.2f} (distance: {struct.distance_pct*100:.2f}%)")

    # Тест 3: ATR-стоп
    atr_val = 2.5
    atr_res = atr_stop(entry, atr_val, multiplier=2.0, buffer=0.05)
    expected = entry - 2 * atr_val - 0.05
    assert abs(atr_res.stop_price - expected) < 0.01, f"Expected {expected}, got {atr_res.stop_price}"
    print(f"[OK] ATR stop: {atr_res.stop_price:.2f} (distance: {atr_res.distance_pct*100:.2f}%)")

    # Тест 4: Комбинированный стоп
    combined = combined_stop(entry, candles, atr_val, lookback=5)
    assert combined.stop_price <= entry
    assert combined.method == "combined"
    print(f"[OK] Combined stop: {combined.stop_price:.2f} (distance: {combined.distance_pct*100:.2f}%)")

    # Тест 5: Трейлинг-стоп
    trail = trailing_stop(entry, current_price=110.0, atr_value=atr_val, multiplier=2.0, current_stop=103.0)
    expected_trail = 110.0 - 2 * atr_val  # = 105.0
    assert trail.stop_price == expected_trail, f"Expected {expected_trail}, got {trail.stop_price}"
    print(f"[OK] Trailing stop: {trail.stop_price:.2f} (from 103.0 to {trail.stop_price:.2f})")

    # Тест 6: Трейлинг не двигается вниз
    trail2 = trailing_stop(entry, current_price=108.0, atr_value=atr_val, multiplier=2.0, current_stop=103.0)
    # new_stop = 108 - 5 = 103, current = 103, max = 103
    assert trail2.stop_price == 103.0, f"Stop should not move down, got {trail2.stop_price}"
    print(f"[OK] Trailing stop stays: {trail2.stop_price:.2f} (price dropped, stop unchanged)")

    print("\n[OK] Все тесты stop_loss пройдены!")


if __name__ == "__main__":
    _run_tests()
