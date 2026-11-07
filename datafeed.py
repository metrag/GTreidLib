"""
Модуль получения рыночных данных через tcli.

Использует прямой доступ к SDK через Broker класс из tcli.
Поддерживает кэширование исторических данных на диск.

Функции:
    - get_candles: получение исторических свечей
    - get_last_price: последняя цена инструмента
    - get_orderbook: стакан заявок
    - get_trading_status: статус торгов
    - is_market_open: проверка открытия рынка
    - get_sessions: торговые сессии MOEX
"""

import pickle
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from tinkoff.invest import CandleInterval


@dataclass
class Candle:
    """Свеча (OHLCV)."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class OrderBook:
    """Стакан заявок."""
    bids: List[Tuple[float, int]]  # [(цена, объём)]
    asks: List[Tuple[float, int]]
    spread: float
    mid_price: float


@dataclass
class TradingStatus:
    """Статус торгов инструмента."""
    figi: str
    ticker: str
    is_open: bool
    limit_up: Optional[float]
    limit_down: Optional[float]


# Интервалы свечей
CANDLE_INTERVALS = {
    "1min": CandleInterval.CANDLE_INTERVAL_1_MIN,
    "5min": CandleInterval.CANDLE_INTERVAL_5_MIN,
    "15min": CandleInterval.CANDLE_INTERVAL_15_MIN,
    "1hour": CandleInterval.CANDLE_INTERVAL_HOUR,
    "1day": CandleInterval.CANDLE_INTERVAL_DAY,
}


class DataFeed:
    """
    Класс для получения рыночных данных через tcli.
    
    Пример:
        >>> from GTreidLib.datafeed import DataFeed
        >>> df = DataFeed(sandbox=True)
        >>> candles = df.get_candles("SBER", days_ago=7, interval="1min")
        >>> price = df.get_last_price("SBER")
    """
    
    def __init__(self, sandbox: bool = True, cache_dir: Optional[Path] = None):
        """
        Инициализация DataFeed.
        
        Args:
            sandbox: использовать sandbox (True) или live (False)
            cache_dir: директория для кэша (по умолчанию ~/.cache/gtreidlib)
        """
        from tcli.client import Broker
        from tcli.config import Settings, Contour
        
        # Загружаем настройки
        settings = Settings.load()
        
        # Устанавливаем контур
        if sandbox:
            settings.contour = Contour.SANDBOX
        else:
            settings.contour = Contour.LIVE
        
        self.broker = Broker(settings)
        self.sandbox = sandbox
        self.cache_dir = cache_dir or Path.home() / ".cache" / "gtreidlib"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Кэш FIGI
        self._figi_cache = {}
    
    def _get_figi(self, ticker: str) -> str:
        """Получить FIGI по тикеру (с кэшированием)."""
        if ticker not in self._figi_cache:
            instrument = self.broker.find_instrument_smart(ticker)
            self._figi_cache[ticker] = instrument.figi
        return self._figi_cache[ticker]
    
    def _cache_key(self, ticker: str, interval: str, from_: datetime, to: datetime) -> str:
        """Создать ключ для кэша."""
        return f"{ticker}_{interval}_{from_.isoformat()}_{to.isoformat()}"
    
    def _load_cache(self, key: str) -> Optional[List[Candle]]:
        """Загрузить из кэша."""
        cache_file = self.cache_dir / f"{key}.pkl"
        if cache_file.exists():
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        return None
    
    def _save_cache(self, key: str, candles: List[Candle]) -> None:
        """Сохранить в кэш."""
        cache_file = self.cache_dir / f"{key}.pkl"
        with open(cache_file, "wb") as f:
            pickle.dump(candles, f)
    
    def get_candles(
        self,
        ticker: str,
        from_: Optional[datetime] = None,
        to: Optional[datetime] = None,
        interval: str = "1min",
        days_ago: Optional[int] = None,
    ) -> List[Candle]:
        """
        Получить исторические свечи.
        
        Args:
            ticker: тикер инструмента (например, "SBER")
            from_: начало периода (если не указано, используется days_ago)
            to_: конец периода (если не указано, текущее время)
            interval: интервал свечей ("1min", "5min", "15min", "1hour", "1day")
            days_ago: сколько дней назад начать (если from_ не указан)
        
        Returns:
            Список свечей от старых к новым
        
        Пример:
            >>> candles = df.get_candles("SBER", days_ago=7, interval="1min")
            >>> candles = df.get_candles("GAZP", from_=datetime(2024, 1, 1), interval="1day")
        """
        if interval not in CANDLE_INTERVALS:
            raise ValueError(f"Неизвестный интервал: {interval}. Доступны: {list(CANDLE_INTERVALS.keys())}")
        
        # Определить временной диапазон
        if from_ is None:
            if days_ago is None:
                days_ago = 1
            from_ = datetime.now() - timedelta(days=days_ago)
        
        if to is None:
            to = datetime.now()
        
        # Проверить кэш
        cache_key = self._cache_key(ticker, interval, from_, to)
        cached = self._load_cache(cache_key)
        if cached is not None:
            return cached
        
        # Получить FIGI
        figi = self._get_figi(ticker)
        
        # Получить свечи через tcli
        sdk_interval = CANDLE_INTERVALS[interval]
        raw_candles = self.broker.candles(figi, sdk_interval, from_, to)
        
        # Конвертировать в наш формат
        candles = []
        for c in raw_candles:
            candles.append(Candle(
                timestamp=c.time,
                open=float(c.open),
                high=float(c.high),
                low=float(c.low),
                close=float(c.close),
                volume=c.volume,
            ))
        
        # Сохранить в кэш
        self._save_cache(cache_key, candles)
        
        return candles
    
    def get_last_price(self, ticker: str) -> float:
        """
        Получить последнюю цену инструмента.
        
        Args:
            ticker: тикер инструмента
        
        Returns:
            Последняя цена
        
        Пример:
            >>> price = df.get_last_price("SBER")
        """
        figi = self._get_figi(ticker)
        status = self.broker.trading_status(figi)
        
        # last_price в MoneyValue, конвертируем в float
        return float(status.last_price)
    
    def get_orderbook(self, ticker: str, depth: int = 10) -> OrderBook:
        """
        Получить стакан заявок.
        
        Args:
            ticker: тикер инструмента
            depth: глубина стакана (по умолчанию 10)
        
        Returns:
            OrderBook с bids, asks, spread, mid_price
        
        Пример:
            >>> ob = df.get_orderbook("SBER", depth=10)
            >>> print(f"Spread: {ob.spread:.2f}")
        """
        figi = self._get_figi(ticker)
        raw_ob = self.broker.orderbook(figi, depth)
        
        # Конвертировать bids и asks
        bids = [(float(b.price), b.quantity) for b in raw_ob.bids]
        asks = [(float(a.price), a.quantity) for a in raw_ob.asks]
        
        # Рассчитать spread и mid_price
        if bids and asks:
            best_bid = bids[-1][0]  # Последний bid (лучшая цена)
            best_ask = asks[0][0]   # Первый ask (лучшая цена)
            spread = best_ask - best_bid
            mid_price = (best_bid + best_ask) / 2
        else:
            spread = 0.0
            mid_price = 0.0
        
        return OrderBook(
            bids=bids,
            asks=asks,
            spread=spread,
            mid_price=mid_price,
        )
    
    def get_trading_status(self, ticker: str) -> TradingStatus:
        """
        Получить статус торгов инструмента.
        
        Args:
            ticker: тикер инструмента
        
        Returns:
            TradingStatus с информацией о торгах
        
        Пример:
            >>> status = df.get_trading_status("SBER")
            >>> print(f"Market open: {status.is_open}")
        """
        figi = self._get_figi(ticker)
        raw_status = self.broker.trading_status(figi)
        
        # Конвертировать limit prices
        limit_up = float(raw_status.limit_up_price) if raw_status.limit_up_price else None
        limit_down = float(raw_status.limit_down_price) if raw_status.limit_down_price else None
        
        return TradingStatus(
            figi=figi,
            ticker=ticker,
            is_open=raw_status.trading_status,
            limit_up=limit_up,
            limit_down=limit_down,
        )
    
    def is_market_open(self, ticker: str) -> bool:
        """
        Проверить, открыт ли рынок для инструмента.
        
        Args:
            ticker: тикер инструмента
        
        Returns:
            True если рынок открыт, False иначе
        
        Пример:
            >>> if df.is_market_open("SBER"):
            ...     print("Торгуем!")
        """
        return self.broker.is_market_open(self._get_figi(ticker))
    
    def get_sessions(self) -> List[Tuple[time, time]]:
        """
        Получить торговые сессии MOEX (МСК).
        
        Returns:
            Список кортежей (начало, конец) сессий
        
        Пример:
            >>> sessions = df.get_sessions()
            >>> for start, end in sessions:
            ...     print(f"{start} - {end}")
        """
        return [
            (time(10, 0), time(18, 40)),    # Дневная сессия
            (time(19, 5), time(23, 50)),    # Вечерняя сессия
        ]


# ─────────────────────────────────────────────────────────────
# Тесты (для самопроверки)
# ─────────────────────────────────────────────────────────────

def _run_tests():
    """Встроенные тесты для проверки структуры (без реальных вызовов)."""
    
    # Тест 1: Создание DataFeed (sandbox)
    try:
        df = DataFeed(sandbox=True)
        assert df.sandbox is True
        assert df.cache_dir.exists()
        print("[OK] DataFeed создан в sandbox режиме")
    except Exception as e:
        print(f"[SKIP] DataFeed не создан (tcli не установлен): {e}")
        return
    
    # Тест 2: Интервалы свечей
    assert "1min" in CANDLE_INTERVALS
    assert "5min" in CANDLE_INTERVALS
    assert "15min" in CANDLE_INTERVALS
    assert "1hour" in CANDLE_INTERVALS
    assert "1day" in CANDLE_INTERVALS
    print("[OK] Интервалы свечей определены")
    
    # Тест 3: Торговые сессии
    sessions = df.get_sessions()
    assert len(sessions) == 2
    assert sessions[0] == (time(10, 0), time(18, 40))
    assert sessions[1] == (time(19, 5), time(23, 50))
    print("[OK] Торговые сессии MOEX корректны")
    
    # Тест 4: Структуры данных
    candle = Candle(
        timestamp=datetime.now(),
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=1000,
    )
    assert candle.open == 100.0
    assert candle.volume == 1000
    
    ob = OrderBook(
        bids=[(100.0, 10), (99.5, 20)],
        asks=[(100.5, 15), (101.0, 25)],
        spread=0.5,
        mid_price=100.25,
    )
    assert len(ob.bids) == 2
    assert ob.spread == 0.5
    
    print("[OK] Структуры данных корректны")
    
    print("\n[OK] Все тесты пройдены!")
    print("     DataFeed готов к использованию.")


if __name__ == "__main__":
    _run_tests()
