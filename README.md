# DailyMed FDA drug-label sections (corpus mirror)

Section-split text mirror of **NIH DailyMed** structured product labels (SPL) —
the official provider of FDA drug label information (package inserts) — built as
reference-retrieval material for consumer medication questions: what a drug
treats, how to take it, warnings, interactions, side effects.

- Source list: <https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json>
  (pages 1–10, 100 per page; DailyMed DB published date of the snapshot:
  `Oct 02, 2026 07:38:48PM EST`, 159,390 SPLs total in the database)
- Label XML: `https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/<SETID>.xml`
- Downloaded: **2026-10-04 UTC**
- Scope: the **first 1,000 SPLs** of the current list (list endpoint default
  ordering, pages 1–10). No more was fetched. This is a bounded sample, not the
  whole database.
- Pin: the commit of this repository IS the snapshot; re-snapshotting is a new
  commit, never a force-push.

Source: National Library of Medicine.

## Shape

- One plain-text file per SPL `<section>` that carries a `<title>`
  (indications, warnings, dosage, interactions, adverse reactions, …),
  including nested subsections.
- Path: `<setid[0:2]>/<SETID>__<slugified-section-title>.txt`
  (two-hex-character shard of the setid — 245 directories, max 790 files in
  the largest — keeps every directory far below single-dir-at-scale while
  staying a flat two-level layout).
- Each file starts with one header line:
  `DailyMed <SETID> | <drug name(s)> | <section title>`
  where drug name(s) are the `<manufacturedProduct>/<name>` values of the
  label (the finished product names). If a section body was truncated, the
  header carries ` | [section truncated from N chars to fit 150KB]`.
- Body: the **verbatim** text content of the section's `<text>` element
  (XML tags stripped, whitespace normalised, table cells separated by ` | `).
  No paraphrase.
- Hard limits: labels with XML > 2 MB are skipped entirely (0 skipped in this
  snapshot); no output file exceeds 150 KB (1 file truncated).

## Counts (this snapshot)

| Metric | Value |
|---|---|
| Labels in list (pages 1–10) | 1,000 |
| Label XMLs fetched (HTTP 200) | 1,000 |
| Labels skipped (>2 MB XML) | 0 |
| Download failures | 0 |
| Output files | 18,729 |
| Files truncated at 150 KB | 1 |
| Largest file | 153,589 bytes |
| Distinct section titles | 4,965 |

Top-10 section titles by file count: Directions (407), Purpose (361),
Inactive ingredients (322), Uses (317), Warnings (298), Other information
(285), 11 DESCRIPTION (237), 12.1 Mechanism of Action (236), 8.4 Pediatric
Use (235), 8.5 Geriatric Use (230).

## Terms / copyright (verified 2026-10-04)

The DailyMed web-services documentation page
(<https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm>)
contains **no terms-of-use or copyright text of its own**; its footer links
"Copyright" to NLM copyright information. The statements that govern the data
are on the linked NLM pages, quoted verbatim:

NLM Web Policies — Copyright
(<https://www.nlm.nih.gov/web_policies.html>):

> **Attribution and Rights for Government Works:**
> Works produced by the U.S. government are not subject to copyright
> protection in the United States. Any such works found on National Library
> of Medicine (NLM) Web sites may be freely used or reproduced without
> permission in the U.S. Please acknowledge NLM as the source of the
> information by including the phrase "Courtesy of the National Library of
> Medicine" or "Source: National Library of Medicine."

NLM Data Distribution — Copyright Information & Downloading National Library
of Medicine Data (<https://www.nlm.nih.gov/databases/download.html>):

> The National Library of Medicine (NLM) data are produced by a U.S.
> Government agency and include works of the United States Government that
> are not protected by U.S. copyright law but may be protected by non-US
> copyright law, as well as abstracts originating from publications that may
> be protected by U.S. or non-US copyright law.

> Although a signed license agreement is not needed, users must ensure that
> all downloaded publicly accessible data must be in compliance with the
> following provisions of the NLM Terms and Conditions:
> Users of the data agree to: acknowledge NLM as the source of the data in a
> clear and conspicuous manner, not indicate or imply that NLM has endorsed
> its products/services/applications.
> Users who republish or redistribute the data (services, products or raw
> data) agree to: maintain the most current version of all distributed data,
> or make known in a clear and conspicuous manner that the
> products/services/applications do not reflect the most current/accurate
> data available from NLM.

About DailyMed (<https://dailymed.nlm.nih.gov/dailymed/about-dailymed.cfm>)
confirms provenance: the database "contains labeling, submitted to the Food
and Drug Administration (FDA) by companies" — i.e. the label text is
manufacturer-authored and NLM redistributes it.

Consequences, stated plainly:

- The label text is US-government-published and not protected by U.S.
  copyright law; it **may be protected by non-US copyright law**.
- **No LICENSE file is shipped with this mirror** because the applicable
  statements are the NLM terms above, not a licence we could assert.
- Attribution: this repository acknowledges NLM as the source
  ("Source: National Library of Medicine") and does not imply NLM
  endorsement of XERJ or anything else.
- This mirror is a pinned snapshot and **does not reflect the most current
  data available from NLM** (per the redistribution provision above); for
  current labels query DailyMed directly.

## Regeneration

```sh
mkdir -p listpages raw
for p in $(seq 1 10); do
  curl -sS -m 30 --retry 1 -o "listpages/page-$p.json" \
    "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?page=$p"
  sleep 4
done
jq -r '.data[].setid' listpages/page-*.json | sort -u > setids.txt
while read -r s; do
  [ -s "raw/$s.xml" ] && continue
  curl -sS -m 30 --retry 1 -o "raw/$s.xml" \
    "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/$s.xml"
  sleep 0.4
done < setids.txt
python3 tools/split_spl.py .        # writes <cc>/<SETID>__<slug>.txt + stats
```

`tools/split_spl.py` is the exact splitter that produced this snapshot
(standard library only).
