from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models import EnrichedSeriesRecord, SelectionDecision


class SelectorStrategy(ABC):
    @abstractmethod
    def decide(self, item: EnrichedSeriesRecord) -> SelectionDecision:
        raise NotImplementedError
