import { describe, expect, it } from "vitest";
import {
  consistencyLabel,
  evidenceBoundary,
  evidenceStatusLabel,
  indicatorLabel,
  mechanismDescription,
  mechanismLabel,
  reportKindLabel,
  riskLevelLabel,
} from "./i18n";

describe("domain localization", () => {
  it("localizes model output vocabulary without changing machine identifiers", () => {
    expect(riskLevelLabel("zh", "emergency")).toBe("紧急风险");
    expect(riskLevelLabel("en", "emergency")).toBe("Emergency");
    expect(consistencyLabel("zh", "model_higher_than_detection")).toBe("模型高于规则");
    expect(consistencyLabel("en", "model_higher_than_detection")).toBe("Model higher than rules");
    expect(indicatorLabel("zh", "tmax_c")).toBe("日最高气温");
    expect(indicatorLabel("en", "tmax_c")).toBe("Daily maximum temperature");
  });

  it("localizes evidence vocabulary and preserves the English source text in English mode", () => {
    const original = "Subtropical / continental high (heat dome)";
    expect(mechanismLabel("zh", "subtropical_high")).toBe("副热带高压");
    expect(mechanismDescription("zh", "subtropical_high", original)).not.toContain("heat dome");
    expect(mechanismDescription("en", "subtropical_high", original)).toBe(original);
    expect(evidenceStatusLabel("zh", "needs_source_review")).toBe("待人工核验");
    expect(evidenceBoundary("zh", "Explanation only.")).toContain("不参与模型训练");
  });

  it("localizes report metadata", () => {
    expect(reportKindLabel("zh", "verification")).toBe("核验报告");
    expect(reportKindLabel("en", "verification")).toBe("Verification report");
  });
});
