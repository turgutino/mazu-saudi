# MAZU Layer 3 — Curated Literature Evidence Attachment

## What this layer does

The structural graph contains hand-authored mechanism mappings such as
`driven_by`. This layer attaches citation records and locally traceable
evidence passages to four of five mechanism nodes. It improves retrieval
traceability; it does not discover causality or prove every graph edge.

## Method

1. **Curated corpus (`corpus.py`)** — local paraphrases associated with cited
   publications, covering ARST, moisture transport, the subtropical high, and
   the summer Shamal/thermal low.
2. **Assisted extraction (`02_extract_causal.py`)** — DeepSeek reads one local
   passage at a time and proposes structured subject/relation/object records
   with a mandatory evidence string.
3. **Local-passage gate** — each evidence string must be an exact
   whitespace-normalised substring of the supplied local passage. This
   prevents the extractor from introducing wording outside its input.
4. **Manual quality screen** — one locally matched record was excluded because
   its framing was descriptive/circular rather than mechanistic.
5. **Evidence attachment (`03_merge_causal_kg.py`)** — accepted records are
   stored as metadata on Citation nodes. A `grounded_by` edge connects the
   corpus's preassigned mechanism tag to the citation.

## Verification boundary

The automatic gate checks against `corpus.py`, whose passages are curated
paraphrases. It does **not** check the wording against the original
publication. It also does not verify that:

- the extracted triple is the only valid interpretation of the passage;
- the publication supports every city-specific or hazard-specific graph edge;
- the assertion transfers to every Saudi location and date;
- the graph improves forecast accuracy.

Original-publication wording, source quality, geographic applicability, and
edge-level scientific validity remain human-review tasks. The graph exposes
this status through `source_text_kind`, `verification_scope`, `confidence`,
and `review_status`.

## Results

| Metric | Value |
|---|---|
| Candidate triples extracted | 21 |
| Matched to curated local passages | 21 / 21 |
| Passed manual quality screen | 20 / 21 |
| Citation nodes attached | 6 |
| `grounded_by` edges attached | 6 |
| Mechanisms with citation support | 4 / 5 |
| Mechanism still lacking citation support | `orographic_lift` |

The graph is regenerated from the current structural builder before this
attachment step. Current node/edge counts are reported by
`causal_kg_report.txt`, rather than frozen in this document.

## The excluded record

The Red Sea coast trend passage described temperature, wind, humidity, and
pressure trends as consistent with a warming/drying atmosphere. Although the
evidence string appeared in the local passage, treating that descriptive
framing as a causal mechanism would be circular. It was therefore excluded.

This example demonstrates why substring fidelity is necessary but not
sufficient for scientific validity.

## Files

```text
kg/causal/
  corpus.py                 curated local literature passages
  02_extract_causal.py      DeepSeek-assisted structured extraction
  causal_triples.json       locally matched extraction records
  extraction_report.txt     extraction audit log
  03_merge_causal_kg.py     attaches citation evidence to kg_data.json
  causal_kg_report.txt      evidence-attachment audit log
  LAYER3_REPORT.md          this verification-boundary report
```

## Security note

The DeepSeek API key used for extraction is stored in
`kg/causal/.deepseek_key`, excluded through `.gitignore`, and is not committed.
