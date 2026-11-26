"""Ingest one caption file into meetings, people, statements, and projects.

Steps for one file:
1. Read captions.
2. Hybrid cue scan: hard regex first, JEV second look only on soft/borderline
   windows for data_center and the other cues. No data_center → skip full ingest.
3. Find section and vote boundaries (JEV).
4. Mark sections that overlap cue windows.
5. Find speaker introductions in those sections (JEV).
6. Follow each speech span (JEV).
7. Ask Gemini for people, voices, projects, summaries, and motions.
8. Save everything through the repositories.
"""
from __future__ import annotations

import argparse
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.services import prompts
from app.config import model_concurrency
from app.database import init_db, session_scope
from app.llm.gemini import GeminiClient
from app.llm.jev import JevClient
from app.services.keywords import scan_caption_windows
from app.logging_config import configure_logging
from app.models import Fact, Meeting, Section, SectionSpeaker
from app.repositories import (
    FactRepository,
    LocationRepository,
    MeetingRepository,
    PersonRepository,
    ProjectRepository,
    SectionRepository,
    SectionSpeakerRepository,
)
from app.utils import (
    caption_pieces,
    chair_handoff,
    clean_caption,
    code_key,
    codes_match,
    load_captions,
    normalize,
    section_kind,
    text_between,
    window_lines,
)

SECTION_CONFIDENCE = 0.7
VOTE_CONFIDENCE = 0.7
INTRO_CONFIDENCE = 0.9
CUE_CONFIDENCE = 0.62
SPEECH_GAP = 15
CUE_WINDOW = 36

logger = logging.getLogger("app.flow")


def run_parallel(items: list, fn, on_progress=None) -> list:
    """Run fn on each item. Results keep input order."""
    total = len(items)
    if total == 0:
        return []
    done = 0
    lock = threading.Lock()

    def wrap(item):
        nonlocal done
        value = fn(item)
        with lock:
            done += 1
            current = done
        if on_progress and (current % 100 == 0 or current == total):
            on_progress(current, total)
        return value

    workers = min(model_concurrency(), total)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(wrap, items))


class DraftSection:
    """One section held in memory until every model call for the meeting returns."""

    def __init__(self, position: int, kind: str, title: str, start_seconds: float, end_seconds: float) -> None:
        self.position = position
        self.kind = kind
        self.title = title
        self.about = None
        self.summary = None
        self.start_seconds = start_seconds
        self.end_seconds = end_seconds
        self.is_vote = False
        self.relevant = False
        self.signals: list[str] = []
        self.people: list[dict] = []
        self.speakers: list[dict] = []
        self.voices: list[dict] = []
        self.projects: list[dict] = []
        self.motions: list[dict] = []


class MeetingFlow:
    """Runs the ingest steps for one transcript file."""

    def __init__(self, jev: JevClient, gemini: GeminiClient) -> None:
        self.jev = jev
        self.gemini = gemini
        self.relevant = False
        self.signal_names: list[str] = []
        self.matched_keywords: list[str] = []

    def prepare(self, path: Path, on_step) -> list[DraftSection]:
        """Run model work for one file. Returns sections to save, or [] when skipped."""
        on_step("reading captions")
        captions = load_captions(path)
        logger.info("%s captions", len(captions))

        cue_hits = self.scan_cues(captions, on_step)
        self.signal_names = sorted({name for hit in cue_hits for name in hit["signals"]})
        self.matched_keywords = sorted({word for hit in cue_hits for word in hit.get("keywords") or []})
        self.relevant = any("data_center" in hit["signals"] for hit in cue_hits)

        if not self.relevant:
            on_step("skipped: no data center")
            logger.info("skipping full ingest; cues=%s", ", ".join(self.signal_names) or "none")
            return []

        logger.info(
            "data center open; keywords %s; cues %s",
            ", ".join(self.matched_keywords) or "none",
            ", ".join(self.signal_names),
        )
        sections, vote_indexes = self.find_sections(captions, cue_hits, on_step)
        self.mark_cue_sections(captions, sections, cue_hits)
        intro_by_index = self.find_introductions(captions, sections, on_step)
        speeches = self.follow_speeches(captions, sections, intro_by_index, on_step)
        on_step("extracting people and views")
        self.extract_text(captions, sections, vote_indexes, speeches)
        logger.info(
            "jev %s calls, %s reused, gemini %s calls",
            self.jev.calls,
            self.jev.cache_hits,
            self.gemini.calls,
        )
        return sections

    def save(self, session, meta: dict, sections: list[DraftSection]) -> Meeting:
        """Write the meeting and every linked row in one transaction."""
        location = self.save_location(session, meta)
        meeting = self.save_meeting(session, meta, location)
        if not sections:
            return meeting

        people = PersonRepository(session)
        projects = ProjectRepository(session)
        speakers = SectionSpeakerRepository(session)
        facts = FactRepository(session)
        section_repo = SectionRepository(session)
        project_by_key: dict = {}

        for draft in sections:
            section = self.save_section(section_repo, meeting, draft)
            self.save_section_projects(projects, project_by_key, location, meta, meeting, section, draft)
            self.save_intro_people(people, speakers, section, draft)
            seen = self.save_speech_statements(
                people, speakers, facts, projects, project_by_key, location, meta, meeting, section, draft
            )
            self.save_voice_statements(
                people, speakers, facts, projects, project_by_key, location, meta, meeting, section, draft, seen
            )
            self.save_motions(facts, project_by_key, meeting, section, draft)
        return meeting

    def scan_cues(self, captions: list[dict], on_step) -> list[dict]:
        """Hybrid cue scan: hard regex first, JEV only for soft misses.

        If no data center is known yet, JEV only answers the data_center question
        on soft-hint windows. After a data center is found, JEV fills in the
        other soft cue misses too.
        """
        on_step("scanning cues (regex)")
        windows = scan_caption_windows(captions, CUE_WINDOW)
        # Keep regex findings on the flow immediately so a later network error
        # still reports what the keyword pass already saw.
        self.matched_keywords = sorted({word for row in windows for word in row.get("keywords") or []})
        self.signal_names = sorted({name for row in windows for name in row.get("signals") or []})
        self.relevant = "data_center" in self.signal_names
        hard_hits = sum(1 for row in windows if row["signals"])
        checked = 0

        def has_data_center() -> bool:
            return any("data_center" in row["signals"] for row in windows)

        def missing_signals(row: dict) -> list[str]:
            return [name for name in (row.get("ask_jev") or []) if name not in row["signals"]]

        def judge(row: dict):
            ask = missing_signals(row)
            if not has_data_center():
                ask = [name for name in ask if name == "data_center"]
            questions = {name: prompts.RELEVANCE[name] for name in ask if name in prompts.RELEVANCE}
            if not questions:
                return row
            answers = self.jev.ask(row["text"][:12000], questions)
            signals = set(row["signals"])
            sources = dict(row.get("sources") or {})
            for name in questions:
                choice, score = self.jev.choice(answers, name)
                if choice == "yes" and score >= CUE_CONFIDENCE:
                    signals.add(name)
                    sources[name] = "jev"
            row["signals"] = sorted(signals)
            row["sources"] = sources
            return row

        # Pass 1: find a data center when regex missed one.
        pass1 = [row for row in windows if "data_center" in missing_signals(row)]
        if pass1 and not has_data_center():
            on_step(f"scanning cues (jev gate) 0/{len(pass1)}")
            run_parallel(pass1, judge, lambda done, total: on_step(f"scanning cues (jev gate) {done}/{total}"))
            checked += len(pass1)

        # Pass 2: with the gate open, fill soft cue misses (water, power, …).
        if has_data_center():
            pass2 = [row for row in windows if missing_signals(row)]
            if pass2:
                on_step(f"scanning cues (jev cues) 0/{len(pass2)}")
                run_parallel(pass2, judge, lambda done, total: on_step(f"scanning cues (jev cues) {done}/{total}"))
                checked += len(pass2)

        hits = [row for row in windows if row["signals"]]
        gate = sum(1 for row in hits if "data_center" in row["signals"])
        jev_added = sum(1 for row in hits if "jev" in (row.get("sources") or {}).values())
        logger.info(
            "cue windows regex=%s jev_checked=%s hits=%s data_center=%s jev_confirmed=%s",
            hard_hits,
            checked,
            len(hits),
            gate,
            jev_added,
        )
        return hits

    def find_sections(
        self, captions: list[dict], cue_hits: list[dict], on_step
    ) -> tuple[list[DraftSection], list[int]]:
        """Ask JEV where new sections and vote calls start.

        Only captions near the opening and near keyword windows are judged.
        That keeps runtime on large meetings proportional to the data-center talk.
        """
        indexes = self.section_scan_indexes(captions, cue_hits)
        on_step(f"scanning sections 0/{len(indexes)}")

        def judge(index: int):
            answers = self.jev.ask(window_lines(captions, index, 5, 0), prompts.SECTION_AND_VOTE)
            section_choice, section_score = self.jev.choice(answers, "section")
            vote_choice, vote_score = self.jev.choice(answers, "vote")
            return index, section_choice, section_score, vote_choice, vote_score

        judged = run_parallel(indexes, judge, lambda done, total: on_step(f"scanning sections {done}/{total}"))
        boundaries = []
        vote_indexes = []
        for index, section_choice, section_score, vote_choice, vote_score in judged:
            if section_choice == "new_section" and section_score >= SECTION_CONFIDENCE:
                boundaries.append(index)
            if vote_choice == "vote_called" and vote_score >= VOTE_CONFIDENCE:
                vote_indexes.append(index)
        boundaries.sort()
        vote_indexes.sort()
        sections = self.build_sections(captions, boundaries)
        logger.info("%s sections, %s vote calls", len(sections), len(vote_indexes))
        return sections, vote_indexes

    def section_scan_indexes(self, captions: list[dict], cue_hits: list[dict]) -> list[int]:
        """Caption indexes worth judging for section and vote boundaries."""
        needed = set(range(5, min(len(captions), 60)))
        for hit in cue_hits:
            start = max(5, hit["start"] - 8)
            end = min(len(captions), hit["end"] + 8)
            needed.update(range(start, end))
        return sorted(needed)

    def build_sections(self, captions: list[dict], boundaries: list[int]) -> list[DraftSection]:
        """Turn boundary indexes into DraftSection rows. Index 0 is always the introduction."""
        cuts = [0, *boundaries, len(captions)]
        sections: list[DraftSection] = []
        for position, (start, end) in enumerate(zip(cuts, cuts[1:])):
            if start == end:
                continue
            title = "Introduction" if position == 0 else clean_caption(captions[start].get("text"))[:300]
            kind = "introduction" if position == 0 else section_kind(title)
            sections.append(
                DraftSection(position, kind, title, captions[start]["start"], captions[end - 1]["end"])
            )
        return sections

    def mark_cue_sections(self, captions: list[dict], sections: list[DraftSection], hits: list[dict]) -> None:
        """Mark a section for extraction when it overlaps a keyword / cue window."""
        for section in sections:
            signals = set()
            for hit in hits:
                hit_start = captions[hit["start"]]["start"]
                hit_end = captions[hit["end"] - 1]["end"]
                if section.end_seconds >= hit_start and section.start_seconds <= hit_end:
                    signals.update(hit["signals"])
            section.signals = sorted(signals)
            section.relevant = bool(signals)
        logger.info("extractable sections %s", sum(1 for section in sections if section.relevant))

    def find_introductions(self, captions, sections, on_step) -> dict[int, tuple[str, float]]:
        """Ask which captions in cue sections are a speaker introducing themselves."""
        indexes = []
        for section in sections:
            if section.kind == "introduction" or not section.relevant:
                continue
            indexes.extend(
                index
                for index, caption in enumerate(captions)
                if section.start_seconds <= caption["start"] <= section.end_seconds
            )
        on_step(f"scanning speakers 0/{len(indexes)}")

        def judge(index: int):
            answers = self.jev.ask(window_lines(captions, index, 3, 3), prompts.INTRO_SIGNAL)
            return (index, *self.jev.choice(answers, "signal"))

        found = {}
        for index, choice, score in run_parallel(
            indexes, judge, lambda done, total: on_step(f"scanning speakers {done}/{total}")
        ):
            found[index] = (choice, score)
        return found

    def follow_speeches(self, captions, sections, intro_by_index, on_step) -> list[tuple]:
        """Walk each introduction until someone else keeps the floor."""
        jobs = []
        for section in sections:
            if section.kind == "introduction" or not section.relevant:
                continue
            anchors = self.intro_anchors(captions, section, intro_by_index)
            for anchor in anchors:
                jobs.append((section.position, anchor))
        on_step(f"following {len(jobs)} speeches")

        def walk(item):
            position, anchor = item
            start, end, speech = self.speech_span(captions, anchor)
            return position, start, end, speech

        return [item for item in run_parallel(jobs, walk) if item[3]]

    def intro_anchors(self, captions, section, intro_by_index) -> list[int]:
        """Indexes where a new speaker starts inside one section."""
        indexes = [
            index
            for index, caption in enumerate(captions)
            if section.start_seconds <= caption["start"] <= section.end_seconds
        ]
        anchors = []
        for index in indexes:
            choice, score = intro_by_index.get(index, ("none", 0.0))
            if choice in {"self_intro", "call_up"} and score >= INTRO_CONFIDENCE:
                if not anchors or index - anchors[-1] >= SPEECH_GAP:
                    anchors.append(index)
        return anchors

    def extract_text(self, captions, sections, vote_indexes, speeches) -> None:
        """Ask Gemini for introductions, summaries, voices, projects, speeches, and motions."""
        tasks = self.build_gemini_tasks(captions, sections, vote_indexes, speeches)
        by_position = {section.position: section for section in sections}

        def run(task):
            return task, self.gemini.generate(task[2], task[3])

        for task, parsed in run_parallel(tasks, run):
            self.apply_gemini_result(by_position[task[1]], task, parsed)

    def build_gemini_tasks(self, captions, sections, vote_indexes, speeches) -> list[tuple]:
        """Build the Gemini work list for this meeting."""
        tasks = []
        for section in sections:
            body = text_between(captions, section.start_seconds, section.end_seconds + 0.001)
            if section.kind == "introduction" and body:
                tasks.append(("intro", section.position, prompts.INTRO_PEOPLE_PROMPT + "\n\n" + body, prompts.INTRO_PEOPLE_SCHEMA))
            if not body:
                continue
            if section.kind == "introduction" or section.relevant:
                tasks.append(("summary", section.position, prompts.SECTION_PROMPT + "\n\n" + body, prompts.SECTION_SCHEMA))
            if section.relevant:
                tasks.append(("voices", section.position, prompts.VOICES_PROMPT + "\n\n" + body, prompts.VOICES_SCHEMA))
                tasks.append(("project", section.position, prompts.PROJECT_PROMPT + "\n\n" + body, prompts.PROJECT_SCHEMA))
            vote_inside = [
                index
                for index in vote_indexes
                if section.start_seconds <= captions[index]["start"] <= section.end_seconds
            ]
            if vote_inside and (section.relevant or section.kind == "introduction"):
                section.is_vote = True
                excerpts = "\n".join(clean_caption(captions[index].get("text")) for index in vote_inside)
                tasks.append(
                    (
                        "motion",
                        section.position,
                        prompts.MOTION_PROMPT + "\n\n" + excerpts,
                        prompts.MOTION_SCHEMA,
                        captions[vote_inside[0]]["start"],
                        captions[vote_inside[-1]]["end"],
                    )
                )
        for position, start, end, speech in speeches:
            tasks.append(
                (
                    "speech",
                    position,
                    prompts.SPEECH_PROMPT + "\n\n" + speech,
                    prompts.SPEECH_SCHEMA,
                    captions[start]["start"],
                    captions[end]["end"],
                )
            )
        return tasks

    def apply_gemini_result(self, section: DraftSection, task: tuple, parsed: dict) -> None:
        """Copy one Gemini answer onto the draft section."""
        kind = task[0]
        if kind == "intro":
            section.people = parsed.get("people") or []
            logger.info("introduction returned %s people", len(section.people))
        elif kind == "summary":
            section.title = parsed.get("title") or section.title
            section.about = parsed.get("about")
            section.summary = parsed.get("summary")
            logger.info("section %s titled %s", section.position, section.title)
        elif kind == "voices":
            section.voices = parsed.get("voices") or []
            logger.info("section %s voices %s", section.position, len(section.voices))
        elif kind == "project":
            section.projects = parsed.get("projects") or []
            logger.info("section %s projects %s", section.position, len(section.projects))
        elif kind == "speech":
            section.speakers.append({"parsed": parsed, "start_seconds": task[4], "end_seconds": task[5]})
            logger.info("speaker %s topics %s", parsed.get("name"), len(parsed.get("topics") or []))
        elif kind == "motion":
            for motion in parsed.get("motions") or []:
                motion["start_seconds"] = task[4]
                motion["end_seconds"] = task[5]
                section.motions.append(motion)
            logger.info("section %s vote, %s motions", section.position, len(section.motions))

    def speech_span(self, captions: list[dict], anchor: int) -> tuple[int, int, str]:
        """Walk backward and forward from an introduction until someone else keeps the floor."""
        intro = clean_caption(captions[anchor].get("text"))
        accepted = [intro]
        start_index = anchor
        end_index = anchor
        for index in range(anchor - 1, max(-1, anchor - 9), -1):
            pieces = caption_pieces(captions[index].get("text"))
            if not pieces or chair_handoff(pieces[-1]):
                break
            if not self.line_is_same_speaker(intro, accepted, pieces[-1]):
                break
            accepted.insert(0, pieces[-1])
            start_index = index
        index = anchor + 1
        steps = 0
        while index < len(captions) and steps < 80:
            stopped = False
            for line in caption_pieces(captions[index].get("text")):
                if len(accepted) >= 4 and chair_handoff(line):
                    if not self.speaker_resumes(captions, index, intro, accepted):
                        stopped = True
                        break
                    continue
                if not self.line_is_same_speaker(intro, accepted, line):
                    if not self.speaker_resumes(captions, index, intro, accepted):
                        stopped = True
                        break
                    continue
                accepted.append(line)
                end_index = index
            if stopped:
                break
            steps += 1
            index += 1
        return start_index, end_index, " ".join(accepted)

    def line_is_same_speaker(self, intro: str, accepted: list[str], line: str) -> bool:
        """Ask JEV whether the next line is still the person who introduced themselves."""
        recent = "\n".join(f"Already theirs: {item}" for item in accepted[-3:])
        state = f"Introduction: {intro}\n{recent}\nNEXT, judge this line only: {line}"
        answers = self.jev.ask(state, prompts.STILL_SPEAKING)
        choice, _score = self.jev.choice(answers, "still")
        someone_score = (answers["still"].get("probabilities") or {}).get("someone_else", 0)
        return not (choice == "someone_else" and someone_score >= 0.6)

    def speaker_resumes(self, captions: list[dict], index: int, intro: str, accepted: list[str]) -> bool:
        """True when the same person continues within the next two captions."""
        for follow in range(index + 1, min(len(captions), index + 3)):
            for line in caption_pieces(captions[follow].get("text")):
                if chair_handoff(line):
                    continue
                if self.line_is_same_speaker(intro, accepted, line):
                    return True
        return False

    def save_location(self, session, meta: dict):
        """Create or reuse the location named on the upload."""
        if not meta.get("location"):
            return None
        return LocationRepository(session).find_or_create(meta.get("location_id"), meta["location"])

    def save_meeting(self, session, meta: dict, location) -> Meeting:
        """Insert the meeting row, including skipped (not relevant) meetings."""
        return MeetingRepository(session).add(
            Meeting(
                transcript_id=meta["transcript_id"],
                external_meeting_id=meta.get("meeting_id"),
                title=meta.get("title") or "",
                meeting_date=meta.get("meeting_date"),
                source_url=meta.get("source_url"),
                source_kind=meta.get("source_kind"),
                location=location,
                relevant=self.relevant,
                signals=self.signal_names,
            )
        )

    def save_section_projects(
        self, projects, project_by_key, location, meta, meeting, section, draft: DraftSection
    ) -> None:
        """Upsert projects named in this section and append dated findings."""
        location_id = location.id if location is not None else None
        meeting_date = meta.get("meeting_date")
        for spoken in draft.projects:
            if not (spoken.get("name") or "").strip():
                continue
            row = projects.find_or_create(location_id, spoken, meeting_date)
            projects.record_meeting_update(row, meeting, section, spoken, meeting_date)
            self.index_project(project_by_key, draft.position, row, spoken)

    def save_section(self, section_repo, meeting, draft: DraftSection) -> Section:
        """Insert one section row."""
        return section_repo.add(
            Section(
                meeting=meeting,
                position=draft.position,
                kind=draft.kind,
                title=draft.title,
                about=draft.about,
                summary=draft.summary,
                start_seconds=draft.start_seconds,
                end_seconds=draft.end_seconds,
                is_vote=draft.is_vote,
                relevant=draft.relevant,
                signals=draft.signals,
            )
        )

    def save_intro_people(self, people, speakers, section, draft: DraftSection) -> None:
        """Store people named in the introduction."""
        for spoken in draft.people:
            if not (spoken.get("name") or "").strip():
                continue
            person = people.find_or_create(spoken)
            speakers.add(
                SectionSpeaker(section=section, person=person, role=spoken.get("role"), kind=spoken.get("kind"))
            )

    def save_speech_statements(
        self, people, speakers, facts, projects, project_by_key, location, meta, meeting, section, draft
    ) -> set[str]:
        """Store followed speeches and their topic statements. Returns spoken name keys."""
        seen = set()
        location_id = location.id if location is not None else None
        for speaker in draft.speakers:
            parsed = speaker["parsed"]
            if not (parsed.get("name") or "").strip():
                continue
            person = people.find_or_create(parsed)
            seen.add(normalize(parsed.get("name")))
            speakers.add(
                SectionSpeaker(
                    section=section,
                    person=person,
                    role=parsed.get("role"),
                    kind=parsed.get("kind"),
                    start_seconds=speaker["start_seconds"],
                    end_seconds=speaker["end_seconds"],
                )
            )
            project = self.resolve_project(
                projects,
                project_by_key,
                draft,
                location_id,
                meta.get("meeting_date"),
                parsed.get("project"),
                parsed.get("project_code"),
            )
            for topic in parsed.get("topics") or []:
                facts.add(
                    Fact(
                        meeting=meeting,
                        section=section,
                        person=person,
                        project=project,
                        kind="statement",
                        topic=topic.get("topic"),
                        body=topic.get("summary") or "",
                        mentions=topic.get("entities") or [],
                        stance=parsed.get("stance"),
                        evidence_kind=parsed.get("evidence_kind"),
                        signals=parsed.get("signals") or [],
                        excerpt=parsed.get("excerpt"),
                        start_seconds=speaker["start_seconds"],
                        end_seconds=speaker["end_seconds"],
                    )
                )
        return seen

    def save_voice_statements(
        self, people, speakers, facts, projects, project_by_key, location, meta, meeting, section, draft, seen
    ) -> None:
        """Store section-level voices that were not already captured as followed speeches."""
        location_id = location.id if location is not None else None
        for voice in draft.voices:
            if not (voice.get("name") or "").strip() or normalize(voice.get("name")) in seen:
                continue
            person = people.find_or_create(voice)
            seen.add(normalize(voice.get("name")))
            speakers.add(
                SectionSpeaker(
                    section=section,
                    person=person,
                    role=voice.get("role"),
                    kind=voice.get("kind"),
                    start_seconds=draft.start_seconds,
                    end_seconds=draft.end_seconds,
                )
            )
            project = self.resolve_project(
                projects,
                project_by_key,
                draft,
                location_id,
                meta.get("meeting_date"),
                voice.get("project"),
                voice.get("project_code"),
            )
            facts.add(
                Fact(
                    meeting=meeting,
                    section=section,
                    person=person,
                    project=project,
                    kind="statement",
                    topic=voice.get("project") or voice.get("project_code") or (voice.get("signals") or ["view"])[0],
                    body=voice.get("summary") or "",
                    mentions=[],
                    stance=voice.get("stance"),
                    evidence_kind=voice.get("evidence_kind"),
                    signals=voice.get("signals") or [],
                    excerpt=voice.get("excerpt"),
                    start_seconds=draft.start_seconds,
                    end_seconds=draft.end_seconds,
                )
            )

    def save_motions(self, facts, project_by_key, meeting, section, draft: DraftSection) -> None:
        """Store vote outcomes for the section."""
        section_projects = [row for (position, _name), row in project_by_key.items() if position == draft.position]
        motion_project = section_projects[0] if len(section_projects) == 1 else None
        for motion in draft.motions:
            facts.add(
                Fact(
                    meeting=meeting,
                    section=section,
                    person=None,
                    project=motion_project,
                    kind="action",
                    topic=motion.get("on"),
                    body=motion.get("summary") or "",
                    mentions=[],
                    motion_on=motion.get("on"),
                    result=motion.get("result"),
                    tally=motion.get("tally"),
                    start_seconds=motion["start_seconds"],
                    end_seconds=motion["end_seconds"],
                )
            )

    def index_project(self, project_by_key, position: int, row, spoken: dict | None = None) -> None:
        """Index a project by name and by code so later statements can find it."""
        project_by_key[(position, normalize(row.name))] = row
        if spoken and spoken.get("name"):
            project_by_key[(position, normalize(spoken.get("name")))] = row
        for raw in (row.code, (spoken or {}).get("code"), (spoken or {}).get("project_code")):
            key = code_key(raw)
            if key:
                project_by_key[(position, f"code:{key}")] = row

    def resolve_project(
        self, projects, project_by_key, draft, location_id, meeting_date, name, project_code=None
    ):
        """Attach a statement to the project it names or codes, or the only one in the section.

        Prefer a petition/case/ordinance/project code when the speaker gave one.
        Fall back to name, then to the only project in the section.
        """
        label = (name or "").strip()
        code = (project_code or "").strip() or None
        rows = [row for (position, _key), row in project_by_key.items() if position == draft.position]
        code_lookup = code_key(code)
        if code_lookup:
            exact = project_by_key.get((draft.position, f"code:{code_lookup}"))
            if exact is not None:
                return exact
            # Soft code match for label/ASR variants already indexed in this section.
            seen = set()
            for (position, key), row in project_by_key.items():
                if position != draft.position or id(row) in seen:
                    continue
                seen.add(id(row))
                if row.code and codes_match(code, row.code):
                    return row
                if key.startswith("code:") and codes_match(code, key.removeprefix("code:")):
                    return row
        if label:
            key = (draft.position, normalize(label))
            if key in project_by_key:
                return project_by_key[key]
        if not label and not code:
            # Unique projects only — avoid collapsing distinct rows.
            unique = list({id(row): row for row in rows}.values())
            return unique[0] if len(unique) == 1 else None
        row = projects.find_or_create(
            location_id,
            {
                "name": label or code or "unnamed",
                "code": code,
                "kind": "project",
                "stage": "unknown",
                "signals": draft.signals,
                "data_center": "data_center" in draft.signals,
            },
            meeting_date,
        )
        self.index_project(project_by_key, draft.position, row, {"name": label, "code": code})
        return row


def main() -> None:
    """Create the tables, or run one transcript from the command line."""
    parser = argparse.ArgumentParser(description="Create the tables or run one transcript.")
    parser.add_argument("command", choices=["init", "run"])
    parser.add_argument("--captions", type=Path)
    parser.add_argument("--transcript-id", type=int)
    parser.add_argument("--title", default="")
    parser.add_argument("--location", default="")
    parser.add_argument("--location-id", type=int)
    parser.add_argument("--meeting-id", type=int)
    parser.add_argument("--meeting-date")
    parser.add_argument("--source-url")
    parser.add_argument("--source-kind")
    args = parser.parse_args()
    configure_logging()
    if args.command == "init":
        init_db()
        print("tables ready")
        return
    if args.captions is None or args.transcript_id is None:
        raise SystemExit("run needs --captions and --transcript-id")
    from datetime import date

    meta = {
        "transcript_id": args.transcript_id,
        "title": args.title,
        "location": args.location,
        "location_id": args.location_id,
        "meeting_id": args.meeting_id,
        "meeting_date": date.fromisoformat(args.meeting_date) if args.meeting_date else None,
        "source_url": args.source_url,
        "source_kind": args.source_kind,
    }
    init_db()
    flow = MeetingFlow(JevClient(), GeminiClient())
    prepared = flow.prepare(args.captions, logger.info)
    with session_scope() as session:
        meeting = flow.save(session, meta, prepared)
        print(f"meeting {meeting.id} transcript {meeting.transcript_id}")


if __name__ == "__main__":
    main()
