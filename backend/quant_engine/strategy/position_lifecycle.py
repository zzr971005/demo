"""
ä»ä½çå½å¨æç®¡ç

ç®¡çç­ç¥ä»ä½çå®æ´çå½å¨æï¼
- å¼ä»?â?æä»çæ§ â?å¹³ä»/æ­¢æ â?ç»ç®
- ä»ä½ä¸åéç­ç¥ç»å®?
- æ¯ææ¨¡æçåå®çåºå
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.models import Candidate, Trade, TradeSide, TradeStatus
from strategy.spec import PositionIntent, SignalDirection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ä»ä½ç¶æ?
# ---------------------------------------------------------------------------

class PositionStatus(Enum):
    EMPTY = "EMPTY"
    OPENING = "OPENING"      # ä¸åä¸?
    OPEN = "OPEN"            # å·²æä»?
    CLOSING = "CLOSING"      # å¹³ä»ä¸?
    CLOSED = "CLOSED"        # å·²å¹³ä»?
    PARTIAL = "PARTIAL"      # é¨åæäº¤
    STOPPED = "STOPPED"      # æ­¢æå¹³ä»


# ---------------------------------------------------------------------------
# ä»ä½è®°å½
# ---------------------------------------------------------------------------

@dataclass
class PositionRecord:
    """ä»ä½è®°å½"""

    id: str
    candidate_id: str
    symbol: str
    side: TradeSide
    lots: int
    entry_price: Decimal
    entry_at: datetime
    exit_price: Optional[Decimal] = None
    exit_at: Optional[datetime] = None
    status: PositionStatus = PositionStatus.OPEN
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None
    max_favorable_excursion: Decimal = Decimal("0")
    max_adverse_excursion: Decimal = Decimal("0")
    commission: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    is_paper: bool = True
    order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_long(self) -> bool:
        return self.side == TradeSide.BUY

    @property
    def is_open(self) -> bool:
        return self.status in (PositionStatus.OPEN, PositionStatus.PARTIAL, PositionStatus.OPENING)

    def update_mtm(self, current_price: Decimal) -> Decimal:
        """æ´æ°ç¯å¸çäºã?""
        if not self.is_open:
            return Decimal("0")
        direction = 1 if self.is_long else -1
        mtm = direction * (current_price - self.entry_price) * self.lots
        self.unrealized_pnl = mtm

        if mtm > self.max_favorable_excursion:
            self.max_favorable_excursion = mtm
        if mtm < self.max_adverse_excursion:
            self.max_adverse_excursion = mtm

        return mtm

    def close(
        self,
        exit_price: Decimal,
        exit_at: datetime,
        commission: Decimal = Decimal("0"),
        slippage: Decimal = Decimal("0"),
    ) -> Decimal:
        """å¹³ä»å¹¶è®¡ç®å®ç°çäºã?""
        self.exit_price = exit_price
        self.exit_at = exit_at
        self.commission += commission
        self.slippage += slippage

        direction = 1 if self.is_long else -1
        gross_pnl = direction * (exit_price - self.entry_price) * self.lots
        self.realized_pnl = gross_pnl - self.commission - self.slippage
        self.status = PositionStatus.CLOSED
        self.unrealized_pnl = Decimal("0")

        return self.realized_pnl

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "lots": self.lots,
            "entry_price": float(self.entry_price),
            "entry_at": self.entry_at.isoformat(),
            "exit_price": float(self.exit_price) if self.exit_price else None,
            "exit_at": self.exit_at.isoformat() if self.exit_at else None,
            "status": self.status.value,
            "unrealized_pnl": float(self.unrealized_pnl),
            "realized_pnl": float(self.realized_pnl) if self.realized_pnl else None,
            "stop_loss_price": float(self.stop_loss_price) if self.stop_loss_price else None,
            "take_profit_price": float(self.take_profit_price) if self.take_profit_price else None,
            "commission": float(self.commission),
            "slippage": float(self.slippage),
            "is_paper": self.is_paper,
            "order_id": self.order_id,
        }


# ---------------------------------------------------------------------------
# ä»ä½çå½å¨æç®¡çå?
# ---------------------------------------------------------------------------

class PositionLifecycleManager:
    """ä»ä½çå½å¨æç®¡çå?""

    def __init__(self) -> None:
        self._positions: Dict[str, PositionRecord] = {}
        self._candidate_positions: Dict[str, List[str]] = {}
        self._symbol_positions: Dict[str, List[str]] = {}

    def open_position(
        self,
        position_id: str,
        intent: PositionIntent,
        entry_price: Decimal,
        order_id: Optional[str] = None,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        is_paper: bool = True,
    ) -> PositionRecord:
        """å¼ä»ã?""
        side = TradeSide.BUY if intent.target_direction == SignalDirection.LONG else TradeSide.SELL

        pos = PositionRecord(
            id=position_id,
            candidate_id=intent.candidate_id,
            symbol=intent.symbol,
            side=side,
            lots=intent.target_lots,
            entry_price=entry_price,
            entry_at=intent.timestamp,
            status=PositionStatus.OPENING,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit,
            is_paper=is_paper,
            order_id=order_id,
            metadata={"intent": intent.to_dict()},
        )

        self._positions[position_id] = pos
        self._candidate_positions.setdefault(intent.candidate_id, []).append(position_id)
        self._symbol_positions.setdefault(intent.symbol, []).append(position_id)

        logger.info(
            f"[{intent.symbol}] å¼ä»?{position_id}: "
            f"åé?{intent.candidate_id}, æ¹å={side.value}, ææ°={intent.target_lots}, "
            f"ä»·æ ¼={entry_price}, æ¨¡æ={is_paper}"
        )
        return pos

    def confirm_open(self, position_id: str, filled_price: Decimal, filled_lots: int) -> PositionRecord:
        """ç¡®è®¤å¼ä»æäº¤ã?""
        pos = self._positions.get(position_id)
        if pos is None:
            raise ValueError(f"ä»ä½ {position_id} ä¸å­å?)

        pos.entry_price = filled_price
        pos.lots = filled_lots
        pos.status = PositionStatus.OPEN if filled_lots == pos.lots else PositionStatus.PARTIAL

        logger.info(f"[{pos.symbol}] å¼ä»ç¡®è®?{position_id}: æäº¤={filled_lots}æ?@ {filled_price}")
        return pos

    def close_position(
        self,
        position_id: str,
        exit_price: Decimal,
        exit_at: datetime,
        commission: Decimal = Decimal("0"),
        slippage: Decimal = Decimal("0"),
        reason: str = "",
    ) -> Tuple[PositionRecord, Decimal]:
        """å¹³ä»ã?""
        pos = self._positions.get(position_id)
        if pos is None:
            raise ValueError(f"ä»ä½ {position_id} ä¸å­å?)

        if not pos.is_open:
            logger.warning(f"ä»ä½ {position_id} å·²å³é­ï¼æ æ³éå¤å¹³ä»")
            return pos, Decimal("0")

        pos.status = PositionStatus.CLOSING
        pnl = pos.close(exit_price, exit_at, commission, slippage)
        pos.metadata["close_reason"] = reason

        logger.info(
            f"[{pos.symbol}] å¹³ä» {position_id}: "
            f"ä»·æ ¼={exit_price}, çäº={pnl:.2f}, åå ={reason}"
        )
        return pos, pnl

    def update_position_mtm(self, position_id: str, current_price: Decimal) -> Decimal:
        """æ´æ°ä»ä½ç¯å¸çäºã?""
        pos = self._positions.get(position_id)
        if pos is None or not pos.is_open:
            return Decimal("0")
        return pos.update_mtm(current_price)

    def check_stop_loss(self, position_id: str, current_price: Decimal) -> bool:
        """æ£æ¥æ¯å¦è§¦åæ­¢æã?""
        pos = self._positions.get(position_id)
        if pos is None or not pos.is_open or pos.stop_loss_price is None:
            return False

        if pos.is_long and current_price <= pos.stop_loss_price:
            return True
        if not pos.is_long and current_price >= pos.stop_loss_price:
            return True
        return False

    def check_take_profit(self, position_id: str, current_price: Decimal) -> bool:
        """æ£æ¥æ¯å¦è§¦åæ­¢çã?""
        pos = self._positions.get(position_id)
        if pos is None or not pos.is_open or pos.take_profit_price is None:
            return False

        if pos.is_long and current_price >= pos.take_profit_price:
            return True
        if not pos.is_long and current_price <= pos.take_profit_price:
            return True
        return False

    def get_position(self, position_id: str) -> Optional[PositionRecord]:
        """è·åä»ä½è®°å½ã?""
        return self._positions.get(position_id)

    def get_candidate_positions(
        self,
        candidate_id: str,
        only_open: bool = True,
    ) -> List[PositionRecord]:
        """è·ååéçææä»ä½ã?""
        ids = self._candidate_positions.get(candidate_id, [])
        positions = [self._positions[i] for i in ids if i in self._positions]
        if only_open:
            positions = [p for p in positions if p.is_open]
        return positions

    def get_symbol_positions(
        self,
        symbol: str,
        only_open: bool = True,
    ) -> List[PositionRecord]:
        """è·ååç§çææä»ä½ã?""
        ids = self._symbol_positions.get(symbol, [])
        positions = [self._positions[i] for i in ids if i in self._positions]
        if only_open:
            positions = [p for p in positions if p.is_open]
        return positions

    def get_total_exposure(self, symbol: str) -> int:
        """è·ååç§çæ»æå£ï¼ææ°ï¼å¤å¤´ä¸ºæ­£ï¼ç©ºå¤´ä¸ºè´ï¼ã?""
        positions = self.get_symbol_positions(symbol, only_open=True)
        exposure = 0
        for p in positions:
            direction = 1 if p.is_long else -1
            exposure += direction * p.lots
        return exposure

    def get_unrealized_pnl(self, candidate_id: Optional[str] = None) -> Decimal:
        """è·åæªå®ç°çäºã?""
        if candidate_id:
            positions = self.get_candidate_positions(candidate_id, only_open=True)
        else:
            positions = [p for p in self._positions.values() if p.is_open]
        return sum((p.unrealized_pnl for p in positions), Decimal("0"))

    def get_realized_pnl(self, candidate_id: Optional[str] = None) -> Decimal:
        """è·åå·²å®ç°çäºã?""
        if candidate_id:
            positions = self.get_candidate_positions(candidate_id, only_open=False)
        else:
            positions = list(self._positions.values())
        return sum(
            (p.realized_pnl for p in positions if p.realized_pnl is not None),
            Decimal("0"),
        )

    def to_trade_model(self, position: PositionRecord) -> Trade:
        """å°ä»ä½è®°å½è½¬æ¢ä¸ºTradeæ¨¡åã?""
        return Trade(
            id=position.id,
            symbol=position.symbol,
            candidate_id=position.candidate_id,
            side=position.side,
            quantity=position.lots,
            entry_price=position.entry_price,
            exit_price=position.exit_price,
            entry_at=position.entry_at,
            exit_at=position.exit_at,
            status=TradeStatus.FILLED if position.status == PositionStatus.CLOSED else TradeStatus.PENDING,
            pnl=position.realized_pnl,
            pnl_pct=None,
            commission=position.commission,
            slippage=position.slippage,
            is_paper=position.is_paper,
            order_id=position.order_id,
        )

    def get_all_open_positions(self) -> List[PositionRecord]:
        """è·åæææªå¹³ä»ä»ä½ã?""
        return [p for p in self._positions.values() if p.is_open]

    def clear_closed_positions(self, max_age_hours: Optional[int] = None) -> int:
        """æ¸çå·²å¹³ä»ä»ä½è®°å½ã?""
        now = datetime.utcnow()
        to_remove = []
        for pid, pos in self._positions.items():
            if pos.status == PositionStatus.CLOSED:
                if max_age_hours is None:
                    to_remove.append(pid)
                elif pos.exit_at and (now - pos.exit_at).total_seconds() / 3600 > max_age_hours:
                    to_remove.append(pid)

        for pid in to_remove:
            pos = self._positions.pop(pid)
            if pos.candidate_id in self._candidate_positions:
                self._candidate_positions[pos.candidate_id] = [
                    i for i in self._candidate_positions[pos.candidate_id] if i != pid
                ]
            if pos.symbol in self._symbol_positions:
                self._symbol_positions[pos.symbol] = [
                    i for i in self._symbol_positions[pos.symbol] if i != pid
                ]

        return len(to_remove)
