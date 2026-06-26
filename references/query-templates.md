# Query Templates

The orchestrator uses these as guidance for building search strings. They are **suggestions**, not literal API queries — each source has its own filter syntax which the per-source script handles.

## Generic topic query

```text
("<core topic>" OR "<synonym 1>" OR "<synonym 2>")
AND ("<method>" OR "<device>" OR "<material>")
AND ("<outcome 1>" OR "<outcome 2>")
```

## Newest-papers query

```text
("<core topic>")
AND ("<outcome>" OR "<technical target>")
```

Use the per-API date filters and sort by publication date descending.

## Review-focused query

```text
("<core topic>")
AND ("review" OR "systematic review" OR "meta-analysis" OR "scoping review")
```

Crossref also supports `filter=type:review-article` and OpenAlex `filter=type:review`.

## Mechanism-focused query

```text
("<core topic>")
AND ("mechanism" OR "degradation" OR "stability" OR "kinetics" OR "transport")
```

## Economics / techno-economic query

```text
("<core topic>")
AND ("cost reduction" OR "techno-economic" OR "LCOH" OR "CAPEX" OR "OPEX" OR "levelized cost")
```

## Materials-focused query

```text
("<core topic>")
AND ("catalyst" OR "membrane" OR "electrode" OR "coating" OR "bipolar plate" OR "anode" OR "cathode")
```

## Clinical / biomedical query

```text
("<condition>")
AND ("<intervention>" OR "<drug>" OR "<biomarker>")
AND ("randomized" OR "clinical trial" OR "cohort" OR "case-control" OR "observational")
```

## ML / CS query

```text
("<task>")
AND ("<model family>" OR "transformer" OR "diffusion" OR "graph neural network")
AND ("benchmark" OR "SOTA" OR "ablation")
```

## Dataset / software discovery

```text
("<topic>")
AND ("dataset" OR "benchmark" OR "corpus" OR "open data" OR "software")
```

Route this primarily to DataCite and OpenAIRE.

## Exclusion pattern

```text
NOT ("editorial" OR "conference abstract" OR "book review" OR "news item" OR "letter to the editor" OR "erratum" OR "retraction")
```

Apply at the API level when the source supports type filters (Crossref, OpenAlex), and post-hoc on `article_type` for sources that don't.

## Multilingual normalization examples

### Hydrogen / electrolysis (built-in dictionary)

| Bulgarian input | Normalized English core | Expanded terms |
|---|---|---|
| статии за PEM електролиза и ефективност | PEM electrolysis efficiency | proton exchange membrane electrolysis · PEM water electrolysis · current density · energy efficiency |
| зелен водород себестойност | green hydrogen cost | renewable hydrogen · LCOH · CAPEX · OPEX · techno-economic |
| алкална електролиза катализатор | alkaline electrolysis catalyst | AWE · nickel · electrocatalyst · electrode |
| твърдо-оксидни горивни клетки | solid oxide fuel cells | SOFC · solid oxide electrolyzer · SOEC |

### Other domains (translated in conversation, passed via `--query`)

| Bulgarian input | English form to pass |
|---|---|
| мозъчно-машинни интерфейси | brain-computer interface neural prosthetics |
| големи езикови модели халюцинации | large language models hallucinations factuality |
| невроморфни изчисления | neuromorphic computing |
| фотоволтаични перовскитни клетки | perovskite photovoltaic solar cells |
| метилиране на ДНК и рак | DNA methylation cancer epigenetics |

For any BG topic outside the built-in dictionary, do the translation yourself and pass the English form explicitly. The audit trail still records the original BG.

## Expansion rules

- Expand abbreviations into full forms (PEM ↔ proton exchange membrane; LCOH ↔ levelized cost of hydrogen; SOTA ↔ state of the art).
- Expand common scientific synonyms.
- Add outcome terms that match the user intent (efficiency, cost, durability, accuracy).
- Keep the expansion small enough to remain on-topic — aim for ≤ 10 terms in the OR clause.
- Drop adjectives that don't add discriminative value ("novel", "recent", "modern", "advanced").
