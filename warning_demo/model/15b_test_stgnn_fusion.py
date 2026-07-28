# =============================================================================
# MAZU -- independent verification of 15_stgnn_fusion.py's disclosed finding:
# confirms the report exists with the expected structure, that the baseline-
# only row (weight=0.0) is really identical to the production baseline model
# (not a second, independently invented number), that the CSI-optimal
# in-sample fusion weight is at least as good as baseline-only on the SAME
# data (true by construction), and that the "does not transfer" verdict is
# really true from the report's own numbers, not just an eyeballed read of
# the printed text.
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


REPORT_PATH = os.path.join(HERE, "stgnn_fusion_report.json")
if not os.path.exists(REPORT_PATH):
    print("  [SKIP] stgnn_fusion_report.json not found -- run 15_stgnn_fusion.py first")
    sys.exit(0)

with open(REPORT_PATH, encoding="utf-8") as f:
    report = json.load(f)

# --- current threshold must match the ACTUAL production threshold ----------
spec = importlib.util.spec_from_file_location("de_chk2", os.path.join(HERE, "01_detection_engine.py"))
de = importlib.util.module_from_spec(spec)
spec.loader.exec_module(de)
prod_thr = de.RULES["flash_flood"]["severity"][1][1]
check("current_operational_threshold matches DetectionEngine.RULES['flash_flood'] "
      "(the actual production threshold, not a second invented cutoff)",
      report["current_operational_threshold"] == prod_thr,
      (report["current_operational_threshold"], prod_thr))

# --- baseline-only row (weight=0.0) must match the ALREADY-VERIFIED --------
# meteorological metrics report for flash_flood at the same threshold, not a
# second independently-computed number.
met_path = os.path.join(HERE, "meteorological_metrics_report.txt")
baseline = report["baseline_only_full_test"]
check("baseline_only_full_test uses weight=0.0 (pure baseline, no STGNN contribution)",
      baseline["weight"] == 0.0, baseline["weight"])
if os.path.exists(met_path):
    with open(met_path, encoding="utf-8") as f:
        met_txt = f.read()
    # meteorological_metrics_report.txt reports POD/FAR/CSI/HSS for flash_flood
    # at the SAME 0.50 threshold -- pull its CSI line and cross-check.
    section = met_txt.split("--- flash_flood")[1].split("--- ")[0] if "--- flash_flood" in met_txt else ""
    check("meteorological_metrics_report.txt contains a flash_flood CSI figure to cross-check against",
          "CSI=" in section, section[:80])
    if "CSI=" in section:
        reported_csi = float(section.split("CSI=")[1].split()[0])
        check("baseline_only_full_test CSI matches the independently-generated "
              "meteorological_metrics_report.txt CSI for flash_flood (same model, same threshold)",
              abs(baseline["csi"] - reported_csi) < 1e-3, (baseline["csi"], reported_csi))

# --- structural checks -------------------------------------------------------
for key in ("baseline_only_full_test", "in_sample_csi_optimal_fusion_full_test",
            "half_a_csi_optimal", "half_b_csi_optimal", "transfer_check", "adopted", "verdict"):
    check(f"report contains '{key}'", key in report, list(report.keys()))

tc = report["transfer_check"]
for key in ("half_a_at_baseline_only", "half_a_at_half_b_optimal_weight",
            "half_b_at_baseline_only", "half_b_at_half_a_optimal_weight"):
    check(f"transfer_check contains '{key}'", key in tc, list(tc.keys()))

# --- the full-test-set in-sample fusion optimum must be >= baseline-only's --
# CSI (true by construction: weight=0.0 is itself one of the scanned points)
opt = report["in_sample_csi_optimal_fusion_full_test"]
check("in-sample full-test CSI-optimal fusion weight's CSI is >= baseline-only's CSI "
      "(true by construction: w=0.0 is one of the scanned grid points)",
      opt["csi"] >= baseline["csi"], (opt["csi"], baseline["csi"]))

# --- adopted flag must be internally consistent with the transfer numbers --
a_base = tc["half_a_at_baseline_only"]["csi"]
a_b_w = tc["half_a_at_half_b_optimal_weight"]["csi"]
b_base = tc["half_b_at_baseline_only"]["csi"]
b_a_w = tc["half_b_at_half_a_optimal_weight"]["csi"]
transfers = (a_b_w > a_base) and (b_a_w > b_base)
check("'adopted' flag is internally consistent with the transfer_check numbers "
      "(adopted only if BOTH halves improve over baseline-only under the OTHER half's weight)",
      report["adopted"] == (transfers and opt["weight"] > 0.0),
      (report["adopted"], transfers, opt["weight"]))

# --- given this run's actual numbers, the finding is a non-transfer (as of --
# the run that produced this report) -- assert directionally rather than
# hardcoding today's exact CSI values, so this test stays valid if the STGNN
# (retrained fresh each run, no fixed checkpoint) varies slightly next run.
if not report["adopted"]:
    check("verdict explicitly states the fusion was NOT ADOPTED",
          "NOT ADOPTED" in report["verdict"], report["verdict"][:40])
    check("verdict explicitly states the production model is UNCHANGED",
          "UNCHANGED" in report["verdict"], report["verdict"][-80:])
else:
    check("verdict explicitly states the fusion was ADOPTED",
          report["verdict"].startswith("ADOPTED"), report["verdict"][:40])

print()
print("=" * 70)
print(f"TOTAL: {PASS} passed, {FAIL} failed")
print("=" * 70)
if FAIL > 0:
    sys.exit(1)
