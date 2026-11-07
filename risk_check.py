"""
Проверка риск-лимитов.

Функции:
    - check_risk_limits: проверка всех риск-лимитов
    - check_daily_loss: проверка дневного лимита убытков
    - check_max_positions: проверка максимума позиций
    - check_drawdown: проверка максимальной просадки
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RiskConfig:
    """Конфигурация риск-лимитов."""
    max_daily_loss: float = 0.02          # макс. дневной убыток (0.02 = 2% от капитала)
    max_positions: int = 3                # макс. открытых позиций
    max_position_pct: float = 0.25        # макс. позиция в % от капитала (0.25 = 25%)
    max_drawdown: float = 0.10            # макс. просадка (0.10 = 10% от капитала)
    max_daily_trades: int = 20            # макс. сделок в день
    min_risk_reward: float = 2.0          # мин. R:R
    max_stop_pct: float = 0.015           # макс. стоп в % от entry (0.015 = 1.5%)


@dataclass
class RiskCheckResult:
    """Результат проверки риск-лимитов."""
    allowed: bool              # можно ли открывать позицию
    reason: Optional[str]      # причина отказа (если allowed=False)
    checks_passed: int         # сколько проверок пройдено
    checks_total: int          # всего проверок
    violations: List[str]      # список нарушений


# ─────────────────────────────────────────────────────────────
# Проверка дневного лимита убытков
# ─────────────────────────────────────────────────────────────

def check_daily_loss(
    daily_pnl: float,
    capital: float,
    max_daily_loss: float = 0.02,
) -> tuple[bool, Optional[str]]:
    """
    Проверка дневного лимита убытков.

    Args:
        daily_pnl: дневной PnL (отрицательный = убыток)
        capital: текущий капитал
        max_daily_loss: макс. убыток в долях (0.02 = 2%)

    Returns:
        (passed, reason) — True если можно торговать

    Пример:
        >>> passed, reason = check_daily_loss(-1500, 100000, 0.02)
        >>> passed
        True
        >>> passed, reason = check_daily_loss(-2500, 100000, 0.02)
        >>> passed
        False
    """
    max_loss_amount = capital * max_daily_loss
    loss_amount = abs(daily_pnl) if daily_pnl < 0 else 0

    if loss_amount >= max_loss_amount:
        return False, f"Дневной лимит убытков: {loss_amount:.0f} / {max_loss_amount:.0f} руб"

    return True, None


# ─────────────────────────────────────────────────────────────
# Проверка максимума позиций
# ─────────────────────────────────────────────────────────────

def check_max_positions(
    current_positions: int,
    max_positions: int = 3,
) -> tuple[bool, Optional[str]]:
    """
    Проверка максимума открытых позиций.

    Args:
        current_positions: текущее количество позиций
        max_positions: максимум позиций

    Returns:
        (passed, reason)

    Пример:
        >>> passed, _ = check_max_positions(2, max_positions=3)
        >>> passed
        True
    """
    if current_positions >= max_positions:
        return False, f"Максимум позиций: {current_positions} / {max_positions}"

    return True, None


# ─────────────────────────────────────────────────────────────
# Проверка просадки
# ─────────────────────────────────────────────────────────────

def check_drawdown(
    peak_capital: float,
    current_capital: float,
    max_drawdown: float = 0.10,
) -> tuple[bool, Optional[str]]:
    """
    Проверка максимальной просадки от пика.

    Args:
        peak_capital: пиковый капитал
        current_capital: текущий капитал
        max_drawdown: макс. просадка в долях (0.10 = 10%)

    Returns:
        (passed, reason)

    Пример:
        >>> passed, _ = check_drawdown(100000, 92000, 0.10)
        >>> passed
        True
        >>> passed, reason = check_drawdown(100000, 88000, 0.10)
        >>> passed
        False
    """
    if peak_capital <= 0:
        return False, "peak_capital должен быть > 0"

    drawdown = (peak_capital - current_capital) / peak_capital

    if drawdown >= max_drawdown:
        return False, f"Просадка: {drawdown*100:.1f}% / {max_drawdown*100:.0f}%"

    return True, None


# ─────────────────────────────────────────────────────────────
# Проверка R:R (risk/reward)
# ─────────────────────────────────────────────────────────────

def check_risk_reward(
    entry_price: float,
    stop_price: float,
    take_price: float,
    min_rr: float = 2.0,
) -> tuple[bool, Optional[str]]:
    """
    Проверка минимального R:R.

    Args:
        entry_price: цена входа
        stop_price: цена стоп-лосса
        take_price: цена тейк-профита
        min_rr: минимальное R:R

    Returns:
        (passed, reason)

    Пример:
        >>> passed, _ = check_risk_reward(100, 98, 104, min_rr=2.0)
        >>> passed  # risk=2, reward=4, R:R=2.0
        True
    """
    risk = entry_price - stop_price
    reward = take_price - entry_price

    if risk <= 0:
        return False, "Stop должен быть ниже entry"

    rr = reward / risk

    if rr < min_rr:
        return False, f"R:R = {rr:.2f} < {min_rr:.1f}"

    return True, None


# ─────────────────────────────────────────────────────────────
# Проверка размера стопа
# ─────────────────────────────────────────────────────────────

def check_stop_size(
    entry_price: float,
    stop_price: float,
    max_stop_pct: float = 0.015,
) -> tuple[bool, Optional[str]]:
    """
    Проверка что стоп не слишком большой.

    Args:
        entry_price: цена входа
        stop_price: цена стоп-лосса
        max_stop_pct: макс. стоп в % от entry

    Returns:
        (passed, reason)

    Пример:
        >>> passed, _ = check_stop_size(100, 99, max_stop_pct=0.015)
        >>> passed  # stop = 1%
        True
    """
    stop_pct = (entry_price - stop_price) / entry_price

    if stop_pct > max_stop_pct:
        return False, f"Стоп слишком большой: {stop_pct*100:.2f}% > {max_stop_pct*100:.1f}%"

    return True, None


# ─────────────────────────────────────────────────────────────
# Комплексная проверка всех лимитов
# ─────────────────────────────────────────────────────────────

def check_risk_limits(
    capital: float,
    daily_pnl: float = 0.0,
    current_positions: int = 0,
    peak_capital: Optional[float] = None,
    entry_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    take_price: Optional[float] = None,
    config: Optional[RiskConfig] = None,
) -> RiskCheckResult:
    """
    Комплексная проверка всех риск-лимитов.

    Проверяет:
    1. Дневной лимит убытков
    2. Максимум позиций
    3. Максимальная просадка
    4. R:R (если указаны entry/stop/take)
    5. Размер стопа (если указаны entry/stop)

    Args:
        capital: текущий капитал
        daily_pnl: дневной PnL
        current_positions: текущее количество позиций
        peak_capital: пиковый капитал (для просадки)
        entry_price: цена входа (опционально)
        stop_price: цена стоп-лосса (опционально)
        take_price: цена тейк-профита (опционально)
        config: конфигурация риск-лимитов (по умолчанию RiskConfig())

    Returns:
        RiskCheckResult

    Пример:
        >>> config = RiskConfig(max_daily_loss=0.02, max_positions=3)
        >>> result = check_risk_limits(
        ...     capital=100000,
        ...     daily_pnl=-1000,
        ...     current_positions=1,
        ...     config=config
        ... )
        >>> result.allowed
        True
    """
    if config is None:
        config = RiskConfig()

    violations = []
    checks_passed = 0
    checks_total = 0

    # 1. Дневной лимит убытков
    checks_total += 1
    passed, reason = check_daily_loss(daily_pnl, capital, config.max_daily_loss)
    if passed:
        checks_passed += 1
    else:
        violations.append(reason)

    # 2. Максимум позиций
    checks_total += 1
    passed, reason = check_max_positions(current_positions, config.max_positions)
    if passed:
        checks_passed += 1
    else:
        violations.append(reason)

    # 3. Просадка (если указан peak_capital)
    if peak_capital is not None:
        checks_total += 1
        passed, reason = check_drawdown(peak_capital, capital, config.max_drawdown)
        if passed:
            checks_passed += 1
        else:
            violations.append(reason)

    # 4. R:R (если указаны entry/stop/take)
    if entry_price is not None and stop_price is not None and take_price is not None:
        checks_total += 1
        passed, reason = check_risk_reward(entry_price, stop_price, take_price, config.min_risk_reward)
        if passed:
            checks_passed += 1
        else:
            violations.append(reason)

    # 5. Размер стопа (если указаны entry/stop)
    if entry_price is not None and stop_price is not None:
        checks_total += 1
        passed, reason = check_stop_size(entry_price, stop_price, config.max_stop_pct)
        if passed:
            checks_passed += 1
        else:
            violations.append(reason)

    allowed = len(violations) == 0
    reason = violations[0] if violations else None

    return RiskCheckResult(
        allowed=allowed,
        reason=reason,
        checks_passed=checks_passed,
        checks_total=checks_total,
        violations=violations,
    )


# ─────────────────────────────────────────────────────────────
# Тесты
# ─────────────────────────────────────────────────────────────

def _run_tests():
    """Встроенные тесты."""

    # Тест 1: Базовая проверка (всё OK)
    config = RiskConfig(max_daily_loss=0.02, max_positions=3)
    result = check_risk_limits(
        capital=100000,
        daily_pnl=-1000,
        current_positions=1,
        config=config,
    )
    assert result.allowed, f"Should be allowed, but violations: {result.violations}"
    print(f"[OK] Basic check: {result.checks_passed}/{result.checks_total} passed")

    # Тест 2: Превышение дневного лимита
    result2 = check_risk_limits(
        capital=100000,
        daily_pnl=-2500,  # 2.5% > 2%
        current_positions=1,
        config=config,
    )
    assert not result2.allowed, "Should be denied (daily loss exceeded)"
    assert "Дневной лимит" in result2.reason
    print(f"[OK] Daily loss exceeded: {result2.reason}")

    # Тест 3: Максимум позиций
    result3 = check_risk_limits(
        capital=100000,
        daily_pnl=0,
        current_positions=3,  # = max_positions
        config=config,
    )
    assert not result3.allowed, "Should be denied (max positions)"
    assert "Максимум позиций" in result3.reason
    print(f"[OK] Max positions: {result3.reason}")

    # Тест 4: Просадка
    result4 = check_risk_limits(
        capital=88000,
        daily_pnl=0,
        current_positions=0,
        peak_capital=100000,  # drawdown = 12% > 10%
        config=RiskConfig(max_drawdown=0.10),
    )
    assert not result4.allowed, "Should be denied (drawdown)"
    assert "Просадка" in result4.reason
    print(f"[OK] Drawdown: {result4.reason}")

    # Тест 5: R:R проверка (max_stop_pct увеличен, чтобы stop_size не мешал)
    result5 = check_risk_limits(
        capital=100000,
        entry_price=100,
        stop_price=98,    # risk = 2
        take_price=104,   # reward = 4, R:R = 2.0
        config=RiskConfig(min_risk_reward=2.0, max_stop_pct=0.05),
    )
    assert result5.allowed, f"R:R=2.0 should pass, violations: {result5.violations}"
    print(f"[OK] R:R = 2.0: passed")

    result6 = check_risk_limits(
        capital=100000,
        entry_price=100,
        stop_price=98,    # risk = 2
        take_price=103,   # reward = 3, R:R = 1.5 < 2.0
        config=RiskConfig(min_risk_reward=2.0, max_stop_pct=0.05),
    )
    assert not result6.allowed, "R:R=1.5 should fail"
    assert "R:R" in result6.reason
    print(f"[OK] R:R = 1.5: {result6.reason}")

    # Тест 6: Размер стопа
    result7 = check_risk_limits(
        capital=100000,
        entry_price=100,
        stop_price=97,    # stop = 3% > 1.5%
        config=RiskConfig(max_stop_pct=0.015),
    )
    assert not result7.allowed, "Stop too large should fail"
    assert "Стоп слишком большой" in result7.reason
    print(f"[OK] Stop size: {result7.reason}")

    print("\n[OK] Все тесты risk_check пройдены!")


if __name__ == "__main__":
    _run_tests()
