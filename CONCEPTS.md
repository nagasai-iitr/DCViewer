# DCViewer concepts

Plain definitions for the main objects the system stores and shows. These map 1:1 to Postgres tables (except where noted).

Inspect the live data with:

```bash
docker compose exec db psql -U gathergov -d gathergov
```

Useful tables: `locations`, `meetings`, `sections`, `section_speakers`, `people`, `facts`, `projects`, `project_findings`.

---

## Location

A place a meeting belongs to — usually a city or township from the corpus manifest (for example Joliet, Hermantown).

In the UI, each **location tile** for a given month is colored by the mix of community stances recorded that month at that place.

---

## Meeting

One transcript file: a single municipal meeting with a date, title, optional source URL, and a location.

`relevant` is true only when the **data-center gate** decided the meeting (or enough of it) is about data centers / closely tied infrastructure. Irrelevant meetings are stored lightly and do not drive full extraction.

---

## Section

A labeled stretch of one meeting — not “the whole agenda,” but a part of the transcript with a time range.

Examples of `kind`: introduction, awards, an agenda item, public comment block, vote, close.

Fields that matter:

- `start_seconds` / `end_seconds` — caption time span
- `relevant` — whether this stretch passed the data-center gate
- `is_vote` — formal vote / motion stretch when detected

Sections are the scaffold the rest of extraction hangs on: speakers, facts, and findings point back to a section when possible.

---

## Section speaker

A **person speaking inside one section**, with an optional role for that appearance and the caption span of that speech.

The same person can appear in many sections/meetings. Role on the appearance can differ from meeting to meeting (for example resident in one hearing, petitioner in another).

---

## Person

Someone named in the captions — resident, petitioner, council member, staff, or other.

Identity today is the pair **name + address** (normalized keys). If the address is missing or ASR garbles the name, the same real-world person can show up as more than one row. That is a known limitation (people deduplication).

`kind` is a coarse role bucket supported by the transcript: `petitioner`, `resident`, `council`, `staff`, or `other`.

---

## Fact

One **claim, view, or formal action** tied to a meeting section — the atomic “someone said / the body decided” record.

Two main shapes:

| `kind` | Meaning |
|--------|---------|
| statement | A person stated a view or asked something (usually has `person_id` + `stance`) |
| action | A motion / vote / formal board result (`motion_on`, `result`, optional `tally`) |

Important fields:

- **stance** (on statements): `support`, `oppose`, `condition`, `question`, `uncertain`, or `neutral`  
  - **condition** = accept only if something is met  
  - **question** = they only ask; a question is **not** treated as opposition  
- **excerpt** — short span of words from the transcript (citation / evidence)  
- **project_id** — optional link when the statement is about a specific project or policy  
- **evidence_kind** — how the view was expressed (for example direct speech vs formal action)

Facts are what feed person timelines and the “people’s views” side of the UI.

---

## Project

A **named data-center project or a policy** tied to one (moratorium, ordinance, special-use case, etc.) inside a location.

| Field | Meaning |
|-------|---------|
| `kind` | `project` or `policy` |
| `code` | Petition / case / ordinance / project code when spoken (preferred for matching) |
| `name` | Display / fallback identity when no code |
| `stage` | Latest stage we have a meeting date for |
| `data_center` | Whether it is treated as data-center related |

Matching prefers **code over name** when a code is present, to reduce duplicate rows for the same real project. Name-only matching under ASR noise is still imperfect.

---

## Project finding

A **dated note on a project** from one meeting/section. Later meetings append findings; they do not erase earlier ones.

Typical `kind` values:

| `kind` | Meaning |
|--------|---------|
| `stage_change` | Permit advances, hearing set, vote, moratorium considered/adopted, etc. |
| `decision` | Formal board action |
| `concern` | Issue raised that is not yet a decision |
| `update` | Other material progress |
| `negative` | Something did not happen / was rejected — only kept when coverage looks sufficient |

Findings power the project view (timeline of what happened to the facility or policy).

---

## Stance (as used in the UI)

Not its own table. Stance lives on **facts** (and is aggregated for location tiles).

For a location-month tile we look at community-facing statements in that place and month and summarize tone (mostly support / mostly oppose / mixed / none). Person view shows stance over time, including a prior stance when someone changes.

---

## How they relate (short)

```text
Location
  └── Meeting (transcript)
        └── Section (time-bounded part of the meeting)
              ├── SectionSpeaker → Person
              ├── Fact → Person?  Project?
              └── (feeds) ProjectFinding → Project
```

**Meeting** is the file. **Section** is the chapter. **Person** is who spoke. **Fact** is what they said or what was decided. **Project** is the facility or policy under discussion. **Project finding** is a dated update on that project.
