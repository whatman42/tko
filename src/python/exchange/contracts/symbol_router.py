"""P0 Contract: SymbolRouter — dual-engine awareness, fail-closed.

LOCKED rules:
  symbolType == 1 (MBX)  → ELIGIBLE_FOR_EXECUTION
  symbolType == 3 (NextMe) → DISCOVERED_BUT_EXECUTION_BLOCKED
  unknown / missing      → BLOCK

No silent fallback between type=1 and type=3.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.python.exchange.models.instrument import InstrumentMeta, SymbolType


class ExecutionEligibility(str, Enum):
    ELIGIBLE_FOR_EXECUTION = "ELIGIBLE_FOR_EXECUTION"
    DISCOVERED_BUT_EXECUTION_BLOCKED = "DISCOVERED_BUT_EXECUTION_BLOCKED"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class RouteResult:
    symbol: str
    symbol_type: Optional[int]
    eligibility: ExecutionEligibility
    rest_base: Optional[str]
    public_ws_base: Optional[str]
    private_ws_supported: bool
    reason: str


class SymbolRouter(ABC):
    """Maps instrument metadata → REST/WS endpoints + execution eligibility."""

    @abstractmethod
    def classify(self, instrument: InstrumentMeta) -> RouteResult:
        """Classify a single instrument. Never raises for unknown type — returns BLOCK."""
        ...

    @abstractmethod
    def route_for_symbol(self, symbol: str, instruments: list[InstrumentMeta]) -> RouteResult:
        """Lookup + classify. Missing symbol → BLOCK."""
        ...

    def is_executable(self, instrument: InstrumentMeta) -> bool:
        return self.classify(instrument).eligibility == ExecutionEligibility.ELIGIBLE_FOR_EXECUTION
