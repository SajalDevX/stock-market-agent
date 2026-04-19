from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass
class CorporateAction:
    ex_date: date
    kind: str  # split|bonus|dividend|rights|merger|delisting
    ratio_num: float | None = None
    ratio_den: float | None = None
    dividend_per_share: float | None = None

    @property
    def price_factor(self) -> float:
        """Multiplier to apply to pre-ex_date prices."""
        if self.kind in ("split", "bonus") and self.ratio_num and self.ratio_den:
            return self.ratio_num / self.ratio_den
        return 1.0

    @property
    def volume_factor(self) -> float:
        if self.kind in ("split", "bonus") and self.ratio_num and self.ratio_den:
            return self.ratio_den / self.ratio_num
        return 1.0


class CorporateActionSet:
    def __init__(self, records: list[dict | CorporateAction]) -> None:
        self._actions: list[CorporateAction] = []
        for r in records:
            if isinstance(r, CorporateAction):
                self._actions.append(r)
            else:
                self._actions.append(CorporateAction(**r))
        self._actions.sort(key=lambda a: a.ex_date)

    def iter_price_affecting(self):
        for a in self._actions:
            if a.kind in ("split", "bonus"):
                yield a


def apply_adjustments(df: pd.DataFrame, actions: CorporateActionSet) -> pd.DataFrame:
    """Back-adjust OHLC so historical rows are comparable to post-action prices.

    Convention: bars with index date strictly earlier than ex_date get multiplied
    by the action's price_factor (and volumes by volume_factor).
    Dividends and rights are not applied here (technical agent treats them separately).
    """
    if df.empty:
        return df.copy()
    out = df.copy()
    for a in actions.iter_price_affecting():
        ex = pd.Timestamp(a.ex_date)
        mask = out.index < ex
        pf = a.price_factor
        vf = a.volume_factor
        for col in ("open", "high", "low", "close"):
            if col in out.columns:
                out.loc[mask, col] = out.loc[mask, col] * pf
        if "volume" in out.columns:
            out.loc[mask, "volume"] = (out.loc[mask, "volume"] * vf).round().astype("int64")
    return out
