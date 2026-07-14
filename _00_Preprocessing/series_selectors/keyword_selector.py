from __future__ import annotations

from dataclasses import dataclass

from domain.models import EnrichedSeriesRecord, SelectionDecision
from series_selectors.base import SelectorStrategy


@dataclass
class KeywordSelector(SelectorStrategy):
    accepted_codes: set[str]
    vascular_codes: set[str]
    phase_keywords: list[str]
    include_keywords: list[str]
    exclude_keywords: list[str]
    force_accept_keywords: list[str]
    precedence: str = "exclude"

    def _norm(self, s: str | None) -> str:
        return (s or "").strip().lower()

    def _is_vascular(self, procedure: str) -> bool:
        return procedure.upper() in self.vascular_codes

    def _extract_phase_name(self, text: str) -> str | None:
        for keyword in self.phase_keywords:
            if keyword in text:
                return keyword
        return None

    def decide(self, item: EnrichedSeriesRecord) -> SelectionDecision:
        procedure = self._norm(item.procedure_code_value)
        text = self._norm(item.base.series_description) + " " + self._norm(item.base.series_folder)
        phase_name = self._extract_phase_name(text)
        if not procedure:
            return SelectionDecision(
                status="rejected",
                reason_code="missing_procedure_code",
                reason_detail="Procedure code missing from Excel enrichment",
                include_hits=[],
                exclude_hits=[],
                phase_name=phase_name,
            )

        if procedure.upper() not in self.accepted_codes:
            return SelectionDecision(
                status="rejected",
                reason_code="procedure_code_not_accepted",
                reason_detail=f"Procedure code {procedure.upper()} not in accepted list",
                include_hits=[],
                exclude_hits=[],
                phase_name=phase_name,
            )

        include_hits = [k for k in self.include_keywords if k in text]
        exclude_hits = [k for k in self.exclude_keywords if k in text]
        force_accept_hits = [k for k in self.force_accept_keywords if k in text]

        if self._is_vascular(procedure) and "tor" in exclude_hits:
            exclude_hits = [hit for hit in exclude_hits if hit != "tor"]

        if force_accept_hits:
            return SelectionDecision(
                status="accepted",
                reason_code="forced_keep_keyword",
                reason_detail=f"Accepted by forced-keep keywords: {', '.join(force_accept_hits)}",
                include_hits=include_hits,
                exclude_hits=exclude_hits,
                phase_name=phase_name,
            )

        if exclude_hits:
            return SelectionDecision(
                status="rejected",
                reason_code="matched_exclude_keyword",
                reason_detail=f"Excluded by keywords: {', '.join(exclude_hits)}",
                include_hits=include_hits,
                exclude_hits=exclude_hits,
                phase_name=phase_name,
            )

        if include_hits:
            return SelectionDecision(
                status="accepted",
                reason_code="matched_include_keyword",
                reason_detail=f"Accepted and phase detected from keywords: {', '.join(include_hits)}",
                include_hits=include_hits,
                exclude_hits=exclude_hits,
                phase_name=phase_name,
            )

        return SelectionDecision(
            status="accepted",
            reason_code="accepted_no_exclude_keyword",
            reason_detail="Accepted because no exclusion keyword matched",
            include_hits=include_hits,
            exclude_hits=exclude_hits,
            phase_name=phase_name,
        )
