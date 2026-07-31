"""Generate first-pass insights and figures for Saudi regional weather outputs."""

from __future__ import annotations

import argparse
import calendar
import json
from datetime import datetime
from pathlib import Path

import numpy as np


DEFAULT_DATA_ROOT = Path("/Volumes/E/气象数据/saudi_region_output")
DEFAULT_OUTPUT_DIR = Path("analysis")
FILL_VALUE_ABS_LIMIT = 1.0e20


def is_clean_path(path: Path) -> bool:
    return not any(part.startswith("._") for part in Path(path).parts)


def clean_dirs(path: Path):
    if not path.exists():
        return []
    return sorted(child for child in path.iterdir() if child.is_dir() and is_clean_path(child))


def clean_files(path: Path, pattern: str):
    if not path.exists():
        return []
    return sorted(child for child in path.glob(pattern) if child.is_file() and is_clean_path(child))


def numeric_summary(values):
    arr = np.asarray(values)
    if not np.issubdtype(arr.dtype, np.number):
        return None
    arr = clean_numeric_array(arr)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return None
    return {
        "count": int(finite.size),
        "mean": float(np.nanmean(finite)),
        "min": float(np.nanmin(finite)),
        "p95": float(np.nanpercentile(finite, 95)),
        "max": float(np.nanmax(finite)),
    }


def clean_numeric_array(values):
    arr = np.asarray(values, dtype=float)
    return np.where(np.isfinite(arr) & (np.abs(arr) < FILL_VALUE_ABS_LIMIT), arr, np.nan)


def normalize_grid(values, lat, lon):
    arr = np.asarray(values)
    lat_count = len(lat)
    lon_count = len(lon)
    if arr.shape == (lat_count, lon_count):
        return arr
    if arr.shape == (lon_count, lat_count):
        return arr.T
    raise ValueError(f"Grid shape {arr.shape} does not match lat={lat_count}, lon={lon_count}")


def mean_number(values):
    summary = numeric_summary(values)
    return None if summary is None else summary["mean"]


def days_in_month(month):
    return calendar.monthrange(int(str(month)[:4]), int(str(month)[4:6]))[1]


def add_summary_fields(record, prefix, values, fields=("mean", "max")):
    summary = numeric_summary(values)
    if summary is None:
        return None
    for field in fields:
        record[f"{prefix}_{field}"] = summary[field]
    return summary


def safe_ratio(numerator, denominator, min_abs=1e-12):
    numerator = clean_numeric_array(numerator)
    denominator = clean_numeric_array(denominator)
    result = np.full(np.broadcast_shapes(numerator.shape, denominator.shape), np.nan, dtype=float)
    return np.divide(numerator, denominator, out=result, where=np.abs(denominator) > min_abs)


def first_file(path: Path, pattern: str):
    files = clean_files(path, pattern)
    return files[0] if files else None


def period_dirs(root: Path, dataset: str, width: int):
    dirs = []
    for child in clean_dirs(root / dataset):
        if child.name.isdigit() and len(child.name) == width:
            dirs.append(child)
    return dirs


def npz_periods(root: Path):
    paths = clean_files(root / "ds10_daily", "*/*.npz")
    periods = []
    for path in paths:
        period = path.stem.removeprefix("saudi_ds10_daily_")
        if period.isdigit() and len(period) == 8:
            periods.append(period)
    return sorted(set(periods))


def filter_periods(periods, start=None, end=None, limit=None):
    selected = sorted(set(periods))
    if start:
        selected = [period for period in selected if period >= start]
    if end:
        selected = [period for period in selected if period <= end]
    if limit is not None:
        selected = selected[:limit]
    return selected


def collect_analysis(data_root=DEFAULT_DATA_ROOT, start=None, end=None, limit_days=None):
    import xarray as xr

    root = Path(data_root)
    ds1_month_dirs = period_dirs(root, "ds1", 6)
    ds2_day_dirs = period_dirs(root, "ds2", 8)
    ds4_day_dirs = period_dirs(root, "ds4", 8)
    ds10_days = npz_periods(root)

    availability = {
        "ds1_months": len(ds1_month_dirs),
        "ds2_days": len(ds2_day_dirs),
        "ds4_days": len(ds4_day_dirs),
        "ds10_daily_days": len(ds10_days),
    }

    months = filter_periods((path.name for path in ds1_month_dirs), start[:6] if start else None, end[:6] if end else None)
    monthly_records = []
    for month in months:
        monthly_dir = root / "ds1" / month
        avg_path = first_file(monthly_dir, f"*MONTH_AVG*{month}.nc")
        acc_path = first_file(monthly_dir, f"*MONTH_ACC*{month}.nc")
        if avg_path is None and acc_path is None:
            continue
        record = {"period": month}
        if acc_path is not None:
            record["acc_source"] = str(acc_path)
            with xr.open_dataset(acc_path) as ds:
                if "tp" in ds:
                    add_summary_fields(record, "precip_total_mm", ds["tp"].values)
                    add_summary_fields(record, "precip_mmday", ds["tp"].values / days_in_month(month))
                if "acpcp" in ds:
                    add_summary_fields(record, "convective_precip_mm", ds["acpcp"].values, fields=("mean", "max"))
                if "ncpcp" in ds:
                    add_summary_fields(record, "large_scale_precip_mm", ds["ncpcp"].values, fields=("mean", "max"))
                if {"acpcp", "tp"}.issubset(ds):
                    ratio = safe_ratio(ds["acpcp"].values, ds["tp"].values)
                    add_summary_fields(record, "convective_precip_ratio", ratio, fields=("mean",))
        if avg_path is None:
            monthly_records.append(record)
            continue
        record["avg_source"] = str(avg_path)
        with xr.open_dataset(avg_path) as ds:
            if "prate" in ds:
                record.setdefault("avg_prate_source", str(avg_path))
                if "precip_mmday_mean" not in record:
                    add_summary_fields(record, "precip_mmday", ds["prate"].values * 86400.0)
            if {"cpr", "prate"}.issubset(ds):
                ratio = safe_ratio(ds["cpr"].values, ds["prate"].values)
                if "convective_precip_ratio_mean" not in record:
                    add_summary_fields(record, "convective_precip_ratio", ratio, fields=("mean",))
            if {"avg_ishf", "avg_slhtf"}.issubset(ds):
                ratio = safe_ratio(ds["avg_ishf"].values, ds["avg_slhtf"].values)
                add_summary_fields(record, "bowen_ratio", ratio, fields=("mean",))
        monthly_records.append(record)

    day_candidates = [path.name for path in ds2_day_dirs] + [path.name for path in ds4_day_dirs] + ds10_days
    days = filter_periods(day_candidates, start, end, limit_days)
    daily_records = []
    for day in days:
        month = day[:6]
        record = {"period": day}
        sfc_path = first_file(root / "ds2" / day, f"*DAY_SFC_{day}.nc")
        if sfc_path is not None:
            record["ds2_sfc_source"] = str(sfc_path)
            with xr.open_dataset(sfc_path) as ds:
                if "t2m" in ds:
                    summary = numeric_summary(ds["t2m"].values - 273.15)
                    if summary:
                        record["t2m_mean_c"] = summary["mean"]
                        record["t2m_max_c"] = summary["max"]
                if {"u10", "v10"}.issubset(ds):
                    wind = np.sqrt(ds["u10"].values ** 2 + ds["v10"].values ** 2)
                    summary = numeric_summary(wind)
                    if summary:
                        record["wind10_mean_ms"] = summary["mean"]
                        record["wind10_max_ms"] = summary["max"]
                if "r2" in ds:
                    summary = numeric_summary(ds["r2"].values)
                    if summary:
                        record["rh2_mean_pct"] = summary["mean"]

        acc_path = first_file(root / "ds2" / day, f"*DAY_ACC_{day}.nc")
        if acc_path is not None:
            record["ds2_acc_source"] = str(acc_path)
            with xr.open_dataset(acc_path) as ds:
                if "tp" in ds:
                    summary = numeric_summary(ds["tp"].values)
                    if summary:
                        record["tp_mean_mm"] = summary["mean"]
                        record["tp_max_mm"] = summary["max"]
                if "acpcp" in ds:
                    summary = numeric_summary(ds["acpcp"].values)
                    if summary:
                        record["convective_tp_mean_mm"] = summary["mean"]

        sst_values = []
        for sst_path in clean_files(root / "ds4" / day, "*.nc"):
            with xr.open_dataset(sst_path) as ds:
                if "analysed_sst" in ds:
                    values = ds["analysed_sst"].values
                    if np.nanmean(values) > 100.0:
                        values = values - 273.15
                    sst_values.append(values)
        if sst_values:
            summary = numeric_summary(np.asarray(sst_values))
            if summary:
                record["sst_mean_c"] = summary["mean"]

        ds10_path = root / "ds10_daily" / month / f"saudi_ds10_daily_{day}.npz"
        if ds10_path.exists() and is_clean_path(ds10_path):
            record["ds10_daily_source"] = str(ds10_path)
            with np.load(ds10_path) as data:
                lat = data["lat"] if "lat" in data.files else []
                lon = data["lon"] if "lon" in data.files else []
                if "daily_total" in data.files:
                    daily_total = normalize_grid(data["daily_total"], lat, lon)
                    summary = numeric_summary(daily_total)
                    if summary:
                        record["ds10_daily_total_mean_mm"] = summary["mean"]
                        record["ds10_daily_total_max_mm"] = summary["max"]
                if "max_1h" in data.files:
                    max_1h = normalize_grid(data["max_1h"], lat, lon)
                    summary = numeric_summary(max_1h)
                    if summary:
                        record["ds10_max_1h_mean_mm"] = summary["mean"]
                        record["ds10_max_1h_max_mm"] = summary["max"]
                if "source_files" in data.files:
                    record["ds10_source_file_count"] = int(np.asarray(data["source_files"]).size)
        if len(record) > 1:
            daily_records.append(record)

    extremes = {}
    hottest = max((r for r in daily_records if "t2m_mean_c" in r), key=lambda r: r["t2m_mean_c"], default=None)
    wettest = max((r for r in daily_records if "tp_mean_mm" in r), key=lambda r: r["tp_mean_mm"], default=None)
    ds10_wettest = max(
        (r for r in daily_records if "ds10_daily_total_mean_mm" in r),
        key=lambda r: r["ds10_daily_total_mean_mm"],
        default=None,
    )
    if hottest:
        extremes["hottest_day"] = {"period": hottest["period"], "value": hottest["t2m_mean_c"], "metric": "t2m_mean_c"}
    if wettest:
        extremes["wettest_day"] = {"period": wettest["period"], "value": wettest["tp_mean_mm"], "metric": "tp_mean_mm"}
    if ds10_wettest:
        extremes["satellite_wettest_day"] = {
            "period": ds10_wettest["period"],
            "value": ds10_wettest["ds10_daily_total_mean_mm"],
            "metric": "ds10_daily_total_mean_mm",
        }

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data_root": str(root),
        "availability": availability,
        "monthly_records": monthly_records,
        "daily_records": daily_records,
        "extremes": extremes,
    }


def generate_figures(analysis, output_dir):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = Path(output_dir)
    figures_dir = output / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    figure_paths = []

    availability = analysis["availability"]
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    ax.bar(list(availability), list(availability.values()), color=["#3877a8", "#d9853b", "#5f9d6e", "#9467bd"])
    ax.set_title("Saudi regional output availability")
    ax.set_ylabel("Periods available")
    ax.tick_params(axis="x", rotation=25)
    path = figures_dir / "data_availability.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    figure_paths.append(path)

    daily = analysis.get("daily_records", [])
    if daily:
        periods = [row["period"] for row in daily]
        fig, ax1 = plt.subplots(figsize=(10, 4.8), constrained_layout=True)
        if any("t2m_mean_c" in row for row in daily):
            ax1.plot(periods, [row.get("t2m_mean_c", np.nan) for row in daily], color="#c94f44", label="2m temperature mean (C)")
            ax1.set_ylabel("Temperature (C)")
        ax2 = ax1.twinx()
        if any("tp_mean_mm" in row for row in daily):
            ax2.bar(periods, [row.get("tp_mean_mm", 0.0) for row in daily], alpha=0.28, color="#337ab7", label="DS2 precipitation mean (mm)")
        if any("ds10_daily_total_mean_mm" in row for row in daily):
            ax2.plot(periods, [row.get("ds10_daily_total_mean_mm", np.nan) for row in daily], color="#235f8f", label="DS10 precipitation mean (mm)")
        ax2.set_ylabel("Precipitation (mm)")
        tick_step = max(1, len(periods) // 12)
        ax1.set_xticks(range(0, len(periods), tick_step))
        ax1.set_xticklabels(periods[::tick_step], rotation=35, ha="right")
        ax1.set_title("Daily heat and rainfall signals")
        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines + lines2, labels + labels2, loc="upper left", fontsize=8)
        path = figures_dir / "daily_timeseries.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        figure_paths.append(path)

    monthly = analysis.get("monthly_records", [])
    if monthly:
        periods = [row["period"] for row in monthly]
        fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
        ax.bar(periods, [row.get("precip_mmday_mean", np.nan) for row in monthly], color="#4c8f6f")
        ax.set_title("Monthly mean precipitation rate")
        ax.set_ylabel("mm/day")
        ax.tick_params(axis="x", rotation=35)
        path = figures_dir / "monthly_precipitation.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        figure_paths.append(path)

    spatial = make_spatial_figure(analysis, figures_dir)
    if spatial is not None:
        figure_paths.append(spatial)

    return figure_paths


def make_spatial_figure(analysis, figures_dir):
    import matplotlib.pyplot as plt
    import xarray as xr

    root = Path(analysis["data_root"])
    hottest = analysis.get("extremes", {}).get("hottest_day")
    wettest = analysis.get("extremes", {}).get("wettest_day")
    if not hottest and not wettest:
        return None

    panels = []
    if hottest:
        day = hottest["period"]
        path = first_file(root / "ds2" / day, f"*DAY_SFC_{day}.nc")
        if path is not None:
            with xr.open_dataset(path) as ds:
                if "t2m" in ds:
                    panels.append(("Hottest day 2m temperature (C)", clean_numeric_array(ds["t2m"].values) - 273.15, ds["latitude"].values, ds["longitude"].values))
    if wettest:
        day = wettest["period"]
        path = first_file(root / "ds2" / day, f"*DAY_ACC_{day}.nc")
        if path is not None:
            with xr.open_dataset(path) as ds:
                if "tp" in ds:
                    panels.append(("Wettest day total precipitation (mm)", clean_numeric_array(ds["tp"].values), ds["latitude"].values, ds["longitude"].values))
    if not panels:
        return None

    fig, axes = plt.subplots(1, len(panels), figsize=(6 * len(panels), 4.8), constrained_layout=True)
    if len(panels) == 1:
        axes = [axes]
    for ax, (title, values, lat, lon) in zip(axes, panels):
        grid = normalize_grid(values, lat, lon)
        image = ax.imshow(
            grid,
            origin="lower",
            extent=[float(np.nanmin(lon)), float(np.nanmax(lon)), float(np.nanmin(lat)), float(np.nanmax(lat))],
            aspect="auto",
            cmap="viridis",
        )
        ax.set_title(title)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        fig.colorbar(image, ax=ax, shrink=0.82)
    path = figures_dir / "extreme_day_maps.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def build_markdown_report(analysis, output_dir, figure_paths=None):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    figure_paths = figure_paths or []

    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    availability = analysis["availability"]
    extremes = analysis.get("extremes", {})
    monthly = analysis.get("monthly_records", [])
    daily = analysis.get("daily_records", [])

    hottest = extremes.get("hottest_day", {})
    wettest = extremes.get("wettest_day", {})
    sat_wettest = extremes.get("satellite_wettest_day", {})

    lines = [
        "# 沙特区域气象数据洞察分析报告",
        "",
        f"- 数据来源：`{analysis['data_root']}`",
        f"- 生成时间：`{analysis.get('generated_at', 'unknown')}`",
        f"- 月尺度样本：{availability.get('ds1_months', 0)} 个；日尺度样本：{availability.get('ds2_days', 0)} 天；SST 样本：{availability.get('ds4_days', 0)} 天；卫星降水日聚合：{availability.get('ds10_daily_days', 0)} 天。",
        "",
        "## 核心洞察",
        "",
    ]
    if hottest:
        lines.append(f"- 区域平均 2m 气温最高日为 **{hottest['period']}**，平均约 **{hottest['value']:.2f} C**。")
    if wettest:
        lines.append(f"- DS2 日累计降水区域平均最高日为 **{wettest['period']}**，平均约 **{wettest['value']:.2f} mm**。")
    if sat_wettest:
        lines.append(f"- DS10 卫星降水日聚合最高日为 **{sat_wettest['period']}**，区域平均约 **{sat_wettest['value']:.2f} mm**。")
    if monthly:
        wettest_month = max((r for r in monthly if "precip_mmday_mean" in r), key=lambda r: r["precip_mmday_mean"], default=None)
        if wettest_month:
            lines.append(f"- 月平均降水率最高月份为 **{wettest_month['period']}**，区域平均约 **{wettest_month['precip_mmday_mean']:.2f} mm/day**。")
        valid_precip_months = sum(1 for row in monthly if "precip_mmday_mean" in row)
        if valid_precip_months < len(monthly):
            lines.append(f"- DS1 月平均降水率共有 {valid_precip_months}/{len(monthly)} 个月存在有效数值，其余月份为缺测或填充值。")
    if not any([hottest, wettest, sat_wettest, monthly]):
        lines.append("- 当前可用数据不足以形成极值洞察，建议先检查裁剪输出是否完整。")

    lines.extend(["", "## 可视化", ""])
    for path in figure_paths:
        rel = Path(path).relative_to(output)
        title = rel.stem.replace("_", " ")
        lines.extend([f"![{title}]({rel.as_posix()})", ""])

    lines.extend(
        [
            "## 指标说明",
            "",
            "- `t2m_mean_c`：DS2 日地表 2 米气温，已从 K 转换为 C。",
            "- `tp_mean_mm`：DS2 日累计总降水，按裁剪区域求平均。",
            "- `ds10_daily_total_mean_mm`：DS10 高频卫星降水日聚合结果，脚本会跳过 `date`、`source_files` 等非数值字段。",
            "- `precip_mmday_mean`：DS1 月降水强度，优先按 `MONTH_ACC tp / 当月天数` 转换为 mm/day。",
            "",
            "## 数据质量提示",
            "",
            "- 本报告是初步洞察分析，重点用于快速识别时间变化、空间热点和数据覆盖情况。",
            "- 原目录中存在 macOS `._*` 元数据文件，分析过程已跳过。",
            "- 报告摘要同时写入 `summary.json`，便于后续自动化建模或仪表盘复用。",
        ]
    )

    report_path = output / "saudi_data_insights_report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT), help="Saudi regional output directory")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Analysis output directory")
    parser.add_argument("--start", help="Optional start period, YYYYMM or YYYYMMDD")
    parser.add_argument("--end", help="Optional end period, YYYYMM or YYYYMMDD")
    parser.add_argument("--limit-days", type=int, help="Limit daily analysis to the first N selected days")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    analysis = collect_analysis(args.data_root, start=args.start, end=args.end, limit_days=args.limit_days)
    figures = generate_figures(analysis, output_dir)
    report = build_markdown_report(analysis, output_dir, figures)
    print(report)


if __name__ == "__main__":
    main()
