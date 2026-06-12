"""
åéç­ç¥è¡ç¼è¿½è¸?â?è¿åè·¯å¾è®°å½ä¸è¡ç¼æ çæ

è®°å½ï¼?- ç¶ä»£IDãåå¼ç®å­ãäº¤åå¯¹è±¡ãè¿åä»£æ?- è¿åè·¯å¾è®°å½
- ç­ç¥è¡ç¼æ çæ
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from app.models import Candidate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# è¡ç¼è®°å½æ°æ®ç»æ?# ---------------------------------------------------------------------------

@dataclass
class LineageRecord:
    """åæ¬¡è¿åæä½çè¡ç¼è®°å½?""

    candidate_id: str
    generation: int
    operator: str  # åå¼ç®å­åç§°ï¼å¦ "MUTATE_ADD", "CROSSOVER"
    parent_ids: List[str] = field(default_factory=list)
    crossover_partner_id: Optional[str] = None
    mutation_details: Dict[str, Any] = field(default_factory=dict)
    fitness_before: Optional[float] = None
    fitness_after: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    symbol: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "generation": self.generation,
            "operator": self.operator,
            "parent_ids": self.parent_ids,
            "crossover_partner_id": self.crossover_partner_id,
            "mutation_details": self.mutation_details,
            "fitness_before": self.fitness_before,
            "fitness_after": self.fitness_after,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
        }


@dataclass
class LineageNode:
    """è¡ç¼æ èç¹"""

    candidate_id: str
    generation: int
    operator: str
    symbol: str
    formula: str = ""
    fitness: Optional[float] = None
    status: str = ""
    children: List["LineageNode"] = field(default_factory=list)
    parent_ids: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "generation": self.generation,
            "operator": self.operator,
            "symbol": self.symbol,
            "formula": self.formula,
            "fitness": self.fitness,
            "status": self.status,
            "children": [c.to_dict() for c in self.children],
            "parent_ids": self.parent_ids,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# è¡ç¼è¿½è¸ªå¨
# ---------------------------------------------------------------------------

class CandidateTracer:
    """åéç­ç¥è¡ç¼è¿½è¸ªå¨"""

    def __init__(self, storage: Optional[Any] = None) -> None:
        """
        Parameters
        ----------
        storage : optional
            å¤é¨å­å¨æ¥å£ï¼éæ¯æ set(key, value) å?get(key) æ¹æ³ã?            é»è®¤ä½¿ç¨åå­å­å¸ã?        """
        self.storage = storage
        self._memory: Dict[str, List[LineageRecord]] = {}

    async def record_lineage(
        self,
        candidate: Candidate,
        operator: str,
        parent_ids: Optional[List[str]] = None,
        crossover_partner_id: Optional[str] = None,
        mutation_details: Optional[Dict[str, Any]] = None,
        fitness_before: Optional[float] = None,
        fitness_after: Optional[float] = None,
    ) -> LineageRecord:
        """è®°å½ä¸æ¬¡è¿åæä½çè¡ç¼ä¿¡æ¯ã?""
        record = LineageRecord(
            candidate_id=candidate.id,
            generation=candidate.generation,
            operator=operator,
            parent_ids=parent_ids or [],
            crossover_partner_id=crossover_partner_id,
            mutation_details=mutation_details or {},
            fitness_before=fitness_before,
            fitness_after=fitness_after,
            symbol=candidate.symbol,
        )

        key = f"lineage:{candidate.id}"
        records = self._memory.get(key, [])
        records.append(record)
        self._memory[key] = records

        if self.storage is not None:
            try:
                await self.storage.set(key, json.dumps([r.to_dict() for r in records], ensure_ascii=False))
            except Exception as e:
                logger.warning(f"è¡ç¼å­å¨å¤±è´? {e}")

        logger.debug(f"[{candidate.symbol}] è®°å½è¡ç¼? {candidate.id} â?{operator}")
        return record

    async def get_lineage(self, candidate_id: str) -> List[LineageRecord]:
        """è·ååéçå®æ´è¡ç¼è®°å½ã?""
        key = f"lineage:{candidate_id}"
        records = self._memory.get(key, [])

        if not records and self.storage is not None:
            try:
                raw = await self.storage.get(key)
                if raw:
                    data = json.loads(raw)
                    records = [LineageRecord(**item) for item in data]
                    self._memory[key] = records
            except Exception as e:
                logger.warning(f"è¡ç¼è¯»åå¤±è´? {e}")

        return records

    async def build_evolution_path(
        self,
        candidate_id: str,
        all_candidates: Optional[Dict[str, Candidate]] = None,
    ) -> List[Dict[str, Any]]:
        """
        æå»ºä»ç§å­å°å½ååéçè¿åè·¯å¾ã?
        Returns
        -------
        list of dict â?ä»æ ¹å°å¶çè¿åæ­¥éª?        """
        path: List[Dict[str, Any]] = []
        visited: Set[str] = set()
        current_id = candidate_id

        while current_id and current_id not in visited:
            visited.add(current_id)
            records = await self.get_lineage(current_id)

            if not records:
                break

            latest = records[-1]
            path.insert(0, latest.to_dict())

            if latest.parent_ids:
                current_id = latest.parent_ids[0]
            else:
                break

        return path

    async def build_lineage_tree(
        self,
        root_candidate: Candidate,
        all_candidates: Dict[str, Candidate],
        max_depth: int = 10,
    ) -> LineageNode:
        """
        ä»æ ¹åéæå»ºå®æ´è¡ç¼æ ã?
        Parameters
        ----------
        root_candidate : Candidate
            æ ¹èç¹åé?        all_candidates : dict[str, Candidate]
            ææåéå­å¸ï¼ç¨äºæ¥æ¾å­ä»£
        max_depth : int
            æå¤§éå½æ·±åº¦

        Returns
        -------
        LineageNode
        """

        def _build_node(candidate: Candidate, depth: int) -> LineageNode:
            node = LineageNode(
                candidate_id=candidate.id,
                generation=candidate.generation,
                operator="SEED" if candidate.is_seed else "EVOLVED",
                symbol=candidate.symbol,
                formula=candidate.formula,
                status=candidate.status.value,
                created_at=candidate.created_at,
            )

            if depth >= max_depth:
                return node

            for child in candidate.children:
                child_node = _build_node(child, depth + 1)
                child_node.parent_ids = [candidate.id]
                node.children.append(child_node)

            return node

        return _build_node(root_candidate, 0)

    async def find_common_ancestor(
        self,
        candidate_a_id: str,
        candidate_b_id: str,
        all_candidates: Dict[str, Candidate],
    ) -> Optional[str]:
        """
        æ¥æ¾ä¸¤ä¸ªåéçæè¿å¬å±ç¥åã?
        Returns
        -------
        str or None â?å¬å±ç¥ååéID
        """
        ancestors_a: Set[str] = set()
        current = candidate_a_id

        while current:
            ancestors_a.add(current)
            cand = all_candidates.get(current)
            if cand and cand.parent_id:
                current = cand.parent_id
            else:
                break

        current = candidate_b_id
        while current:
            if current in ancestors_a:
                return current
            cand = all_candidates.get(current)
            if cand and cand.parent_id:
                current = cand.parent_id
            else:
                break

        return None

    async def compute_diversity_score(
        self,
        candidate_ids: List[str],
        all_candidates: Dict[str, Candidate],
    ) -> float:
        """
        è®¡ç®åéç¾¤ä½çè¡ç¼å¤æ ·æ§å¾åã?
        åºäºå¬å±ç¥åæ¯ä¾ï¼å¬å±ç¥åè¶å°ï¼å¤æ ·æ§è¶é«ã?
        Returns
        -------
        float â?å¤æ ·æ§å¾å?[0, 1]ï¼è¶é«è¶å¤æ ·
        """
        if len(candidate_ids) <= 1:
            return 1.0

        pair_count = 0
        common_count = 0

        for i in range(len(candidate_ids)):
            for j in range(i + 1, len(candidate_ids)):
                pair_count += 1
                ancestor = await self.find_common_ancestor(
                    candidate_ids[i], candidate_ids[j], all_candidates
                )
                if ancestor is not None:
                    common_count += 1

        if pair_count == 0:
            return 1.0

        diversity = 1.0 - (common_count / pair_count)
        return float(diversity)

    async def export_lineage_report(
        self,
        candidate_id: str,
        all_candidates: Optional[Dict[str, Candidate]] = None,
    ) -> Dict[str, Any]:
        """å¯¼åºåéçå®æ´è¡ç¼æ¥åã?""
        path = await self.build_evolution_path(candidate_id, all_candidates)
        records = await self.get_lineage(candidate_id)

        operators_used: Dict[str, int] = {}
        for r in records:
            operators_used[r.operator] = operators_used.get(r.operator, 0) + 1

        return {
            "candidate_id": candidate_id,
            "evolution_path": path,
            "total_operations": len(records),
            "operators_used": operators_used,
            "max_generation": max((r.generation for r in records), default=0),
            "generated_at": datetime.utcnow().isoformat(),
        }
