"""
GTreidLib — модуль математики для алготрейдинга.

Функции:
    # Безубыточность и комиссии
    - break_even_price: цена безубыточности (P_out)
    - break_even_delta: дельта цены и процента безубыточности (ΔP, ΔP%)
    - break_even_summary: полная сводка по безубыточности
    - pct_change: процентное изменение цены
    - round_trip_commission: комиссия «на круг» (вход + выход)
    
    # Стоп-лоссы
    - structural_stop: стоп за структурным минимумом (swing low)
    - atr_stop: стоп по ATR
    - combined_stop: комбинированный стоп (максимум из структурного и ATR)
    - trailing_stop: трейлинг-стоп (подтягивание за ценой)
    - calculate_atr: расчёт Average True Range
    
    # Размер позиции
    - calculate_position_size: размер позиции по фиксированному риску
    - calculate_risk_amount: расчёт суммы риска
    - check_lot_size: округление до лотов
    
    # Риск-менеджмент
    - check_risk_limits: комплексная проверка всех риск-лимитов
    - check_daily_loss: проверка дневного лимита убытков
    - check_max_positions: проверка максимума позиций
    - check_drawdown: проверка максимальной просадки
    - check_risk_reward: проверка минимального R:R
    - check_stop_size: проверка что стоп не слишком большой
    
    # Технические индикаторы
    - sma: простая скользящая средняя (Simple Moving Average)
    - ema: экспоненциальная скользящая средняя (Exponential Moving Average)
    - rsi: относительный индекс силы (Relative Strength Index)
    - vwap: средневзвешенная цена по объёму (Volume Weighted Average Price)
    - crossover: проверка пересечения двух линий ("golden" = снизу вверх, "death" = сверху вниз)
    
    # Получение данных (tcli)
    - DataFeed: класс для получения рыночных данных через tcli
    - Candle: свеча (OHLCV)
    - OrderBook: стакан заявок
    - TradingStatus: статус торгов

    # Сигналы и фильтры
    - Signal / FilterResult / TradeSetup: структуры сигналов
    - breakout_retest / pullback_to_ma / level_reversal /
      momentum_candle / orderbook_imbalance: сигналы входа [С]
    - trend/zone/volume/volatility/spread/session/news/market_open
      + apply_filters: стек из 8 фильтров [Ф] (сигнал + все 8 = сделка)
    - time_stop / reverse_signal_exit / eod_flatten: выходы без ТП [В]
"""

from .break_even import (
    break_even_price,
    break_even_delta,
    break_even_summary,
    pct_change,
    round_trip_commission,
)

from .stop_loss import (
    structural_stop,
    atr_stop,
    combined_stop,
    trailing_stop,
    calculate_atr,
    Candle,
)

from .position_sizing import (
    calculate_position_size,
    calculate_risk_amount,
    check_lot_size,
)

from .risk_check import (
    check_risk_limits,
    check_daily_loss,
    check_max_positions,
    check_drawdown,
    check_risk_reward,
    check_stop_size,
    RiskConfig,
)

from .indicators import (
    sma,
    ema,
    rsi,
    vwap,
    crossover,
)

from .datafeed import (
    DataFeed,
    Candle as DataFeedCandle,
    OrderBook,
    TradingStatus,
    CANDLE_INTERVALS,
)

from .signals import (
    Signal,
    FilterResult,
    TradeSetup,
    breakout_retest,
    pullback_to_ma,
    level_reversal,
    momentum_candle,
    orderbook_imbalance,
    trend_filter,
    zone_filter,
    volume_filter,
    volatility_filter,
    spread_filter,
    session_filter,
    news_filter,
    market_open_filter,
    apply_filters,
    time_stop,
    reverse_signal_exit,
    eod_flatten,
)

__version__ = "0.5.0"
__all__ = [
    # break_even
    "break_even_price",
    "break_even_delta",
    "break_even_summary",
    "pct_change",
    "round_trip_commission",
    # stop_loss
    "structural_stop",
    "atr_stop",
    "combined_stop",
    "trailing_stop",
    "calculate_atr",
    "Candle",
    # position_sizing
    "calculate_position_size",
    "calculate_risk_amount",
    "check_lot_size",
    # risk_check
    "check_risk_limits",
    "check_daily_loss",
    "check_max_positions",
    "check_drawdown",
    "check_risk_reward",
    "check_stop_size",
    "RiskConfig",
    # indicators
    "sma",
    "ema",
    "rsi",
    "vwap",
    "crossover",
    # datafeed
    "DataFeed",
    "DataFeedCandle",
    "OrderBook",
    "TradingStatus",
    "CANDLE_INTERVALS",
    # signals
    "Signal",
    "FilterResult",
    "TradeSetup",
    "breakout_retest",
    "pullback_to_ma",
    "level_reversal",
    "momentum_candle",
    "orderbook_imbalance",
    "trend_filter",
    "zone_filter",
    "volume_filter",
    "volatility_filter",
    "spread_filter",
    "session_filter",
    "news_filter",
    "market_open_filter",
    "apply_filters",
    "time_stop",
    "reverse_signal_exit",
    "eod_flatten",
]
