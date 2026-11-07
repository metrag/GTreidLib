# GTreidLib
Работает через cli-инструмент [tcli](https://github.com/metrag/tcli)
При необходимости доустановить отдельно.
Для разарботки сверять README.md из tcli. При необходимости загрузить последнюю версию

Библиотека математических функций для торгового бота (скальпинг акций MOEX).

## Установка

```bash
cd C:\Users\user\Desktop\algoTreid_book
pip install -e .
```

Или используйте напрямую:

```python
import sys
sys.path.insert(0, r"C:\Users\user\Desktop\algoTreid_book")
from GTreidLib import ...
```

## Модули

### 1. break_even — Безубыточность и комиссии

Расчёт цены безубыточности с учётом комиссий и обслуживания тарифа.

**Функции:**
- `break_even_price(P_in, c, S_day, N, Q)` — цена выхода для безубыточности
- `break_even_pnl(P_in, P_out, Q, c)` — чистая прибыль с учётом комиссий
- `pct_change(P1, P2)` — процентное изменение
- `round_trip_commission(P_in, P_out, Q, c)` — комиссия туда-обратно

**Пример:**
```python
from GTreidLib import break_even_price, break_even_pnl

# Цена входа: 263.50 руб
# Комиссия: 0.05% = 0.0005
# Обслуживание: 390 руб/мес = 19.5 руб/день
# Сделок в день: 5
# Объём: 100 акций

P_out = break_even_price(263.50, 0.0005, 19.5, 5, 100)
print(f"Цена безубыточности: {P_out:.4f} руб")  # 263.8023 руб

pnl = break_even_pnl(263.50, 265.00, 100, 0.0005)
print(f"Чистая прибыль: {pnl:.2f} руб")  # 123.84 руб
```

---

### 2. stop_loss — Расчёт стоп-лоссов

**Функции:**
- `structural_stop(candles, lookback=20, buffer=0.05)` — стоп за структурным минимумом (swing low)
- `atr_stop(candles, atr_period=14, multiplier=2.0, buffer=0.05)` — стоп по ATR (2×ATR)
- `combined_stop(candles, lookback=20, atr_period=14, multiplier=2.0, buffer=0.05)` — комбинированный (максимум из структурного и ATR)
- `trailing_stop(entry_price, current_price, candles, atr_period=14, multiplier=2.0)` — трейлинг-стоп
- `calculate_atr(candles, period=14)` — расчёт ATR

**Пример:**
```python
from GTreidLib import structural_stop, atr_stop, combined_stop, trailing_stop

# candles = список объектов с полями open, high, low, close

# Структурный стоп (за последними 20 свечами)
stop_struct = structural_stop(candles, lookback=20, buffer=0.05)

# ATR-стоп (2×ATR)
stop_atr = atr_stop(candles, atr_period=14, multiplier=2.0, buffer=0.05)

# Комбинированный (выбирает больший стоп)
stop_combined = combined_stop(candles, lookback=20, atr_period=14, multiplier=2.0, buffer=0.05)

# Трейлинг-стоп (двигается за ценой)
stop_trailing = trailing_stop(entry_price=263.50, current_price=265.00, 
                               candles=candles, atr_period=14, multiplier=2.0)
```

**Правила:**
- Стоп НЕ двигается вниз (только вверх для long)
- Комбинированный стоп = max(структурный, ATR) — даёт больше пространства
- Трейлинг активируется после +1R прибыли

---

### 3. position_sizing — Расчёт размера позиции

**Функции:**
- `calculate_position_size(capital, risk_per_trade, entry_price, stop_loss, lot_size)` — размер позиции по фиксированному риску

**Пример:**
```python
from GTreidLib import calculate_position_size

# Капитал: 100,000 руб
# Риск на сделку: 1% = 1000 руб
# Вход: 263.50 руб
# Стоп: 262.35 руб (расстояние 1.15 руб)
# Лот: 100 акций

lots, shares = calculate_position_size(
    capital=100000,
    risk_per_trade=1000,
    entry_price=263.50,
    stop_loss=262.35,
    lot_size=100
)

print(f"Размер позиции: {lots} лотов = {shares} акций")
print(f"Стоимость: {shares * 263.50:.2f} руб")
print(f"Риск: {shares * 1.15:.2f} руб")
```

**Формула:**
```
risk_per_share = entry_price - stop_loss
shares = risk_amount / risk_per_share
lots = shares // lot_size
```

---

### 4. risk_check — Проверка риск-лимитов

**Функции:**
- `check_risk_limits(trades_today, max_trades_per_day, daily_loss, max_daily_loss, positions, max_positions, ...)` — комплексная проверка всех лимитов
- `check_daily_loss(daily_loss, max_daily_loss)` — проверка дневного убытка
- `check_max_positions(positions, max_positions)` — проверка количества позиций
- `check_drawdown(peak_capital, current_capital, max_drawdown_pct)` — проверка просадки
- `check_stop_size(stop_loss_pct, max_stop_pct)` — проверка размера стопа

**Пример:**
```python
from GTreidLib import check_risk_limits

result = check_risk_limits(
    trades_today=3,
    max_trades_per_day=10,
    daily_loss=-500,
    max_daily_loss=2000,
    positions=2,
    max_positions=3,
    peak_capital=100000,
    current_capital=99500,
    max_drawdown_pct=0.10,
    stop_loss_pct=0.0044,
    max_stop_pct=0.015
)

print(f"Проверки пройдено: {result.checks_passed}/{result.checks_total}")
print(f"Можно торговать: {result.allowed}")
if not result.allowed:
    print(f"Причина: {result.reason}")
```

**Проверки:**
1. Дневной убыток < лимита
2. Количество сделок < лимита
3. Количество позиций < лимита
4. Просадка < лимита
5. Размер стопа < лимита

---

### 5. datafeed — Получение рыночных данных

Обёртка над tcli для получения свечей, стакана, последней цены и статуса рынка.

**Класс DataFeed:**
- `get_candles(ticker, interval, from_, to, use_cache=True)` — получение исторических свечей
- `get_last_price(ticker)` — последняя цена инструмента
- `get_orderbook(ticker, depth=10)` — стакан заявок
- `is_market_open(ticker)` — проверка открытия рынка
- `get_sessions()` — торговые сессии MOEX

**Доступные интервалы:**
- `1min`, `5min`, `15min`, `1hour`, `1day`

**Пример:**
```python
from GTreidLib import DataFeed
from datetime import datetime, timedelta

# Инициализация (sandbox для тестов, live для реальной торговли)
df = DataFeed(use_sandbox=True)

# Получить свечи за последний день
now = datetime.now()
yesterday = now - timedelta(days=1)

candles = df.get_candles(
    ticker="SBER",
    interval="5min",
    from_=yesterday,
    to=now,
    use_cache=True  # кэширование в ~/.cache/gtreidlib/
)

print(f"Получено {len(candles)} свечей")
for candle in candles[:5]:
    print(f"  {candle.time}: O={candle.open:.2f} H={candle.high:.2f} "
          f"L={candle.low:.2f} C={candle.close:.2f} V={candle.volume}")

# Последняя цена
price = df.get_last_price("SBER")
print(f"Последняя цена SBER: {price:.2f} руб")

# Проверка рынка
if df.is_market_open("SBER"):
    print("Рынок открыт, можно торговать")
else:
    print("Рынок закрыт")

# Стакан заявок
orderbook = df.get_orderbook("SBER", depth=10)
print(f"Стакан: {len(orderbook.bids)} бидов, {len(orderbook.asks)} асков")
print(f"Спред: {orderbook.spread:.2f} руб")

# Торговые сессии MOEX
sessions = df.get_sessions()
print(f"Дневная сессия: {sessions['day'][0].strftime('%H:%M')}-{sessions['day'][1].strftime('%H:%M')}")
print(f"Вечерняя сессия: {sessions['evening'][0].strftime('%H:%M')}-{sessions['evening'][1].strftime('%H:%M')}")
```

**Особенности:**
- Прямой импорт tcli (не subprocess) для производительности
- Кэширование исторических данных в `~/.cache/gtreidlib/`
- Таймзоны в МСК
- Использование `is_market_open()` из tcli для проверки статуса рынка

---

### 6. signals — Сигналы входа, стек из 8 фильтров и выходы без ТП

Каталог сигналов входа **[С]** (глава 18):

```python
from GTreidLib import (
    breakout_retest, pullback_to_ma, level_reversal,
    momentum_candle, orderbook_imbalance,
    Signal, FilterResult, TradeSetup,
)

# 18.1 Пробой + ретест уровня
sig = breakout_retest(candles, level=310.0, tolerance_pct=0.15, lookback=5)

# 18.2 Откат к EMA/VWAP в тренде
sig = pullback_to_ma(candles, period=20, ma="ema")   # ma: "ema" | "sma" | "vwap"

# 18.3 Разворот на уровне поддержки (контртренд)
sig = level_reversal(candles, level=305.0)

# 18.4 Моментум-свеча с объёмом
sig = momentum_candle(candles, body_ratio=0.6, volume_mult=1.5)

# 18.5 Дисбаланс bid/ask в стакане
sig = orderbook_imbalance(orderbook, threshold=0.6, depth=10)

if sig:
    print(sig.name, sig.direction, sig.price, sig.reason)
```

Стек из 8 фильтров **[Ф]** — *сигнал + все 8 = сделка, иначе — нет сделки* (глава 19):

```python
from GTreidLib import (
    trend_filter, zone_filter, volume_filter, volatility_filter,
    spread_filter, session_filter, news_filter, market_open_filter,
    apply_filters,
)

filters = [
    trend_filter(candles, period=20),                       # 19.1 тренд: цена > растущей EMA
    zone_filter(price, zone_low=305, zone_high=307),        # 19.2 зона покупки
    volume_filter(candles, period=20, mult=1.2),            # 19.3 объём выше среднего
    volatility_filter(candles, min_atr_pct=0.05, max_atr_pct=2.0),  # 19.4 ATR-коридор
    spread_filter(bid, ask, max_spread_pct=0.1),            # 19.5 спред/ликвидность
    session_filter(now, warmup_min=5, cooldown_min=10),     # 19.6 не первые/последние минуты
    news_filter(now, news_windows=None),                    # 19.7 новостное эмбарго
    market_open_filter(is_open=True),                       # 19.8 статус-гарант
]

setup = apply_filters(sig, filters)
if setup.approved:
    ...  # сигнал + все 8 фильтров = сделка
else:
    print("Отказ:", setup.rejections)
```

Выходы без ТП **[В]** (глава 20, стоп и трейлинг — в `stop_loss.py`):

```python
from GTreidLib import time_stop, reverse_signal_exit, eod_flatten

# 20.2 Time-stop: не в плюс за 30 минут -> выход
if time_stop(opened_at, now, in_profit=False, max_minutes=30):
    exit_position()

# 20.3 Выход по обратному сигналу (close ниже падающей EMA)
if reverse_signal_exit(candles, period=20):
    exit_position()

# 20.5 EOD-flatten: закрыть всё до конца вечерней сессии (23:35 МСК)
if eod_flatten(now, flatten_at=time(23, 35)):
    flatten_all()
```

---

## Использование в боте

Пример интеграции всех модулей в торговый цикл:

```python
from GTreidLib import (
    break_even_price,
    combined_stop,
    calculate_position_size,
    check_risk_limits,
)

# 1. Проверяем риск-лимиты
risk_check = check_risk_limits(...)
if not risk_check.allowed:
    print(f"Торговля заблокирована: {risk_check.reason}")
    return

# 2. Рассчитываем стоп-лосс
stop_loss = combined_stop(candles, lookback=20, atr_period=14)

# 3. Рассчитываем точку безубыточности
breakeven = break_even_price(entry_price, commission_rate, daily_service, trades_per_day, lot_size)

# 4. Проверяем что стоп выше безубыточности
if stop_loss > breakeven:
    print("Стоп слишком близко к безубыточности")
    return

# 5. Рассчитываем размер позиции
lots, shares = calculate_position_size(capital, risk_amount, entry_price, stop_loss, lot_size)

# 6. Открываем позицию
open_position(entry_price, lots)
```

---

## Технические индикаторы

### SMA (Simple Moving Average)

```python
from GTreidLib import sma

closes = [100, 102, 101, 103, 105, 107, 106, 108, 110, 112]
sma_values = sma(closes, period=5)

print(f"SMA(5): {sma_values}")
# [None, None, None, None, 102.2, 103.6, 104.4, 105.8, 107.2, 108.6]
```

### EMA (Exponential Moving Average)

```python
from GTreidLib import ema

closes = [100, 102, 101, 103, 105, 107, 106, 108, 110, 112]
ema_values = ema(closes, period=5)

print(f"EMA(5): {ema_values}")
# [None, None, None, None, 102.2, 104.13, 104.75, 106.17, 107.78, 109.52]
```

### RSI (Relative Strength Index)

```python
from GTreidLib import rsi

closes = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
rsi_values = rsi(closes, period=14)

print(f"RSI(14): {rsi_values}")
# Первые 14 значений = None, затем значения от 0 до 100
# RSI > 70 = перекупленность, RSI < 30 = перепроданность
```

### VWAP (Volume Weighted Average Price)

```python
from GTreidLib import vwap

highs = [105, 107, 106, 108, 110]
lows = [100, 102, 101, 103, 105]
closes = [102, 104, 103, 105, 107]
volumes = [1000, 1200, 1100, 1300, 1400]

vwap_value = vwap(highs, lows, closes, volumes)

print(f"VWAP: {vwap_value}")
# 104.31 (средневзвешенная цена по объёму)
```

### Crossover (Пересечение линий)

```python
from GTreidLib import crossover, ema

closes = [100, 102, 101, 103, 105, 107, 106, 108, 110, 112, 115]
fast = ema(closes, period=3)  # быстрая EMA
slow = ema(closes, period=7)  # медленная EMA

signals = crossover(fast, slow)

print(f"Сигналы: {signals}")
# "golden" = бычья линия пересекла медвежью снизу вверх (сигнал на покупку)
# "death" = бычья линия пересекла медвежью сверху вниз (сигнал на продажу)
# None = нет пересечения

# Использование в боте:
for i, signal in enumerate(signals):
    if signal == "golden":
        print(f"Сигнал на покупку на баре {i}")
    elif signal == "death":
        print(f"Сигнал на продажу на баре {i}")
```

---

## Тестирование

Каждый модуль содержит встроенные тесты:

```bash
python -m GTreidLib.break_even
python -m GTreidLib.stop_loss
python -m GTreidLib.position_sizing
python -m GTreidLib.risk_check
python -m GTreidLib.indicators
python -m GTreidLib.datafeed
python -m GTreidLib.signals
```

---

## Профиль торговли

- **Рынок:** MOEX акции
- **Стиль:** Интрадей скальпинг
- **Таймфреймы:** 1М, 5М, 15М, 1Ч, 4Ч
- **Сессии:** Дневная (10:00-18:40), Вечерняя (19:05-23:50)
- **Плечо:** Не используется
- **Шорт:** Не используется (только long)
- **Выход:** Стоп-лосс / обратный сигнал / EOD-flatten

---

## Зависимости

- Python 3.10+
- Нет внешних зависимостей (чистый Python)

---

## Лицензия

MIT

---

## Автор

Создано для проекта алготрейдинга на MOEX.

Версия: 0.4.0
