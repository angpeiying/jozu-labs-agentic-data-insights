from __future__ import annotations
from typing import Dict, Any, List
import pandas as pd

def verify_hypotheses(df: pd.DataFrame, hypotheses: List[Dict[str, Any]], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    verified: List[Dict[str, Any]] = []

    for h in hypotheses[:10]:
        kind = h.get("kind")
        payload = dict(h)
        payload["verified"] = False
        payload["evidence"] = None

        try:
            if kind == "missingness":
                col = h.get("col")
                if col in df.columns:
                    payload["verified"] = True
                    payload["evidence"] = {"missing_rate": float(df[col].isna().mean())}

            elif kind == "category_dominance":
                col = h.get("col")
                if col in df.columns:
                    vc = df[col].value_counts(dropna=True)
                    if len(vc) > 0:
                        top_share = float(vc.iloc[0] / max(vc.sum(), 1))
                        payload["verified"] = True
                        payload["evidence"] = {"top_value": str(vc.index[0]), "top_share": top_share}

            elif kind == "correlation":
                x, y = h.get("x"), h.get("y")
                if x in df.columns and y in df.columns:
                    sub = df[[x, y]].dropna()
                    if len(sub) >= 10:
                        corr = float(sub[x].corr(sub[y]))
                        payload["verified"] = True
                        payload["evidence"] = {"pearson_corr": corr, "n": int(len(sub))}

        except Exception as e:
            payload["verify_error"] = str(e)

        verified.append(payload)

    return verified
