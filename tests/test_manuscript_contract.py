import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "docs" / "manuscript"
MANUSCRIPT = PAPER_DIR / "extreme_precipitation_draft.md"


def _section(text: str, start: str, end: str) -> str:
    pattern = rf"^## {re.escape(start)}\s*$\n(.*?)^## {re.escape(end)}\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    assert match, f"missing section boundary: {start} -> {end}"
    return match.group(1).strip()


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w–'-]+\b", text, flags=re.UNICODE))


def test_nature_communications_title_and_abstract_contract():
    text = MANUSCRIPT.read_text(encoding="utf-8")
    title = text.splitlines()[0].removeprefix("# ")
    abstract = _section(text, "Abstract", "Introduction")

    assert _word_count(title) <= 15
    assert _word_count(abstract) <= 200
    assert not re.search(r"\[[0-9,– -]+\]", abstract)
    assert "TODO-RESULT-" in abstract


def test_manuscript_has_required_sections_and_integrity_notice():
    text = MANUSCRIPT.read_text(encoding="utf-8")
    required = [
        "Abstract",
        "Introduction",
        "Results",
        "Discussion",
        "Methods",
        "Data availability",
        "Code availability",
        "References",
        "Author contributions",
        "Competing interests",
        "Figure legends",
    ]
    for heading in required:
        assert f"## {heading}" in text

    assert "Draft integrity notice" in text
    assert "No cross-regional MCR-Precip experiment has yet been completed" in text
    assert "cannot independently demonstrate cross-year generalization" in text
    assert "no flood occurrence or impact claim" in text


def test_result_placeholders_are_explicit_and_evidence_controlled():
    manuscript = MANUSCRIPT.read_text(encoding="utf-8")
    matrix = (PAPER_DIR / "claim_evidence_matrix.md").read_text(encoding="utf-8")
    tokens = set(re.findall(r"TODO-RESULT-[A-Z0-9-]+", manuscript))

    assert len(tokens) >= 40
    assert "Replacement rule" in matrix
    assert "experiment_manifest_id" in matrix
    for family in ("DATA", "OOD", "MCR", "CAL", "SELECTIVE", "CF"):
        assert any(token.startswith(f"TODO-RESULT-{family}-") for token in tokens)
        assert f"TODO-RESULT-{family}-*" in matrix


def test_paper_package_links_resolve():
    markdown_files = list(PAPER_DIR.glob("*.md"))
    local_link = re.compile(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)")

    for markdown_file in markdown_files:
        text = markdown_file.read_text(encoding="utf-8")
        for target in local_link.findall(text):
            clean_target = target.split("#", 1)[0]
            if clean_target:
                assert (markdown_file.parent / clean_target).exists(), (
                    f"broken link in {markdown_file}: {target}"
                )


def test_supplement_and_workplan_preserve_scientific_boundaries():
    supplement = (PAPER_DIR / "supplementary_methods.md").read_text(encoding="utf-8")
    workplan = (PAPER_DIR / "publication_workplan.md").read_text(encoding="utf-8")
    risks = (PAPER_DIR / "reviewer_risk_register.md").read_text(encoding="utf-8")

    for state in ("observed", "not_observed", "not_observable", "conflicting"):
        assert state in supplement
    assert "10/20/30 mm" in supplement
    assert "availability_time <= forecast_origin" in supplement
    assert "event_group_id" in supplement
    assert "At least three regions" in workplan
    assert "Do not call the uniform satellite reference “ground truth”" in risks


def test_working_bibliography_is_present_and_flagged_for_verification():
    bibliography = (PAPER_DIR / "references.bib").read_text(encoding="utf-8")

    assert bibliography.count("@") >= 20
    assert "10.5067/GPM/IMERG/3B-HH/07" in bibliography
    assert "10.1038/s41586-024-08252-9" in bibliography
    assert "TODO-REFERENCE-" in bibliography
    assert bibliography.count("{") == bibliography.count("}")
