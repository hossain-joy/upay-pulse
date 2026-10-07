# upay Pulse — Phase-2 Evidence Provenance

This file is the single source-of-truth for every numeric claim made in
[`PHASE2_MASTER_BLUEPRINT.md`](PHASE2_MASTER_BLUEPRINT.md). Each row links a
claim to the JSON artefact it derives from, the script that produced the
artefact, and the one-line command required to regenerate it. When the JSON
and the blueprint disagree, **the JSON wins** — see the §0 honesty note in the
blueprint.

---

## 1. ML model metrics

| Claim (blueprint location) | Source JSON | Source script | Regenerate |
|---|---|---|---|
| §4.3 M1–M4 ablation table values | `reports/ml_report/model_comparison_report.json` | `ml/training/train_phase2_models.py` (`_run_comparison` → JSON dump) | `python -m ml.training.train_phase2_models` |
| §4.3 chronological split (10.5k / 2.25k / 2.25k, Jul 9 – Oct 7 2026) | `reports/ml_report/model_comparison_report.json` `chronological_split` | same as above | same as above |
| §4.4 unseen-fraud benchmark (0.0% / 42.0% / 40.0% fused / +40.0 pp lift) | `reports/ml_report/graph_ablation_study.json` `unseen_fraud_benchmark` | `ml/evaluation/run_full_ablation_experiment.py` | `python -m ml.evaluation.run_full_ablation_experiment` |
| §4.4 standard test fused PR-AUC 0.9929 | `reports/ml_report/graph_ablation_study.json` `standard_test_benchmark.fused_pr_auc` | same | same |
| §4.5 threshold frontier table | `reports/ml_report/graph_ablation_study.json` `threshold_frontier[]` | same | same |
| Leakage audit (14 features CLEAN_CAUSAL) | `reports/ml_report/leakage_audit_report.json` | `ml/evaluation/leakage_audit.py` | `python -m ml.evaluation.leakage_audit` |

## 2. Business / financial impact

| Claim | Source JSON | Source script | Regenerate |
|---|---|---|---|
| §6 primary KPI ৳6,164,415 / 10k | `reports/impact_report/synthetic_financial_impact.json` `primary_kpi_fraud_loss_prevented_bdt` | `ml/evaluation/financial_impact_simulator.py` | `python -m ml.evaluation.financial_impact_simulator` |
| §6 net benefit ৳6,147,148 | same JSON `net_financial_benefit_bdt` | same | same |
| §6 operating FPR 0.44% | same JSON `operating_fpr` | same | same |
| §6 friction / analyst breakdown | same JSON `breakdown.upay_pulse_fused` | same | same |

## 3. Operations / performance

| Claim | Source JSON | Source script | Regenerate |
|---|---|---|---|
| §10 concurrency table (10/25/50 workers, p50/p95/p99, 0% errors) | `reports/performance_report/concurrency_benchmark.json` | `load_tests/run_concurrency_bench.py` | `python -m load_tests.run_concurrency_bench` |
| §4.3 M3 p50 0.78 ms / p95 1.09 ms | `reports/ml_report/model_comparison_report.json` `models.M3_lightgbm_tabular.latency_*` | `ml/training/train_phase2_models.py` (latency block) | `python -m ml.training.train_phase2_models` |
| §4.3 M4 p50 0.78 ms / p95 1.10 ms | `reports/ml_report/model_comparison_report.json` `models.M4_lightgbm_plus_graph.latency_*` | same | same |

## 4. Soundbox benchmark

| Claim | Source JSON | Source script | Regenerate |
|---|---|---|---|
| §8 / §16 soundbox p50 27.969 ms | `reports/soundbox_report/soundbox_latency_benchmark.json` `pcm_audio_waveform_synthesis.median_p50_ms` | `scripts/bench_soundbox_empirical.py` | `python -m scripts.bench_soundbox_empirical` |
| 3.33x speedup vs. visual glance | same JSON `human_cognitive_confirmation_advantage.speed_advantage_multiplier` | same | same |

## 5. Live API endpoints that surface the JSON to the UI

| Endpoint | Source it returns | File |
|---|---|---|
| `GET /api/v1/evidence/benchmarks` | Union of all six JSONs above | `backend/app/api/v1/endpoints/evidence.py` |
| `POST /api/v1/evidence/simulate-impact` | Re-runs `financial_impact_simulator.py`, returns the JSON | same |
| `GET /api/v1/governance/active-model` | One row of `model_governance_registry` (DB) | `backend/app/api/v1/endpoints/governance.py` |
| `POST /api/v1/governance/rollback` | Flips active model, appends to `immutable_security_audit` | same |
| `POST /api/v1/security/attack-suite/run` | Runs `BadgeService.run_attack_suite`, appends to `immutable_security_audit` | `backend/app/api/v1/endpoints/security.py` |

The frontend dashboard (`frontend/src/components/RiskConsole.tsx`) calls the
evidence endpoint on mount and renders the 6 scorecards from the response. If
the fetch fails the scorecards fall back to the last-known JSON values to
preserve offline demo behaviour.

## 6. Tests that lock the wiring down

| Test | What it locks | File |
|---|---|---|
| `test_evidence_benchmarks_endpoint` | `/api/v1/evidence/benchmarks` returns the merged payload | `backend/tests/test_phase2_wiring.py` |
| `test_governance_active_model_endpoint` | seeded registry row is returned | same |
| `test_governance_rollback_requires_super_admin` | non-admin gets 403 | same |
| `test_attack_suite_endpoint_runs_four_attacks` | `/api/v1/security/attack-suite/run` returns `passed == 4` | same |
| `test_immutable_security_audit_chain` | record_hash chain is consistent | same |

The pre-existing 44 backend tests in `backend/tests/` continue to cover the
rest of the system (transaction pipeline, freeze, soundbox, fraud, appeals,
concurrency, etc.).

## 7. Phase-1 baseline (frozen, immutable) — for the record

| Claim | Source |
|---|---|
| Phase-1 ROC-AUC 1.0000 (acknowledged as target-leakage-inflated) | `phase1-baseline/metrics/risk_metrics_p1.json` |
| Phase-1 38/38 tests | `phase1-baseline/test-results/pytest_p1_results.txt` |
| Phase-1 inference p50 1.37 ms / p95 1.72 ms | `phase1-baseline/metrics/risk_metrics_p1.json` |
| Phase-1 freeze SLA 12.4 ms, graph 42.1 ms, nonce 14.6 ms | `phase1-baseline/README.md` |

Phase-1 is preserved for transparency; the Phase-2 numbers above are the
authoritative ones for the current submission.