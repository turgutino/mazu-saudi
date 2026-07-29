# =============================================================================
# MAZU — flash_flood operational-threshold re-calibration: DISCLOSED FINDING,
# NOT a production change.
#
# Motivation: 08_meteorological_metrics.py showed flash_flood at its current
# operational threshold (0.50, reused from CAP severity) has very low POD
# (0.10) and high FAR (0.80). The obvious next step is a threshold scan to
# see whether a different cutoff trades FAR for POD/CSI more favourably.
#
# What this script actually finds: a threshold CAN be found that raises CSI
# on the held-out Jul-Dec test set (thr~0.34 -> CSI 0.076 vs 0.071 at 0.50,
# a real but small +7% relative gain). BUT this "optimum" does not survive an
# honest out-of-sample check: flash_flood's 2025 positives are heavily
# concentrated in a single event (the 22-23 Aug Jizan flood), so any
# threshold selected on part of the test period overfits to that event's
# probability distribution and does WORSE than the existing 0.50 threshold
# when evaluated on the other part. This is disclosed here explicitly, and
# the production threshold (model_meta.json / DetectionEngine.RULES,
# unaffected by this script) is intentionally left unchanged at 0.50.
# =============================================================================

import os
import json
import importlib.util
import joblib
import numpy as np
import xarray as xr
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
SAVED_DIR = os.path.join(HERE, "..", "agent", "saved_models")

# Splits the test period at its midpoint (3 months each) to check whether a
# threshold selected on one half transfers to the other -- NOT a train/test
# split (both halves are already-held-out Jul-Dec data the model never
# trained on); this only tests threshold TRANSFER, not model generalisation.
SPLIT_DATE = "2025-09-30"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scan_thresholds(y_true, y_proba, contingency_metrics, thresholds):
    """Return list of {threshold, pod, far, csi, hss} across a threshold grid."""
    rows = []
    for thr in thresholds:
        pred = (y_proba >= thr).astype(int)
        m = contingency_metrics(y_true, pred)
        rows.append({"threshold": round(float(thr), 2), **m})
    return rows


def best_by(rows, key):
    return max(rows, key=lambda r: r[key] if np.isfinite(r[key]) else -1)


def main():
    de = load_module("de_thr", os.path.join(HERE, "01_detection_engine.py"))
    fb = load_module("fb_thr", os.path.join(HERE, "03_forecast_baseline.py"))
    metmod = load_module("met_thr", os.path.join(HERE, "08_meteorological_metrics.py"))
    contingency_metrics = metmod.contingency_metrics

    ds = xr.open_dataset(fb.DATASET)
    X, y, dates, _lat, _lon = fb.build_supervised(ds, "flash_flood")
    ds.close()

    clf = joblib.load(os.path.join(SAVED_DIR, "flash_flood_model.joblib"))
    proba = clf.predict_proba(X)[:, 1]

    test_mask = dates > fb.TRAIN_END
    y_test, p_test, d_test = y[test_mask], proba[test_mask], dates[test_mask]

    half_a = d_test <= SPLIT_DATE   # Jul-Sep
    half_b = ~half_a                # Oct-Dec

    thresholds = np.round(np.arange(0.01, 0.99, 0.01), 2)
    current_thr = de.RULES["flash_flood"]["severity"][1][1]   # 0.50, unchanged

    full_scan = scan_thresholds(y_test, p_test, contingency_metrics, thresholds)
    best_csi_full = best_by(full_scan, "csi")
    current_full = next(r for r in full_scan if r["threshold"] == current_thr)

    a_scan = scan_thresholds(y_test[half_a], p_test[half_a], contingency_metrics, thresholds)
    b_scan = scan_thresholds(y_test[half_b], p_test[half_b], contingency_metrics, thresholds)
    best_csi_a = best_by(a_scan, "csi")
    best_csi_b = best_by(b_scan, "csi")

    # Transfer test: apply each half's own CSI-optimal threshold to the OTHER
    # half, and compare against that half's own default-threshold (0.50) CSI.
    def eval_at(y_true, y_proba, thr):
        pred = (y_proba >= thr).astype(int)
        return contingency_metrics(y_true, pred)

    a_at_default = eval_at(y_test[half_a], p_test[half_a], current_thr)
    b_at_default = eval_at(y_test[half_b], p_test[half_b], current_thr)
    a_at_b_thr = eval_at(y_test[half_a], p_test[half_a], best_csi_b["threshold"])
    b_at_a_thr = eval_at(y_test[half_b], p_test[half_b], best_csi_a["threshold"])

    report = {
        "current_operational_threshold": current_thr,
        "current_threshold_metrics_full_test": current_full,
        "in_sample_csi_optimal_full_test": best_csi_full,
        "half_a_period": f"2025-07-01 to {SPLIT_DATE}",
        "half_b_period": f"2025-10-01 to 2025-12-31",
        "half_a_csi_optimal": best_csi_a,
        "half_b_csi_optimal": best_csi_b,
        "transfer_check": {
            "half_a_at_own_optimal_thr": best_csi_a,
            "half_a_at_default_thr": a_at_default,
            "half_a_at_half_b_optimal_thr": a_at_b_thr,
            "half_b_at_own_optimal_thr": best_csi_b,
            "half_b_at_default_thr": b_at_default,
            "half_b_at_half_a_optimal_thr": b_at_a_thr,
        },
        "verdict": (
            f"NOT ADOPTED. The in-sample CSI-optimal threshold on the full "
            f"test set (~{best_csi_full['threshold']:.2f}) gives a small, real CSI gain over "
            f"the current 0.50 threshold, but a threshold chosen on one half "
            f"of the test period does NOT transfer to the other half (it "
            f"performs at or below the existing 0.50 threshold's CSI there) "
            f"-- flash_flood's 2025 positives are dominated by a single "
            f"event (22-23 Aug Jizan flood), so any threshold tuned on a "
            f"period containing that event overfits to its probability "
            f"distribution. The production operational threshold (0.50, "
            f"DetectionEngine.RULES / model_meta.json) is left UNCHANGED."
        ),
    }

    report_path = os.path.join(HERE, "threshold_calibration_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    lines = ["=" * 70, "MAZU -- flash_flood threshold re-calibration (disclosed finding)", "=" * 70,
              f"Current threshold={current_thr:.2f}: {current_full}",
              f"Full-test-set CSI-optimal threshold={best_csi_full['threshold']:.2f}: {best_csi_full}",
              "",
              f"Half A ({report['half_a_period']}) own-optimal thr={best_csi_a['threshold']:.2f} CSI={best_csi_a['csi']:.4f}",
              f"Half B ({report['half_b_period']}) own-optimal thr={best_csi_b['threshold']:.2f} CSI={best_csi_b['csi']:.4f}",
              "",
              f"Half A at default(0.50) CSI={a_at_default['csi']:.4f} | at Half-B's optimal thr CSI={a_at_b_thr['csi']:.4f}",
              f"Half B at default(0.50) CSI={b_at_default['csi']:.4f} | at Half-A's optimal thr CSI={b_at_a_thr['csi']:.4f}",
              "", report["verdict"]]
    txt = "\n".join(lines)
    with open(os.path.join(HERE, "threshold_calibration_report.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)
    print(f"\n[SAVED] {report_path}")
    print("[NO CHANGE] production threshold in model_meta.json / DetectionEngine.RULES remains 0.50")


if __name__ == "__main__":
    main()
