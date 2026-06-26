# Output Template

## 1. Summary Table (review / influence / systematic-review mode)

| # | Authors | Year | Title | Venue | DOI | Type | Citations | Influential | OA | Source | Main contribution |
|---|---|---|---|---|---|---|---|---|---|---|---|

Notes:
- **Citations** is `cited_by_count` (OpenAlex/EPMC max).
- **Influential** is Semantic Scholar `influentialCitationCount` — show "—" when missing.
- **OA** is a clickable link to the open-access copy if `is_oa = true`, otherwise `—`.
- Prefix the row with `⚠ RETRACTED` if `is_retracted = true` and link the retraction notice DOI in the *Main contribution* column.

## 2. Search Audit Trail

```text
Original query (user):     ...
Normalized English query:  ...
Expanded keywords:         ...
Date range:                ...
Ranking mode:              ...
Databases searched:        OpenAlex, Crossref, Semantic Scholar, PubMed, Europe PMC, ...
Initial hits per source:   { OpenAlex: 25, Crossref: 22, ... }
Deduplicated count:        ...
Final included papers:     ...
Records flagged retracted: ...
Access limitations:        ...
```

## 3. Key Trends

Write 3–5 paragraphs on the main directions in the literature. Cite specific papers from the table using `[#N]` (row number) so the reader can trace each claim.

## 4. Top 3 Influential Papers

For each paper, explain:

- why it matters
- what it changed in the field
- why it ranks above the rest

## 5. Open Questions / Gaps

List recurring unresolved issues, conflicting findings, and bottlenecks.

## 6. Recommended First Reading

Pick 3 papers and explain why they are the best entry point — usually:

1. The strongest recent review or systematic review.
2. The most influential original paper still relevant.
3. The most recent paper with a fresh angle.

## 7. Optional Exports

If the user asked for export, append the files at the end of the response:

- `reading.bib` — BibTeX, ready for Zotero / Mendeley / LaTeX.
- `reading.ris` — RIS, ready for EndNote.
- `reading.csv` — CSV with all canonical fields, ready for Excel / Sheets.

---

## Compact newest-first format

Use this when the user asks for the latest papers rather than a full review:

| # | Date | Title | First author | Venue | DOI | Type | Source | OA |
|---|---|---|---|---|---|---|---|---|

Add the audit trail (Section 2) below; skip Sections 3–6 unless asked.

---

## Bulgarian-output guidance

When the final answer is in Bulgarian:

- Keep titles, DOI, venue, and author names in the original language (almost always English).
- Translate the **narrative sections** (Key Trends, Top 3, Open Questions, Recommended First Reading) into Bulgarian.
- Use `недостъпно` for missing fields.
- Keep the audit trail in English for traceability — it's a technical artifact.
