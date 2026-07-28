# =============================================================================
# MAZU -- flash_flood-specific baseline+STGNN weighted-probability fusion.
#
# Motivation (stgnn_report.txt, honest verdict): the STGNN is NOT an
# unambiguous win -- it found a real, larger hotspot on the 22-23 Aug Jizan
# flash-flood event (2382/8800 cells >0.5 vs baseline's 35/8800) but also
# over-triggers on calm days and has worse PR-AUC (0.068 vs baseline 0.089).
# Rather than replacing the baseline with the GNN (rejected) or discarding
# the GNN's real Aug-23 signal entirely, this tests a per-cell weighted
# blend p_fused = w*p_stgnn + (1-w)*p_baseline, ONLY for flash_flood (heatwave
# already has a strictly-better neighbour-feature baseline, no GNN blend
# needed there -- see neighbor_feature_report.txt).
#
# Neither model is retrained/replaced in production by this script: it only
# reads the saved baseline model and retrains a fresh STGNN (no checkpoint
# exists) to evaluate a hypothetical fusion offline. Uses the SAME Half-A/
# Half-B transfer check as 14_threshold_calibration.py: a fusion weight that
# only helps in-sample is not adopted unless it also survives that check.
# =============================================================================

import os
import json
import importlib.util
import joblib
import numpy as np
import torch
import xarray as xr
from sklearn.metrics import roc_auc_score, average_precision_score
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
SAVED_DIR = os.path.join(HERE, "..", "agent", "saved_models")
SPLIT_DATE = "2025-09-30"   # same Jul-Sep / Oct-Dec split as 14_threshold_calibration.py
SEED = 42


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    de = load_module("de_fus", os.path.join(HERE, "01_detection_engine.py"))
    fb = load_module("fb_fus", os.path.join(HERE, "03_forecast_baseline.py"))
    metmod = load_module("met_fus", os.path.join(HERE, "08_meteorological_metrics.py"))
    stg = load_module("stg_fus", os.path.join(HERE, "05_stgnn.py"))
    contingency_metrics = metmod.contingency_metrics

    ds = xr.open_dataset(fb.DATASET)

    # -- baseline (already-saved production model, unchanged) --------------
    X2, y2, dates2, _lat2, _lon2 = fb.build_supervised(ds, "flash_flood")
    clf2 = joblib.load(os.path.join(SAVED_DIR, "flash_flood_model.joblib"))
    proba_base_all = clf2.predict_proba(X2)[:, 1]
    test_mask = dates2 > fb.TRAIN_END
    y_test, p_base_test, d_test = y2[test_mask], proba_base_all[test_mask], dates2[test_mask]

    # -- STGNN: retrain fresh (no saved checkpoint exists) ------------------
    lat, lon = ds.latitude.values, ds.longitude.values
    yi = np.arange(0, len(lat), stg.STRIDE); xi = np.arange(0, len(lon), stg.STRIDE)
    grid_shape = (len(yi), len(xi))
    edge_index = stg.build_grid_edges(*grid_shape).to(stg.DEVICE)
    print(f"Retraining STGNN for flash_flood (grid={grid_shape}, device={stg.DEVICE}) ...")
    r = stg.run_hazard(ds, "flash_flood", edge_index, grid_shape)
    print(f"Reproduced STGNN TEST ROC-AUC={r['roc']:.3f} PR-AUC={r['prauc']:.3f} "
          f"(report: ROC=0.919 PR-AUC=0.068 -- some run-to-run variation expected, no fixed checkpoint)")

    # -- align STGNN per-cell proba to the SAME rows as the baseline's ------
    # build_daily_frames() uses the identical yi/xi stride, meshgrid('ij'),
    # ravel() cell order and isfinite(y_next) validity mask as
    # fb.build_supervised(), so concatenating STGNN's per-date proba_by_date
    # (each length 8800) through the SAME valid mask, in the same ascending
    # date order, reproduces fb's exact row order -- verified below by an
    # exact label match, not assumed.
    frames, _ = stg.build_daily_frames(ds, "flash_flood")
    test_frames = [f for f in frames if f["date"] > fb.TRAIN_END]
    stgnn_rows, y_check, date_check = [], [], []
    for f in test_frames:
        valid = f["valid"]
        stgnn_rows.append(r["proba_by_date"][f["date"]][valid])
        y_check.append(f["y"][valid])
        date_check.append(np.full(valid.sum(), f["date"]))
    p_stgnn_test = np.concatenate(stgnn_rows)
    y_check = np.concatenate(y_check).astype(y_test.dtype)
    date_check = np.concatenate(date_check)
    ds.close()

    assert len(p_stgnn_test) == len(y_test), (len(p_stgnn_test), len(y_test))
    assert np.array_equal(y_check, y_test), "row alignment between STGNN and baseline test sets does not match"
    assert np.array_equal(date_check, d_test), "date alignment between STGNN and baseline test sets does not match"
    print(f"[OK] row alignment verified: {len(y_test):,} rows, labels and dates match exactly")

    current_thr = de.RULES["flash_flood"]["severity"][1][1]   # 0.50, unchanged
    half_a = d_test <= SPLIT_DATE
    half_b = ~half_a
    weights = np.round(np.arange(0.0, 1.01, 0.05), 2)

    def scan_weights(mask):
        rows = []
        for w in weights:
            p_fused = w * p_stgnn_test[mask] + (1 - w) * p_base_test[mask]
            pred = (p_fused >= current_thr).astype(int)
            m = contingency_metrics(y_test[mask], pred)
            rows.append({"weight": float(w), "roc_auc": float(roc_auc_score(y_test[mask], p_fused)),
                         "pr_auc": float(average_precision_score(y_test[mask], p_fused)), **m})
        return rows

    full_scan = scan_weights(np.ones_like(y_test, dtype=bool))
    best_csi_full = max(full_scan, key=lambda x: x["csi"])
    baseline_only = next(r2 for r2 in full_scan if r2["weight"] == 0.0)

    a_scan = scan_weights(half_a)
    b_scan = scan_weights(half_b)
    best_csi_a = max(a_scan, key=lambda x: x["csi"])
    best_csi_b = max(b_scan, key=lambda x: x["csi"])

    def eval_at(mask, w):
        p_fused = w * p_stgnn_test[mask] + (1 - w) * p_base_test[mask]
        pred = (p_fused >= current_thr).astype(int)
        return contingency_metrics(y_test[mask], pred)

    a_at_baseline = eval_at(half_a, 0.0)
    b_at_baseline = eval_at(half_b, 0.0)
    a_at_b_weight = eval_at(half_a, best_csi_b["weight"])
    b_at_a_weight = eval_at(half_b, best_csi_a["weight"])

    transfers = bool(a_at_b_weight["csi"] > a_at_baseline["csi"] and b_at_a_weight["csi"] > b_at_baseline["csi"])
    adopted = bool(transfers and best_csi_full["weight"] > 0.0)
    verdict = (
        f"{'ADOPTED' if adopted else 'NOT ADOPTED'}. Full-test-set CSI-optimal fusion weight "
        f"w={best_csi_full['weight']:.2f} gives CSI={best_csi_full['csi']:.4f} vs baseline-only "
        f"(w=0) CSI={baseline_only['csi']:.4f}. " +
        ("A weight tuned on one test half improves CSI on the OTHER half over baseline-only in "
         "both directions, so this fusion is judged robust and not an artifact of the single "
         "22-23 Aug Jizan event."
         if transfers else
         "A weight tuned on one test half does NOT improve (or performs at/below) baseline-only "
         "CSI on the OTHER half, matching the same non-transfer pattern found for pure threshold "
         "re-calibration (14_threshold_calibration.py) -- flash_flood's 2025 positives are "
         "dominated by the single 22-23 Aug Jizan event, so any weight tuned on a period "
         "containing it overfits to that event. The production model (flash_flood_model.joblib, "
         "no STGNN blend) is left UNCHANGED.")
    )

    report = {
        "current_operational_threshold": current_thr,
        "baseline_only_full_test": baseline_only,
        "in_sample_csi_optimal_fusion_full_test": best_csi_full,
        "half_a_period": f"2025-07-01 to {SPLIT_DATE}", "half_b_period": "2025-10-01 to 2025-12-31",
        "half_a_csi_optimal": best_csi_a, "half_b_csi_optimal": best_csi_b,
        "transfer_check": {
            "half_a_at_baseline_only": a_at_baseline, "half_a_at_half_b_optimal_weight": a_at_b_weight,
            "half_b_at_baseline_only": b_at_baseline, "half_b_at_half_a_optimal_weight": b_at_a_weight,
        },
        "adopted": adopted, "verdict": verdict,
    }
    report_path = os.path.join(HERE, "stgnn_fusion_report.json")
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    txt = "\n".join([
        "=" * 70, "MAZU -- flash_flood baseline+STGNN weighted fusion", "=" * 70,
        f"Baseline-only (w=0.0): {baseline_only}",
        f"In-sample CSI-optimal fusion weight={best_csi_full['weight']:.2f}: {best_csi_full}",
        "",
        f"Half A ({report['half_a_period']}) own-optimal w={best_csi_a['weight']:.2f} CSI={best_csi_a['csi']:.4f}",
        f"Half B ({report['half_b_period']}) own-optimal w={best_csi_b['weight']:.2f} CSI={best_csi_b['csi']:.4f}",
        "",
        f"Half A at baseline-only CSI={a_at_baseline['csi']:.4f} | at Half-B's optimal w CSI={a_at_b_weight['csi']:.4f}",
        f"Half B at baseline-only CSI={b_at_baseline['csi']:.4f} | at Half-A's optimal w CSI={b_at_a_weight['csi']:.4f}",
        "", verdict,
    ])
    with open(os.path.join(HERE, "stgnn_fusion_report.txt"), "w", encoding="utf-8") as fh:
        fh.write(txt)
    print("\n" + txt)
    print(f"\n[SAVED] {report_path}")
    print("[NO CHANGE] production flash_flood model / threshold unchanged")


if __name__ == "__main__":
    main()
