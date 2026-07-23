import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "docs" / "ai4science_manuscript"
MANUSCRIPT = PAPER_DIR / "cross_scale_regimes_draft.md"


def _section(text: str, start: str, end: str) -> str:
    pattern = rf"^## {re.escape(start)}\s*$\n(.*?)^## {re.escape(end)}\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    assert match, f"missing section boundary: {start} -> {end}"
    return match.group(1).strip()


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w–'-]+\b", text, flags=re.UNICODE))


def test_ai4science_title_abstract_and_result_placeholders():
    text = MANUSCRIPT.read_text(encoding="utf-8")
    title = text.splitlines()[0].removeprefix("# ")
    abstract = _section(text, "Abstract", "Introduction")
    tokens = set(re.findall(r"TODO-RESULT-AI4S-[A-Z0-9-]+", text))

    assert _word_count(title) <= 15
    assert _word_count(abstract) <= 200
    assert not re.search(r"\[[0-9,– -]+\]", abstract)
    assert len(tokens) >= 30


def test_ai4science_manuscript_is_science_first_and_complete():
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

    assert "Scientific-integrity notice" in text
    assert "do not by themselves establish a physical mechanism or causality" in text
    assert "AI as an event-discovery instrument" in text
    assert "not called a fundamental predictability limit" in text
    assert "no flood occurrence or impact claim" in text


def test_ai4science_claim_families_have_evidence_controls():
    text = MANUSCRIPT.read_text(encoding="utf-8")
    matrix = (PAPER_DIR / "claim_evidence_matrix.md").read_text(encoding="utf-8")

    for family in (
        "MORPH",
        "REGIME",
        "PHYS",
        "LOCAL",
        "ERROR",
        "PREDICT",
        "MAZU",
    ):
        assert f"TODO-RESULT-AI4S-{family}-" in text
        assert f"TODO-RESULT-AI4S-{family}-*" in matrix

    assert "Causal:** prohibited" in matrix
    assert "Exploratory results cannot be relabelled confirmatory" in matrix


def test_ai4science_experiment_plan_has_discovery_validation_separation():
    plan = (PAPER_DIR / "experiment_plan.md").read_text(encoding="utf-8")

    for experiment in range(7):
        assert f"## Experiment {experiment}:" in plan
    assert "Discovery years: 2001–2018" in plan
    assert "Confirmation years: 2019–2024" in plan
    assert "AI attribution alone never passes this gate" in plan
    assert "conditional association rather than causal effect" in plan
    assert "clusters reflect geography/product artifacts" in plan


def test_two_paper_portfolio_prevents_claim_overlap():
    portfolio = (ROOT / "docs" / "paper_portfolio.md").read_text(encoding="utf-8")

    assert "Paper A: computer-method and reliable-prediction track" in portfolio
    assert "Paper B: AI4Science mechanism-discovery track" in portfolio
    assert "same figure, result table or primary statistical comparison" in portfolio
    assert "Execute Paper B first" in portfolio
    assert (ROOT / "docs" / "manuscript" / "extreme_precipitation_draft.md").exists()
    assert MANUSCRIPT.exists()


def test_ai4science_local_links_and_bibliography():
    local_link = re.compile(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)")
    files = list(PAPER_DIR.glob("*.md")) + [ROOT / "docs" / "paper_portfolio.md"]
    for path in files:
        text = path.read_text(encoding="utf-8")
        for target in local_link.findall(text):
            clean_target = target.split("#", 1)[0]
            if clean_target:
                assert (path.parent / clean_target).exists(), f"broken link: {path}: {target}"

    bibliography = (PAPER_DIR / "references.bib").read_text(encoding="utf-8")
    assert bibliography.count("@") >= 15
    assert "10.1038/s43247-024-01633-y" in bibliography
    assert "10.1038/s43247-020-0003-0" in bibliography
    assert "10.5067/GPM/IMERG/3B-HH/07" in bibliography
    assert "TODO-REFERENCE-AI4S-" in bibliography
    assert bibliography.count("{") == bibliography.count("}")
