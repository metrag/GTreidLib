"""
Технические индикаторы для анализа рынка.

Функции:
    - sma: простое скользящее среднее
    - ema: экспоненциальное скользящее среднее
    - rsi: индекс относительной силы
    - vwap: объёмно-взвешенная средняя цена
    - crossover: проверка пересечения двух линий
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence


# ─────────────────────────────────────────────────────────────
# SMA — простое скользящее среднее
# ─────────────────────────────────────────────────────────────

def sma(values: Sequence[float], period: int) -> List[float]:
    """
    Простое скользящее среднее (Simple Moving Average).

    SMA[i] = mean(values[i-period+1 : i+1])

    Args:
        values: список значений (цены закрытия, объёмы и т.д.)
        period: период усреднения

    Returns:
        Список значений SMA (длиной len(values), первые period-1 = None)

    Пример:
        >>> sma([1, 2, 3, 4, 5], period=3)
        [None, None, 2.0, 3.0, 4.0]
    """
    if period <= 0:
        raise ValueError("period должен быть > 0")
    if period > len(values):
        return [None] * len(values)

    result = [None] * (period - 1)
    window_sum = sum(values[:period])
    result.append(window_sum / period)

    for i in range(period, len(values)):
        window_sum += values[i] - values[i - period]
        result.append(window_sum / period)

    return result


# ─────────────────────────────────────────────────────────────
# EMA — экспоненциальное скользящее среднее
# ─────────────────────────────────────────────────────────────

def ema(values: Sequence[float], period: int) -> List[float]:
    """
    Экспоненциальное скользящее среднее (Exponential Moving Average).

    EMA[i] = (values[i] - EMA[i-1]) * k + EMA[i-1]
    где k = 2 / (period + 1)

    Первые period-1 значений = None, EMA[period-1] = SMA[period-1].

    Args:
        values: список значений
        period: период EMA

    Returns:
        Список значений EMA

    Пример:
        >>> result = ema([1, 2, 3, 4, 5], period=3)
        >>> round(result[2], 4)
        2.0
        >>> round(result[4], 4)
        4.0
    """
    if period <= 0:
        raise ValueError("period должен быть > 0")
    if period > len(values):
        return [None] * len(values)

    result = [None] * (period - 1)
    # Начальное значение = SMA
    initial = sum(values[:period]) / period
    result.append(initial)

    k = 2.0 / (period + 1)
    for i in range(period, len(values)):
        ema_val = (values[i] - result[-1]) * k + result[-1]
        result.append(ema_val)

    return result


# ─────────────────────────────────────────────────────────────
# RSI — индекс относительной силы
# ─────────────────────────────────────────────────────────────

def rsi(values: Sequence[float], period: int = 14) -> List[float]:
    """
    Индекс относительной силы (Relative Strength Index).

    RSI = 100 - 100 / (1 + RS)
    RS = avg_gain / avg_loss за N периодов

    Значения RSI в диапазоне [0, 100]:
    - RSI > 70: перекупленность (возможна коррекция вниз)
    - RSI < 30: перепроданность (возможен отскок вверх)

    Args:
        values: список цен (обычно close)
        period: период RSI (стандартно 14)

    Returns:
        Список значений RSI (первые period = None)

    Пример:
        >>> prices = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64]
        >>> result = rsi(prices, period=14)
        >>> round(result[-1], 2)
        57.87
    """
    if period <= 0:
        raise ValueError("period должен быть > 0")
    if len(values) < period + 1:
        return [None] * len(values)

    # Считаем изменения цен
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]

    result = [None] * period  # Первые period значений = None

    # Первое значение RSI: среднее арифметическое
    gains = [c if c > 0 else 0 for c in changes[:period]]
    losses = [-c if c < 0 else 0 for c in changes[:period]]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100.0 - 100.0 / (1.0 + rs))

    # Последующие значения: экспоненциальное сглаживание
    for i in range(period, len(changes)):
        gain = changes[i] if changes[i] > 0 else 0
        loss = -changes[i] if changes[i] < 0 else 0

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100.0 - 100.0 / (1.0 + rs))

    return result


# ─────────────────────────────────────────────────────────────
# VWAP — объёмно-взвешенная средняя цена
# ─────────────────────────────────────────────────────────────

def typical_price(high: float, low: float, close: float) -> float:
    """
    Типичная цена = (high + low + close) / 3.
    """
    return (high + low + close) / 3.0


def vwap(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
) -> List[float]:
    """
    Объёмно-взвешенная средняя цена (Volume-Weighted Average Price).

    VWAP = cumsum(TP * Volume) / cumsum(Volume)
    где TP = (high + low + close) / 3

    Используется как "справедливая цена" дня. Цена выше VWAP — быки сильнее,
    ниже VWAP — медведи сильнее.

    Args:
        highs: список максимумов
        lows: список минимумов
        closes: список закрытий
        volumes: список объёмов

    Returns:
        Список значений VWAP

    Пример:
        >>> h = [10, 11]
        >>> l = [9, 10]
        >>> c = [10, 11]
        >>> v = [100, 200]
        >>> result = vwap(h, l, c, v)
        >>> round(result[0], 2)
        10.0
        >>> round(result[1], 2)
        10.67
    """
    if not (len(highs) == len(lows) == len(closes) == len(volumes)):
        raise ValueError("Все массивы должны быть одинаковой длины")

    result = []
    cum_tp_vol = 0.0
    cum_vol = 0.0

    for i in range(len(highs)):
        tp = typical_price(highs[i], lows[i], closes[i])
        cum_tp_vol += tp * volumes[i]
        cum_vol += volumes[i]

        if cum_vol == 0:
            result.append(None)
        else:
            result.append(cum_tp_vol / cum_vol)

    return result


# ─────────────────────────────────────────────────────────────
# Пересечения
# ─────────────────────────────────────────────────────────────

def crossover(
    fast: Sequence[float],
    slow: Sequence[float],
) -> List[Optional[str]]:
    """
    Проверка пересечения двух линий.

    Возвращает:
    - "golden" если fast пересёк slow снизу вверх (бычий сигнал)
    - "death" если fast пересёк slow сверху вниз (медвежий сигнал)
    - None в остальных случаях

    Args:
        fast: быстрая линия (например, EMA 9)
        slow: медленная линия (например, EMA 21)

    Returns:
        Список сигналов (длиной len(fast), первые 2 = None)

    Пример:
        >>> fast = [1, 2, 3, 4, 5]
        >>> slow = [3, 3, 3, 3, 3]
        >>> crossover(fast, slow)
        [None, None, None, 'golden', None]
    """
    if len(fast) != len(slow):
        raise ValueError("fast и slow должны быть одинаковой длины")

    result = [None, None]  # Первые 2 значения = None (нужно 2 точки для пересечения)

    for i in range(2, len(fast)):
        if fast[i - 1] is None or fast[i] is None or slow[i - 1] is None or slow[i] is None:
            result.append(None)
            continue

        prev_diff = fast[i - 1] - slow[i - 1]
        curr_diff = fast[i] - slow[i]

        # Пересечение снизу вверх (golden cross)
        if prev_diff <= 0 and curr_diff > 0:
            result.append("golden")
        # Пересечение сверху вниз (death cross)
        elif prev_diff >= 0 and curr_diff < 0:
            result.append("death")
        else:
            result.append(None)

    return result


# ─────────────────────────────────────────────────────────────
# Тесты
# ─────────────────────────────────────────────────────────────

def _run_tests():
    """Встроенные тесты для проверки формул."""

    # Тест 1: SMA
    s = sma([1, 2, 3, 4, 5], period=3)
    assert s[0] is None and s[1] is None
    assert abs(s[2] - 2.0) < 1e-9
    assert abs(s[3] - 3.0) < 1e-9
    assert abs(s[4] - 4.0) < 1e-9
    print("[OK] SMA: [None, None, 2.0, 3.0, 4.0]")

    # Тест 2: EMA
    e = ema([1, 2, 3, 4, 5], period=3)
    assert e[0] is None and e[1] is None
    assert abs(e[2] - 2.0) < 1e-9  # начальное = SMA
    # k = 2/4 = 0.5
    # e[3] = (4 - 2) * 0.5 + 2 = 3.0
    # e[4] = (5 - 3) * 0.5 + 3 = 4.0
    assert abs(e[3] - 3.0) < 1e-9
    assert abs(e[4] - 4.0) < 1e-9
    print("[OK] EMA: [None, None, 2.0, 3.0, 4.0]")

    # Тест 3: RSI
    # Восходящий тренд — RSI должен быть высоким
    uptrend = list(range(1, 20))  # 1, 2, 3, ..., 19
    r = rsi(uptrend, period=14)
    assert r[-1] is not None
    assert r[-1] == 100.0, f"В чистом аптренде RSI = 100, got {r[-1]}"
    print(f"[OK] RSI uptrend: {r[-1]:.2f} (all gains)")

    # Нисходящий тренд
    downtrend = list(range(20, 1, -1))  # 20, 19, ..., 2
    r2 = rsi(downtrend, period=14)
    assert r2[-1] == 0.0, f"В чистом даунтренде RSI = 0, got {r2[-1]}"
    print(f"[OK] RSI downtrend: {r2[-1]:.2f} (all losses)")

    # Тест 4: VWAP
    h = [10, 11, 12]
    l = [9, 10, 11]
    c = [10, 11, 12]
    v = [100, 200, 300]
    vw = vwap(h, l, c, v)
    # TP[0] = (10+9+10)/3 = 9.666...
    # VWAP[0] = 9.666 * 100 / 100 = 9.666
    assert abs(vw[0] - 9.6667) < 0.01
    # VWAP[2] = (TP0*V0 + TP1*V1 + TP2*V2) / (V0+V1+V2)
    # = (9.667*100 + 10.667*200 + 11.667*300) / 600
    # = (966.7 + 2133.3 + 3500) / 600 = 6600 / 600 = 11.0
    assert abs(vw[2] - 11.0) < 0.01
    print(f"[OK] VWAP: {[round(x, 4) for x in vw]}")

    # Тест 5: Crossover
    fast = [1, 2, 3, 4, 5]
    slow = [3, 3, 3, 3, 3]
    cx = crossover(fast, slow)
    # i=2: prev=-1, curr=0 -> нет (curr=0 не > 0)
    # i=3: prev=0, curr=1 -> golden
    # i=4: prev=1, curr=2 -> нет
    assert cx[0] is None and cx[1] is None
    assert cx[3] == "golden"
    print(f"[OK] Crossover: {cx}")

    # Тест 6: Death cross
    fast2 = [5, 4, 3, 2, 1]
    slow2 = [3, 3, 3, 3, 3]
    cx2 = crossover(fast2, slow2)
    # i=2: prev=1, curr=0 -> нет
    # i=3: prev=0, curr=-1 -> death
    assert cx2[3] == "death"
    print(f"[OK] Death cross: {cx2}")

    # Тест 7: Реалистичный EMA 9/21
    prices = [100 + i * 0.1 for i in range(50)]  # аптренд
    ema9 = ema(prices, 9)
    ema21 = ema(prices, 21)
    # В аптренде EMA9 > EMA21 (быстрая выше медленной)
    assert ema9[-1] > ema21[-1]
    print(f"[OK] EMA9 > EMA21 in uptrend: {ema9[-1]:.2f} > {ema21[-1]:.2f}")

    print("\n[OK] Все тесты indicators пройдены!")


if __name__ == "__main__":
    _run_tests()
