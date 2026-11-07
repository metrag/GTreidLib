"""
Сигналы входа, стек фильтров и выходы без ТП (главы 18-20 SYLLABUS).

Каталог сигналов [С]:
    - breakout_retest: пробой + ретест уровня (18.1)
    - pullback_to_ma: откат к EMA/VWAP (18.2)
    - level_reversal: разворот на уровне (18.3)
    - momentum_candle: моментум-свеча с объёмом (18.4)
    - orderbook_imbalance: дисбаланс bid/ask в стакане (18.5)

Стек фильтров [Ф] (сигнал + все 8 = сделка):
    - trend, zone, volume, volatility, spread, session, news, market_open

Выходы без ТП [В] (20.1-20.5):
    - time_stop: не в плюс за N минут -> выход
    - reverse_signal_exit: выход по обратному сигналу
    - eod_flatten: закрыть всё до конца вечерней сессии
    (стоп-лосс и трейлинг уже есть в stop_loss.py)

Профиль: MOEX акции, лонг-only, интрадей.
"""

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Callable, List, Optional, Sequence, Tuple

from .indicators import crossover, ema, sma, vwap
from .datafeed import Candle, OrderBook


# ─────────────────────────────────────────────────────────────
# Структуры данных
# ─────────────────────────────────────────────────────────────

@dataclass
class Signal:
    """Сигнал входа."""
    name: str                     # "breakout_retest" и т.д.
    direction: str                # "long" / "short"
    price: float                  # цена входа
    reason: str                   # человекочитаемая причина
    strength: float = 1.0         # 0..1
    meta: dict = field(default_factory=dict)


@dataclass
class FilterResult:
    """Результат одного фильтра."""
    name: str
    passed: bool
    reason: str


@dataclass
class TradeSetup:
    """Итог: сигнал + стек из 8 фильтров."""
    signal: Signal
    filters: List[FilterResult]
    approved: bool
    rejections: List[str]          # причины отказа (непройденные фильтры)


# ─────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────

def _last(values: Sequence[float]) -> float:
    """Последнее непустое значение (списки индикаторов содержат None)."""
    for v in reversed(values):
        if v is not None:
            return float(v)
    raise ValueError("нет значений индикатора")


def _candles_fields(candles: List[Candle]):
    """Развёртка свечей в отдельные списки полей."""
    return (
        [c.high for c in candles],
        [c.low for c in candles],
        [c.close for c in candles],
        [float(c.volume) for c in candles],
    )


# ─────────────────────────────────────────────────────────────
# Каталог сигналов входа [С] — глава 18
# ─────────────────────────────────────────────────────────────

def breakout_retest(
    candles: List[Candle],
    level: float,
    tolerance_pct: float = 0.15,
    lookback: int = 5,
) -> Optional[Signal]:
    """
    18.1 Пробой + ретест (вход после возврата к пробитому уровню).

    Логика (лонг):
      1. За последние `lookback` свечей был пробой: close > level.
      2. Последняя свеча откатилась к уровню: low <= level * (1 + tolerance_pct/100).
      3. Последняя свеча закрылась выше уровня (close > level) — ретест выдержан.

    Args:
        candles: свечи от старых к новым (минимум lookback + 1)
        level: уровень сопротивления (ценовой уровень)
        tolerance_pct: допуск касания уровня в %
        lookback: окно поиска пробоя

    Returns:
        Signal или None

    Пример:
        >>> cs = [Candle(datetime.now(), 100, 101, 99, 100.5, 1000),
        ...       Candle(datetime.now(), 100.5, 103, 100, 102.5, 1200),
        ...       Candle(datetime.now(), 102.5, 103, 100.1, 101.5, 1100)]
        >>> sig = breakout_retest(cs, level=101.0)
        >>> sig.name
        'breakout_retest'
    """
    if len(candles) < lookback + 1:
        return None

    tol = level * tolerance_pct / 100.0
    window = candles[-lookback:]

    # 1. был пробой в окне (кроме последней свечи)
    broke_out = any(c.close > level for c in window[:-1])
    if not broke_out:
        return None

    last = candles[-1]
    # 2. ретест: low коснулся зоны уровня
    if last.low > level + tol:
        return None
    # 3. ретест выдержан: закрытие выше уровня, бычья свеча
    if last.close <= level or last.close <= last.open:
        return None

    return Signal(
        name="breakout_retest",
        direction="long",
        price=last.close,
        reason=f"пробой уровня {level:.2f} + ретест выдержан "
               f"(close={last.close:.2f} > level)",
        meta={"level": level, "tolerance_pct": tolerance_pct},
    )


def pullback_to_ma(
    candles: List[Candle],
    period: int = 20,
    ma: str = "ema",
    tolerance_pct: float = 0.15,
) -> Optional[Signal]:
    """
    18.2 Pullback к EMA/VWAP (откат к среднему в тренде).

    Логика (лонг):
      1. Цена выше MA (тренд вверх).
      2. Последняя свеча коснулась MA: low <= MA * (1 + tolerance_pct/100).
      3. Последняя свеча закрылась выше MA и бычья.

    Args:
        candles: свечи от старых к новым (минимум period + 1)
        period: период EMA/SMA
        ma: "ema" | "sma" | "vwap"
        tolerance_pct: допуск касания MA в %

    Returns:
        Signal или None
    """
    if len(candles) < period + 1:
        return None

    highs, lows, closes, vols = _candles_fields(candles)

    if ma == "ema":
        values = ema(closes, period)
    elif ma == "sma":
        values = sma(closes, period)
    elif ma == "vwap":
        values = vwap(highs, lows, closes, vols)
    else:
        raise ValueError("ma должен быть 'ema', 'sma' или 'vwap'")

    ma_now = _last(values)
    ma_prev = _last(values[:-1]) if len(values) > 1 else ma_now
    last = candles[-1]

    tol = ma_now * tolerance_pct / 100.0

    # 1. цена выше MA и MA растёт
    if last.close <= ma_now or ma_now <= ma_prev:
        return None
    # 2. откат: low коснулся MA
    if last.low > ma_now + tol:
        return None
    # 3. закрытие выше MA, бычья свеча
    if last.close <= ma_now or last.close <= last.open:
        return None

    return Signal(
        name="pullback_to_ma",
        direction="long",
        price=last.close,
        reason=f"откат к {ma.upper()}({period})={ma_now:.2f}, "
               f"close={last.close:.2f} выше MA, бычья свеча",
        meta={"ma": ma, "period": period, "ma_value": ma_now},
    )


def level_reversal(
    candles: List[Candle],
    level: float,
    tolerance_pct: float = 0.15,
) -> Optional[Signal]:
    """
    18.3 Разворот на уровне (контртренд — аккуратно).

    Логика (лонг у поддержки):
      1. Последняя свеча коснулась уровня: low <= level * (1 + tolerance_pct/100).
      2. Свеча-разворот: закрытие выше уровня, бычье тело.
      3. Предыдущая свеча была медвежьей (падение к уровню).

    Args:
        candles: свечи от старых к новым (минимум 2)
        level: уровень поддержки
        tolerance_pct: допуск касания уровня в %

    Returns:
        Signal или None
    """
    if len(candles) < 2:
        return None

    tol = level * tolerance_pct / 100.0
    prev, last = candles[-2], candles[-1]

    # 1. касание уровня
    if last.low > level + tol:
        return None
    # 2. разворот: закрытие выше уровня, бычья свеча
    if last.close <= level or last.close <= last.open:
        return None
    # 3. падение перед разворотом
    if prev.close >= prev.open:
        return None

    return Signal(
        name="level_reversal",
        direction="long",
        price=last.close,
        reason=f"разворот на поддержке {level:.2f} "
               f"(предыдущая медвежья, текущая бычья)",
        meta={"level": level, "counter_trend": True},
    )


def momentum_candle(
    candles: List[Candle],
    body_ratio: float = 0.6,
    volume_mult: float = 1.5,
    volume_period: int = 20,
) -> Optional[Signal]:
    """
    18.4 Моментум-свеча с объёмом.

    Логика (лонг):
      1. Тело последней свечи >= body_ratio от её диапазона (high-low).
      2. Объём последней свечи >= volume_mult * среднего за volume_period.
      3. Свеча бычья (close > open).

    Args:
        candles: свечи от старых к новым (минимум volume_period + 1)
        body_ratio: минимальная доля тела от диапазона (0..1)
        volume_mult: множитель к среднему объёму
        volume_period: окно среднего объёма

    Returns:
        Signal или None
    """
    if len(candles) < volume_period + 1:
        return None

    last = candles[-1]
    rng = last.high - last.low
    if rng <= 0:
        return None
    body = last.close - last.open

    # 3. бычья свеча
    if body <= 0:
        return None
    # 1. тело достаточно большое
    if body / rng < body_ratio:
        return None
    # 2. объём выше среднего
    avg_vol = sum(c.volume for c in candles[-volume_period - 1:-1]) / volume_period
    if avg_vol <= 0 or last.volume < avg_vol * volume_mult:
        return None

    return Signal(
        name="momentum_candle",
        direction="long",
        price=last.close,
        reason=f"бычья моментум-свеча: тело {body / rng:.0%} диапазона, "
               f"объём {last.volume:.0f} >= {volume_mult}x среднего {avg_vol:.0f}",
        meta={"body_ratio": body / rng, "volume_mult": last.volume / avg_vol},
    )


def orderbook_imbalance(
    orderbook: OrderBook,
    threshold: float = 0.6,
    depth: int = 10,
) -> Optional[Signal]:
    """
    18.5 Сигнал по стакану: дисбаланс bid/ask.

    Логика (лонг):
      Суммарный объём лучших `depth` заявок на покупку делится на общую
      сумму (bid + ask). Если bid_share >= threshold — быки сильнее.

    Args:
        orderbook: стакан заявок (bids/asks как [(цена, объём)])
        threshold: порог доли bid (0.6 = 60%)
        depth: сколько уровней учитывать с каждой стороны

    Returns:
        Signal или None
    """
    bid_vol = sum(v for _, v in orderbook.bids[:depth])
    ask_vol = sum(v for _, v in orderbook.asks[:depth])
    total = bid_vol + ask_vol
    if total <= 0:
        return None

    bid_share = bid_vol / total
    if bid_share < threshold:
        return None

    return Signal(
        name="orderbook_imbalance",
        direction="long",
        price=orderbook.mid_price,
        reason=f"дисбаланс стакана: bid {bid_share:.0%} >= {threshold:.0%} "
               f"(bid={bid_vol:.0f}, ask={ask_vol:.0f})",
        meta={"bid_share": bid_share, "depth": depth},
    )


# ─────────────────────────────────────────────────────────────
# Стек фильтров [Ф] — глава 19 (сигнал + все 8 = сделка)
# ─────────────────────────────────────────────────────────────

def trend_filter(candles: List[Candle], period: int = 20) -> FilterResult:
    """19.1 Трендовый: цена выше растущей EMA — только лонг вверх."""
    if len(candles) < period + 1:
        return FilterResult("trend", False, "мало свечей для EMA")

    closes = [c.close for c in candles]
    values = ema(closes, period)
    ema_now, ema_prev = _last(values), _last(values[:-1])

    if closes[-1] > ema_now and ema_now > ema_prev:
        return FilterResult("trend", True,
                            f"close {closes[-1]:.2f} > EMA {ema_now:.2f}, EMA растёт")
    return FilterResult("trend", False,
                        f"цена/EMA не вверх (close={closes[-1]:.2f}, EMA={ema_now:.2f})")


def zone_filter(price: float, zone_low: float, zone_high: float) -> FilterResult:
    """19.2 Зона: цена внутри зоны покупки (у поддержки/уровня)."""
    if zone_low <= price <= zone_high:
        return FilterResult("zone", True,
                            f"цена {price:.2f} в зоне [{zone_low:.2f}, {zone_high:.2f}]")
    return FilterResult("zone", False,
                        f"цена {price:.2f} вне зоны [{zone_low:.2f}, {zone_high:.2f}]")


def volume_filter(
    candles: List[Candle],
    period: int = 20,
    mult: float = 1.2,
) -> FilterResult:
    """19.3 Объёмный: объём последней свечи >= mult * среднего."""
    if len(candles) < period + 1:
        return FilterResult("volume", False, "мало свечей для среднего объёма")

    last = candles[-1]
    avg = sum(c.volume for c in candles[-period - 1:-1]) / period
    if avg > 0 and last.volume >= avg * mult:
        return FilterResult("volume", True,
                            f"объём {last.volume:.0f} >= {mult}x среднего {avg:.0f}")
    return FilterResult("volume", False,
                        f"объём {last.volume:.0f} < {mult}x среднего {avg:.0f}")


def volatility_filter(
    candles: List[Candle],
    period: int = 14,
    min_atr_pct: float = 0.05,
    max_atr_pct: float = 2.0,
) -> FilterResult:
    """19.4 ATR-коридор: не входить ни в «тишину», ни в «шторм»."""
    if len(candles) < period + 1:
        return FilterResult("volatility", False, "мало свечей для ATR")

    # ATR = средний диапазон свечей (простая версия для фильтра)
    ranges = [c.high - c.low for c in candles[-period:]]
    atr = sum(ranges) / len(ranges)
    atr_pct = atr / candles[-1].close * 100.0

    if min_atr_pct <= atr_pct <= max_atr_pct:
        return FilterResult("volatility", True,
                            f"ATR {atr_pct:.3f}% в коридоре "
                            f"[{min_atr_pct}, {max_atr_pct}]")
    return FilterResult("volatility", False,
                        f"ATR {atr_pct:.3f}% вне коридора "
                        f"[{min_atr_pct}, {max_atr_pct}]")


def spread_filter(
    bid: float,
    ask: float,
    max_spread_pct: float = 0.1,
) -> FilterResult:
    """19.5 Спред/ликвидность: спред не шире max_spread_pct."""
    if bid <= 0 or ask <= 0:
        return FilterResult("spread", False, "нет котировок")
    spread_pct = (ask - bid) / bid * 100.0
    if spread_pct <= max_spread_pct:
        return FilterResult("spread", True,
                            f"спред {spread_pct:.4f}% <= {max_spread_pct}%")
    return FilterResult("spread", False,
                        f"спред {spread_pct:.4f}% > {max_spread_pct}%")


def session_filter(
    now: datetime,
    warmup_min: int = 5,
    cooldown_min: int = 10,
) -> FilterResult:
    """
    19.6 Сессионный: не входить в первые/последние минуты сессии.

    Сессии MOEX (МСК): дневная 10:00-18:40, вечерняя 19:05-23:50.
    """
    t = now.time()
    sessions: List[Tuple[time, time]] = [
        (time(10, 0), time(18, 40)),
        (time(19, 5), time(23, 50)),
    ]

    for open_t, close_t in sessions:
        if open_t <= t <= close_t:
            mins_open = (datetime.combine(now.date(), t)
                         - datetime.combine(now.date(), open_t)).seconds // 60
            mins_close = (datetime.combine(now.date(), close_t)
                          - datetime.combine(now.date(), t)).seconds // 60
            if mins_open < warmup_min:
                return FilterResult("session", False,
                                    f"первые {mins_open} мин сессии (нужно >= {warmup_min})")
            if mins_close < cooldown_min:
                return FilterResult("session", False,
                                    f"до конца сессии {mins_close} мин (< {cooldown_min})")
            return FilterResult("session", True,
                                f"сессия в середине (+{mins_open} мин от открытия)")

    return FilterResult("session", False, "вне торговой сессии")


def news_filter(
    now: datetime,
    news_windows: Optional[List[Tuple[datetime, datetime]]] = None,
    embargo_min: int = 15,
) -> FilterResult:
    """
    19.7 Новостной календарь: не входить в эмбарго вокруг новости.

    Args:
        now: текущее время
        news_windows: список (начало, конец) активных новостей;
                      None или [] = новостей нет (фильтр пропускает)
        embargo_min: эмбарго в минутах после конца новости
    """
    if not news_windows:
        return FilterResult("news", True, "новостей нет")

    for start, end in news_windows:
        embargo_end = end + timedelta(minutes=embargo_min)
        if start <= now <= embargo_end:
            return FilterResult("news", False,
                                f"новостное эмбардо до {embargo_end:%H:%M}")
    return FilterResult("news", True, "новостное окно не задето")


def market_open_filter(is_open: bool) -> FilterResult:
    """19.8 Статус-гарант: is_market_open() из datafeed."""
    if is_open:
        return FilterResult("market_open", True, "рынок открыт")
    return FilterResult("market_open", False, "рынок закрыт")


def apply_filters(signal: Signal, filters: List[FilterResult]) -> TradeSetup:
    """
    Формула главы 19: сигнал + все 8 фильтров = сделка; иначе — нет сделки.

    Args:
        signal: сигнал входа
        filters: результаты всех 8 фильтров

    Returns:
        TradeSetup с approved=True только если все фильтры пройдены
    """
    rejections = [f"{f.name}: {f.reason}" for f in filters if not f.passed]
    return TradeSetup(
        signal=signal,
        filters=filters,
        approved=len(rejections) == 0,
        rejections=rejections,
    )


# ─────────────────────────────────────────────────────────────
# Выходы без ТП [В] — глава 20
# ─────────────────────────────────────────────────────────────

def time_stop(
    opened_at: datetime,
    now: datetime,
    in_profit: bool,
    max_minutes: int = 30,
) -> bool:
    """
    20.2 Time-stop: если не в плюс за max_minutes — выход.

    Returns:
        True -> пора выходить
    """
    held = (now - opened_at).total_seconds() / 60.0
    return held >= max_minutes and not in_profit


def reverse_signal_exit(
    candles: List[Candle],
    period: int = 20,
) -> bool:
    """
    20.3 Выход по обратному сигналу (для лонга).

    Обратный сигнал: close ниже EMA и EMA не растёт
    (эквивалент медвежьего crossover).

    Returns:
        True -> пора выходить из лонга
    """
    if len(candles) < period + 1:
        return False

    closes = [c.close for c in candles]
    values = ema(closes, period)
    ema_now, ema_prev = _last(values), _last(values[:-1])

    return closes[-1] < ema_now and ema_now <= ema_prev


def eod_flatten(
    now: datetime,
    flatten_at: time = time(23, 35),
    evening_end: time = time(23, 50),
) -> bool:
    """
    20.5 EOD-flatten: закрыть всё до конца вечерней сессии.

    Срабатывает, если now >= flatten_at (по умолчанию за 15 минут
    до конца вечерней сессии 23:50 МСК).

    Returns:
        True -> закрывать все позиции
    """
    return now.time() >= flatten_at


# ─────────────────────────────────────────────────────────────
# Тесты
# ─────────────────────────────────────────────────────────────

def _run_tests():
    """Встроенные тесты (без сети)."""
    now = datetime(2026, 11, 7, 12, 0, 0)

    # --- breakout_retest ---
    cs = [
        Candle(now, 100, 100.5, 99, 100.2, 1000),
        Candle(now, 100.2, 103, 100, 102.5, 1200),   # пробой level=101
        Candle(now, 100.8, 102.2, 100.5, 101.8, 1100),  # ретест (low в зоне), бычья, закрылась выше уровня
    ]
    sig = breakout_retest(cs, level=101.0, lookback=2)
    assert sig is not None and sig.name == "breakout_retest", sig

    # --- pullback_to_ma ---
    up = [Candle(now, 100 + i, 101 + i, 99.5 + i, 100.8 + i, 1000)
          for i in range(25)]
    # последняя свеча: откат к EMA (EMA≈115, low опускается в зону EMA), close остаётся выше EMA
    up[-1] = Candle(now, 124.0, 125.0, 110.0, 124.5, 1500)
    sig = pullback_to_ma(up, period=20, ma="ema")
    assert sig is not None and sig.name == "pullback_to_ma", sig

    # --- level_reversal ---
    rev = [
        Candle(now, 102, 102.5, 101, 101.2, 1000),  # медвежья
        Candle(now, 101.2, 103, 99.9, 102.5, 1200), # касание 100 + разворот
    ]
    sig = level_reversal(rev, level=100.0)
    assert sig is not None and sig.name == "level_reversal", sig

    # --- momentum_candle ---
    mom = [Candle(now, 100, 101, 99, 100, 1000) for _ in range(21)]
    mom[-1] = Candle(now, 100, 110, 99.5, 109, 3000)  # тело 9/10.5, объём 3x
    sig = momentum_candle(mom, body_ratio=0.6, volume_mult=1.5)
    assert sig is not None and sig.name == "momentum_candle", sig

    # --- orderbook_imbalance ---
    ob = OrderBook(bids=[(100.0, 500), (99.9, 300)],
                   asks=[(100.1, 200), (100.2, 100)],
                   spread=0.1, mid_price=100.05)
    sig = orderbook_imbalance(ob, threshold=0.6)
    assert sig is not None and sig.name == "orderbook_imbalance", sig

    # --- 8 фильтров: happy path ---
    f_trend = trend_filter(up, period=20)
    f_zone = zone_filter(price=101.0, zone_low=99.5, zone_high=102.0)
    f_vol = volume_filter(up, period=20, mult=1.2)
    f_atr = volatility_filter(up, min_atr_pct=0.01, max_atr_pct=5.0)
    f_spread = spread_filter(bid=100.0, ask=100.05, max_spread_pct=0.1)
    f_sess = session_filter(now, warmup_min=5, cooldown_min=10)
    f_news = news_filter(now, news_windows=None)
    f_open = market_open_filter(is_open=True)

    all_filters = [f_trend, f_zone, f_vol, f_atr, f_spread, f_sess, f_news, f_open]
    assert len(all_filters) == 8, "стек должен содержать 8 фильтров"
    assert all(f.passed for f in all_filters), \
        [f.reason for f in all_filters if not f.passed]

    setup = apply_filters(sig, all_filters)
    assert setup.approved and not setup.rejections

    # --- отказ: рынок закрыт ---
    f_open_fail = market_open_filter(is_open=False)
    setup2 = apply_filters(sig, [f_open_fail])
    assert not setup2.approved and setup2.rejections

    # --- time_stop ---
    opened = datetime(2026, 11, 7, 11, 0, 0)
    assert time_stop(opened, datetime(2026, 11, 7, 11, 31), in_profit=False) is True
    assert time_stop(opened, datetime(2026, 11, 7, 11, 31), in_profit=True) is False
    assert time_stop(opened, datetime(2026, 11, 7, 11, 10), in_profit=False) is False

    # --- reverse_signal_exit ---
    down = [Candle(now, 100 - i * 0.5, 101 - i * 0.5, 99 - i * 0.5, 99.8 - i * 0.5, 1000)
            for i in range(25)]
    assert reverse_signal_exit(down, period=20) is True
    assert reverse_signal_exit(up, period=20) is False

    # --- eod_flatten ---
    assert eod_flatten(datetime(2026, 11, 7, 23, 40)) is True
    assert eod_flatten(datetime(2026, 11, 7, 23, 20)) is False

    print("[OK] Все тесты signals пройдены!")
    print(f"   breakout_retest: {sig.price:.2f} @ {sig.name}")
    print(f"   стек фильтров: {sum(f.passed for f in all_filters)}/8 пройдено")
    print(f"   time_stop/reverse/EOD: работают")


if __name__ == "__main__":
    _run_tests()
