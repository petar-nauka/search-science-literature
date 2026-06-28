# search-science-literature (v2)

Skill за намиране, валидиране, дедупликация, ранкиране и синтез на **рецензирана научна литература** през отворени академични API. Адаптация и подобрение на оригиналния Codex skill за **Claude Code** и **Claude.ai**.

---

## Какво се промени спрямо v1

| Промяна | Защо | Резултат |
|---|---|---|
| Преструктуриран в Claude skill формат с YAML frontmatter | За да се тригерира коректно от Claude | Готов за Claude Code и Claude.ai |
| Добавени 6 нови бази | По-широко покритие, особено за CS/физика/математика/preprints | Semantic Scholar, arXiv, DOAJ, bioRxiv/medRxiv, DataCite, DBLP |
| **Web of Science Starter API** | DOI/author/source-title validation и plan-dependent times-cited counts | Optional `--include-wos-starter` с `WOS_STARTER_API_KEY`, cache и 1 req/sec throttle |
| **OpenAlex abstract reconstruction** | v1 пропускаше абстрактите (бяха като inverted index) | Сега всеки OpenAlex запис има пълен текст на абстракт |
| **Crossref JATS stripping** | v1 връщаше абстракти с XML markup | Чист текст |
| **Retraction detection** | v1 не проверяваше за оттегляния | Crossref + OpenAlex cross-check + score penalty |
| **Influential citations + TLDR** | v1 нямаше тези Semantic Scholar сигнали | По-добро ранкиране, по-кратко резюме на статия |
| **Fuzzy title dedup** (SequenceMatcher ≥ 0.92) | v1 не сливаше леки разлики в заглавия | По-чисти финални таблици |
| **Venue tier boost** | v1 не отчиташе Nature/Science/Cell статус | По-точно `influence` ранкиране |
| **Systematic-review mode** | v1 нямаше този режим | `--sort systematic-review` за СР starter |
| **Per-source argv routing** | v1 имаше collision на флагове | Чисти, паралелни fan-out заявки |
| **ThreadPoolExecutor паралелизъм** | v1 беше sequential | 2-3× по-бързо за 5+ източника |
| **Export форматити** | v1 имаше само markdown table | BibTeX, RIS, CSV — готови за Zotero/EndNote/Excel |

## Структура

```
search-science-literature/
├── SKILL.md                    # Тригер + workflow + източници
├── README.md                   # този файл
├── references/                 # On-demand детайли
│   ├── search-workflow.md
│   ├── source-priority.md
│   ├── query-templates.md
│   ├── quality-rubric.md
│   ├── output-template.md
│   ├── api-notes.md
│   ├── field-mapping.md
│   ├── peer-review-policy.md
│   └── metric-policy.md
├── scripts/                    # Изпълними Python скриптове
│   ├── common.py               # абстракт reconstruction, fuzzy match, etc.
│   ├── search_orchestrator.py  # ГЛАВЕН entry point
│   ├── query_expand.py
│   ├── search_openalex.py      # + abstract reconstruction
│   ├── search_crossref.py      # + JATS stripping + retraction
│   ├── search_pubmed.py        # + NCBI_API_KEY
│   ├── search_europepmc.py     # + preprints filter
│   ├── search_semantic_scholar.py   # НОВО
│   ├── search_arxiv.py         # НОВО
│   ├── search_doaj.py          # НОВО
│   ├── search_biorxiv.py       # НОВО
│   ├── search_datacite.py      # НОВО
│   ├── search_dblp.py          # НОВО
│   ├── search_wos_starter.py   # WoS Starter API (optional key)
│   ├── search_core.py
│   ├── search_openaire.py
│   ├── enrich_unpaywall.py
│   ├── check_retractions.py    # НОВО
│   ├── validate_identifiers.py
│   ├── merge_dedup_rank.py     # + fuzzy + retraction penalty + venue tier
│   ├── build_review_table.py
│   ├── export_bibtex.py        # НОВО
│   ├── export_ris.py           # НОВО
│   └── export_csv.py           # НОВО
└── agents/
    └── openai.yaml             # запазен за обратна съвместимост с Codex
```

---

## Инсталация — Claude Code

1. Копирай папката `search-science-literature/` в `~/.claude/skills/` (или където проектът ти държи skills).
2. Може да настроиш env vars (опционално) в `.env`:
   ```
   OPENALEX_MAILTO=you@example.com
   CROSSREF_MAILTO=you@example.com
   UNPAYWALL_EMAIL=you@example.com
   SEMANTIC_SCHOLAR_API_KEY=...     # увеличава rate limit до ~10 req/sec
   NCBI_API_KEY=...                 # увеличава PubMed rate limit до 10 req/sec
   CORE_API_KEY=...                 # активира CORE търсене
   WOS_STARTER_API_KEY=...          # активира Web of Science Starter API
   ```
3. Готово. Claude ще тригерира skill-а автоматично за заявки като:
   - "Намери ми последните статии за PEM електролиза"
   - "State of the art on diffusion models text-to-image"
   - "Литературен преглед за CRISPR off-target effects"

## Инсталация — Claude.ai (Skills, beta)

1. Изтегли файла `search-science-literature.zip`.
2. В Claude.ai иди на **Settings → Capabilities → Skills**.
3. Натисни **Upload skill** и избери ZIP файла.
4. Активирай го за разговора.
5. Skill-ът сам ще се тригерира за научно-литературни заявки.

> Бележка: Claude.ai няма достъп до твоите env vars. Skill-ът работи без API ключове на shared pool, но е по-бавен (особено Semantic Scholar дава 429s без ключ). За най-добри резултати в Claude.ai използвай `--no-semantic-scholar` или предоставяй ключ през conversation context.

---

## Бързо тестване

```bash
# Пълен литературен преглед
python scripts/search_orchestrator.py \
    --query "PEM electrolysis efficiency" \
    --from-year 2023 --limit 20 \
    --sort influence \
    --include-arxiv --include-doaj \
    --check-retractions \
    --output review.json

# Експорт
python scripts/export_bibtex.py review.json --output review.bib
python scripts/export_csv.py review.json --output review.csv
python scripts/build_review_table.py review.json --mode review > review.md

# Optional Web of Science Starter enrichment
python scripts/search_orchestrator.py \
    --query "PEM electrolysis efficiency" \
    --from-year 2023 --limit 20 \
    --include-wos-starter \
    --output review_wos.json

# DOI validation through WoS Starter
python scripts/search_wos_starter.py --doi "10.1038/nphys1170" --pretty
```

---

## Подобрения и API ключове

Виж **[IMPROVEMENTS.md](IMPROVEMENTS.md)** за пълен план:
- ⏱️ кои безплатни API ключове да си вземеш (NCBI, CORE, Semantic Scholar, OpenAIRE)
- 🔗 директни линкове към регистрационните форми и колко време отнема всеки
- ➕ идеи за нови бази (ORCID, OpenCitations, Lens.org, Scite, CrossRef Event Data)
- ⚙️ pipeline подобрения (embedding re-ranking, citation graph expansion, full-text extraction, cache layer)

---

## Известни ограничения

- **Semantic Scholar без API ключ**: shared pool е силно rate-limited (HTTP 429). Препоръчвам да зададеш `SEMANTIC_SCHOLAR_API_KEY` или да деактивираш с `--no-semantic-scholar`.
- **arXiv**: 1 req / 3 sec. Скриптът sleep-ва автоматично.
- **CORE**: изисква `CORE_API_KEY`; иначе се пропуска.
- **Web of Science Starter API**: поддържа се само с `WOS_STARTER_API_KEY` и е изключен по подразбиране, защото Free Trial квотата е малка. `times cited` се показва само ако твоят план го връща.
- **Други paywalled бази** (Scopus, ScienceDirect, IEEE Xplore): не се обхождат — skill-ът ги декларира явно и продължава с отворените алтернативи.
- **Google Scholar**: НЕ се scrape-ва (TOS + bot detection). Не разчитай на него.

---

## Тестване след инсталация

Препоръчителен smoke test:

```bash
python scripts/search_orchestrator.py \
  --query "PEM electrolysis efficiency" \
  --from-year 2024 --limit 6 \
  --include-arxiv --include-doaj \
  --no-semantic-scholar \
  --output /tmp/smoke.json
```

Очаквано: 6 източника, 0 грешки, поне 30 hits, поне 1 dedup merge.

---

## Лиценз и атрибуции

- Оригинален Codex skill: автор Петър, април 2026.
- Адаптация и v2 подобрения: юни 2026.
- Скриптовете използват само открити API (без scraping). Виж `references/api-notes.md` за конкретните rate limits и TOS-и.
