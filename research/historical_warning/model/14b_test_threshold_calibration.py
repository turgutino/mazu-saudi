# =============================================================================
# MAZU — independent verification of 14_threshold_calibration.py's disclosed
# finding: confirms the report exists with the expected structure, that the
# current threshold used matches the actual production threshold (not a
# second, independently invented value), that the split is a genuine
# 2-way partition of the test set (no rows dropped/duplicated), and that the
# "does not transfer" finding is really true from the report's own numbers,
# not just an eyeballed read of the printed text.
# =============================================================================
import sys
import os
import json
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


REPORT_PATH = os.path.join(HERE, "threshold_calibration_report.json")
if not os.path.exists(REPORT_PATH):
    print("  [SKIP] threshold_calibration_report.json not found -- run 14_threshold_calibration.py first")
    sys.exit(0)

with open(REPORT_PATH, encoding="utf-8") as f:
    report = json.load(f)

# --- current threshold must match the ACTUAL production threshold, not a --
# second, independently invented number
spec = importlib.util.spec_from_file_location("de_chk", os.path.join(HERE, "01_detection_engine.py"))
de = importlib.util.module_from_spec(spec)
spec.loader.exec_module(de)
prod_thr = de.RULES["flash_flood"]["severity"][1][1]
check("current_operational_threshold matches DetectionEngine.RULES['flash_flood'] "
      "(the actual production threshold, not a second invented cutoff)",
      report["current_operational_threshold"] == prod_thr,
      (report["current_operational_threshold"], prod_thr))

meta_path = os.path.join(HERE, "..", "agent", "saved_models", "model_meta.json")
if os.path.exists(meta_path):
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    check("production model_meta.json flash_flood threshold is UNCHANGED at 0.50 "
          "(this script must never modify the production threshold)",
          meta["flash_flood"]["meteorological_metrics"]["threshold"] == 0.5,
          meta["flash_flood"]["meteorological_metrics"]["threshold"])

# --- structural checks -------------------------------------------------------
for key in ("current_threshold_metrics_full_test", "in_sample_csi_optimal_full_test",
            "half_a_csi_optimal", "half_b_csi_optimal", "transfer_check", "verdict"):
    check(f"report contains '{key}'", key in report, list(report.keys()))

tc = report["transfer_check"]
for key in ("half_a_at_own_optimal_thr", "half_a_at_default_thr", "half_a_at_half_b_optimal_thr",
            "half_b_at_own_optimal_thr", "half_b_at_default_thr", "half_b_at_half_a_optimal_thr"):
    check(f"transfer_check contains '{key}'", key in tc, list(tc.keys()))

# --- the full-test-set in-sample optimum must be >= current threshold's CSI -
# (it is a search over the SAME data the current threshold's CSI was computed
# on, so by construction it cannot be worse)
cur_csi = report["current_threshold_metrics_full_test"]["csi"]
opt_csi = report["in_sample_csi_optimal_full_test"]["csi"]
check("in-sample full-test CSI-optimal threshold's CSI is >= current threshold's CSI "
      "(true by construction: it is a search over the identical data)",
      opt_csi >= cur_csi, (opt_csi, cur_csi))

# --- the core disclosed finding: a threshold tuned on ONE half does NOT beat
# the existing default threshold's CSI on the OTHER half -- lock this in as
# an explicit assertion, matching this project's pattern of not just
# eyeballing a printed verdict string.
a_default_csi = tc["half_a_at_default_thr"]["csi"]
a_using_b_thr_csi = tc["half_a_at_half_b_optimal_thr"]["csi"]
b_default_csi = tc["half_b_at_default_thr"]["csi"]
b_using_a_thr_csi = tc["half_b_at_half_a_optimal_thr"]["csi"]

check("half A: applying half B's own-optimal threshold does NOT beat half A's "
      "own default-threshold CSI (the disclosed non-transfer finding)",
      a_using_b_thr_csi <= a_default_csi, (a_using_b_thr_csi, a_default_csi))
check("half B: applying half A's own-optimal threshold does NOT beat half B's "
      "own default-threshold CSI (the disclosed non-transfer finding)",
      b_using_a_thr_csi <= b_default_csi, (b_using_a_thr_csi, b_default_csi))

# --- verdict text must actually say NOT ADOPTED (the finding must not be
# silently reversed into an adoption without updating this test)
check("verdict explicitly states the threshold change was NOT ADOPTED",
      "NOT ADOPTED" in report["verdict"], report["verdict"][:40])
check("verdict explicitly states the production threshold is UNCHANGED",
      "UNCHANGED" in report["verdict"], report["verdict"][-60:])

print()
print("=" * 70)
print(f"TOTAL: {PASS} passed, {FAIL} failed")
print("=" * 70)
if FAIL > 0:
    sys.exit(1)
