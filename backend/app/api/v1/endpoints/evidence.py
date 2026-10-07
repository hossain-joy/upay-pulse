"""
upay Pulse — Phase-2 Evidence & Benchmarks endpoint (Workstreams 5, 6, 8)

GET  /api/v1/evidence/benchmarks
    Returns the live union of:
      - reports/ml_report/model_comparison_report.json (M1-M4 + chronological split)
      - reports/ml_report/graph_ablation_study.json   (unseen fraud, threshold frontier)
      - reports/ml_report/leakage_audit_report.json   (14-feature audit)
      - reports/impact_report/synthetic_financial_impact.json (primary KPI)
      - reports/performance_report/concurrency_benchmark.json  (concurrency SLA)
      - reports/soundbox_report/soundbox_latency_benchmark.json (soundbox)
    Each report is read at request time so a regeneration of the underlying scripts is
    immediately visible to the Evidence Dashboard without restarting the API.

POST /api/v1/evidence/simulate-impact
    Re-runs ml/evaluation/financial_impact_simulator.run_financial_impact_simulation()
    and returns the JSON it wrote. This makes the synthetic impact numbers refreshable
    on demand from the Risk Console.
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter

router = APIRouter()


# Resolve the workspace root (parent of `backend/`) regardless of CWD.
# File path: <repo>/backend/app/api/v1/endpoints/evidence.py
# parents[0]=endpoints, [1]=v1, [2]=api, [3]=app, [4]=backend, [5]=<repo>
_REPO_ROOT = Path(__file__).resolve().parents[5]
_REPORTS_DIR = (_REPO_ROOT / "reports").resolve()


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def _collect_evidence() -> Dict[str, Any]:
    """Merge every benchmark JSON into one payload."""
    ml_dir = _REPORTS_DIR / "ml_report"
    impact_dir = _REPORTS_DIR / "impact_report"
    perf_dir = _REPORTS_DIR / "performance_report"
    soundbox_dir = _REPORTS_DIR / "soundbox_report"

    payload: Dict[str, Any] = {
        "schema_version": 1,
        "report_source_directory": str(_REPORTS_DIR),
        "disclaimer": (
            "All metrics below are derived from the synthetic benchmark dataset "
            "shipped in data/synthetic_transactions_clean.csv and the artefacts "
            "under reports/. They are not claims of real banking-rail impact."
        ),
        "ml": {
            "model_comparison": _read_json(ml_dir / "model_comparison_report.json"),
            "graph_ablation": _read_json(ml_dir / "graph_ablation_study.json"),
            "leakage_audit": _read_json(ml_dir / "leakage_audit_report.json"),
        },
        "impact": _read_json(impact_dir / "synthetic_financial_impact.json"),
        "performance": _read_json(perf_dir / "concurrency_benchmark.json"),
        "soundbox": _read_json(soundbox_dir / "soundbox_latency_benchmark.json"),
    }
    return payload


@router.get("/benchmarks", tags=["Evidence & Benchmarks"])
def get_evidence_benchmarks():
    """
    Live evidence snapshot. Reads reports/*.json at request time so script re-runs
    are reflected immediately in the Evidence Dashboard without an API restart.
    """
    return _collect_evidence()


_simulate_lock = threading.Lock()


@router.post("/simulate-impact", tags=["Evidence & Benchmarks"])
def simulate_financial_impact():
    """
    Re-runs the synthetic financial-impact simulator and returns the JSON it wrote.

    Heavy operation guarded by a process-local lock so concurrent dashboard clicks
    don't double-run the simulator or race on the JSON file write.
    """
    with _simulate_lock:
        repo_root = str(_REPO_ROOT)
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        # Defer import to keep startup fast and avoid side-effects at import time.
        from ml.evaluation.financial_impact_simulator import run_financial_impact_simulation

        result = run_financial_impact_simulation() or {}
        impact_path = _REPORTS_DIR / "impact_report" / "synthetic_financial_impact.json"
        on_disk = _read_json(impact_path)
        return {
            "on_disk_payload": on_disk,
            "result_preview": {k: result.get(k) for k in (
                "primary_kpi_fraud_loss_prevented_bdt",
                "net_financial_benefit_bdt",
                "operating_fpr",
                "breakdown",
            ) if k in result},
        }