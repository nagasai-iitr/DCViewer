"""Every instruction and response schema sent to JEV or Gemini."""
from __future__ import annotations

# Hard regex + soft→JEV hybrid lives in app/keywords.py.
# SIGNALS is the closed list Gemini (and the JEV second look) may return.
GATE_SIGNAL = "data_center"
CUE_SIGNALS = ("water", "power", "noise", "radiation", "jobs", "tax", "siting")
SIGNALS = (GATE_SIGNAL, *CUE_SIGNALS)

# Asked only for signals the soft regex flagged and the hard regex missed.
RELEVANCE = {
    "data_center": {
        "type": "choice",
        "instructions": (
            "Does this window name or clearly discuss a data center, server farm, "
            "hyperscale computing facility, colocation facility, or digital "
            "infrastructure campus? Synonyms, nicknames, and speech-to-text misspellings count."
        ),
        "criteria": {
            "yes": "A data center or equivalent computing facility is named or clearly under discussion.",
            "no": "No data center or equivalent computing facility is discussed.",
        },
    },
    "water": {
        "type": "choice",
        "instructions": (
            "Does this window discuss water supply, consumption, wells, cooling water, "
            "or wastewater in a way that could bear on a data center or similar large facility?"
        ),
        "criteria": {
            "yes": "Water demand or supply is tied to a large facility, cooling, or a large new industrial user.",
            "no": "Water is absent, or it is only a routine repair, billing item, or unrelated utility errand.",
        },
    },
    "power": {
        "type": "choice",
        "instructions": (
            "Does this window discuss electricity demand, megawatts, a substation, or "
            "grid capacity in a way that could bear on a data center or similar large facility?"
        ),
        "criteria": {
            "yes": "Power demand or grid capacity is tied to a large facility or large new industrial user.",
            "no": "Power is absent, or it is only a routine outage, street light, or unrelated utility errand.",
        },
    },
    "noise": {
        "type": "choice",
        "instructions": "Does this window discuss noise, sound, or hum from a data center or similar large facility?",
        "criteria": {
            "yes": "Noise or sound from a large facility is discussed.",
            "no": "Noise is absent, or it is an unrelated ambient complaint with no facility.",
        },
    },
    "radiation": {
        "type": "choice",
        "instructions": "Does this window discuss radiation or electromagnetic fields from a data center or similar facility?",
        "criteria": {
            "yes": "Radiation or electromagnetic fields from a facility are discussed.",
            "no": "Radiation and electromagnetic fields are not discussed.",
        },
    },
    "jobs": {
        "type": "choice",
        "instructions": "Does this window discuss jobs or employment from a data center or similar large facility?",
        "criteria": {
            "yes": "Jobs or employment are tied to a large facility or industrial development.",
            "no": "Jobs are absent, or the remark is not about a facility.",
        },
    },
    "tax": {
        "type": "choice",
        "instructions": (
            "Does this window discuss tax abatement, incentives, PILOT, or tax revenue "
            "from a data center or similar large facility?"
        ),
        "criteria": {
            "yes": "A tax incentive, abatement, or revenue effect of a large facility is discussed.",
            "no": "Tax is absent, or it is ordinary city budgeting with no facility.",
        },
    },
    "siting": {
        "type": "choice",
        "instructions": (
            "Does this window discuss zoning, a special use, a permit, or where a data "
            "center or similar large facility would be built?"
        ),
        "criteria": {
            "yes": "Zoning, a permit, or the site of a large facility is discussed.",
            "no": "No siting, zoning, or permit for a large facility is discussed.",
        },
    },
}


SECTION_AND_VOTE = {
    "section": {
        "type": "choice",
        "instructions": (
            "What is the caption marked 'judge this caption only' doing in the "
            "meeting? Judge that caption only. A new section is when the chair "
            "names the next item or block, not when someone mentions an item number."
        ),
        "criteria": {
            "new_section": "The caption opens a new section, item, hearing, awards block, or the close.",
            "same_section": "The caption continues the section already underway.",
            "not_section": "The caption is chatter, a pledge, a ceremony, or logistics.",
            "unclear": "The words do not show whether a section is opening.",
        },
    },
    "vote": {
        "type": "choice",
        "instructions": "Is the judged caption part of a vote? Judge that caption only.",
        "criteria": {
            "vote_called": "A motion is put or the chair calls for the vote.",
            "vote_cast": "Someone casts a vote, such as aye, nay, or a raised hand.",
            "no_vote": "Nobody is calling a vote or casting one.",
            "unclear": "The words do not show whether a vote is happening.",
        },
    },
}

INTRO_SIGNAL = {
    "signal": {
        "type": "choice",
        "instructions": (
            "Judge only the caption marked 'judge this caption only'. "
            "What kind of introduction signal is in it?"
        ),
        "criteria": {
            "self_intro": "The person speaking states their own name, role, district, or address.",
            "call_up": "Someone calls a new person forward to speak.",
            "call_on": "The chair gives the floor to someone already seated.",
            "none": "The caption is not an introduction and not a call for someone.",
            "unclear": "The words do not show whether anyone is being introduced or called.",
        },
    },
}

STILL_SPEAKING = {
    "still": {
        "type": "choice",
        "instructions": (
            "A person is speaking. You are shown how they introduced themselves "
            "and the last few lines already accepted as theirs. Judge only the "
            "line marked NEXT."
        ),
        "criteria": {
            "same_person": "NEXT continues the same person's remarks.",
            "someone_else": "A different person has started, such as the chair thanking them or calling the next speaker.",
            "unclear": "The line does not show who is speaking.",
        },
    },
}

INTRO_PEOPLE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "people": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "address": {"type": "STRING", "nullable": True},
                    "role": {"type": "STRING", "nullable": True},
                    "kind": {
                        "type": "STRING",
                        "enum": ["petitioner", "resident", "council", "staff", "other"],
                    },
                    "department": {"type": "STRING", "nullable": True},
                },
                "required": ["name", "address", "role", "kind", "department"],
            },
        }
    },
    "required": ["people"],
}

INTRO_PEOPLE_PROMPT = """These are the spoken turns before the first agenda item. Each turn is one continuous stretch by the same speaker. The captions are automatic speech recognition. Copy the name as spoken. Do not replace it with a name you know from elsewhere.

Extract every person who introduces themselves or who is introduced by name. Skip a clause that is not a name. A title such as mayor goes in role. department is the city office when one is spoken, otherwise null.

kind is petitioner when they are the applicant or are speaking for a petition or application. kind is resident when they give public comment as a neighbor or community member. kind is council for a council member, commissioner, mayor, or board member. kind is staff for a city or county employee. kind is other if none of those fit.
"""

SPEECH_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "name": {"type": "STRING"},
        "address": {"type": "STRING", "nullable": True},
        "role": {"type": "STRING", "nullable": True},
        "kind": {
            "type": "STRING",
            "enum": ["petitioner", "resident", "council", "staff", "other"],
        },
        "department": {"type": "STRING", "nullable": True},
        "stance": {
            "type": "STRING",
            "enum": ["support", "oppose", "condition", "question", "uncertain", "neutral"],
        },
        "evidence_kind": {
            "type": "STRING",
            "enum": ["direct", "reported", "formal_action", "speculation"],
        },
        "signals": {"type": "ARRAY", "items": {"type": "STRING", "enum": list(SIGNALS)}},
        "project": {"type": "STRING", "nullable": True},
        "project_code": {"type": "STRING", "nullable": True},
        "excerpt": {"type": "STRING"},
        "topics": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "topic": {"type": "STRING"},
                    "summary": {"type": "STRING"},
                    "entities": {"type": "ARRAY", "items": {"type": "STRING"}},
                },
                "required": ["topic", "summary", "entities"],
            },
        },
    },
    "required": [
        "name",
        "address",
        "role",
        "kind",
        "department",
        "stance",
        "evidence_kind",
        "signals",
        "project",
        "project_code",
        "excerpt",
        "topics",
    ],
}

SPEECH_PROMPT = """This is one person speaking, from the line where they introduce themselves until someone else begins. Copy the name as spoken. Do not replace it with a name you know from elsewhere.

If they stay on one subject, return one topic. If they move to a different subject, return one topic per subject. For each topic write a short title, a two or three sentence summary of their view, and two or three places, organizations, or projects they named.

kind is petitioner when they are the applicant or speak for the petition. kind is resident for a neighbor or public commenter. kind is council only for a council member, commissioner, or mayor. kind is staff only for a city or county employee. department is the office they name, or null.

stance is their own view in this speech. support, oppose, condition (they accept it only if something is met), question (they only ask), uncertain, or neutral. A question is not opposition. Do not infer a view they did not state.

evidence_kind is direct for their own words, reported when someone else describes their view, formal_action for a vote or official motion they make, and speculation when they are guessing.

signals lists which of data_center, water, power, noise, radiation, jobs, tax, siting this speech is about. project is the project or policy name they are speaking about, or null. project_code is the petition, case, ordinance, or project code when they say one, otherwise null. excerpt is one short sentence copied from their words.
"""

SECTION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "about": {"type": "STRING"},
        "summary": {"type": "STRING"},
    },
    "required": ["title", "about", "summary"],
}

SECTION_PROMPT = """You are reading one section of a public meeting. The words are automatic speech recognition.

Write a short title, one sentence on what the section is about, and two or three sentences on what was discussed. Do not list who spoke. Do not decide whether a vote passed.
"""

MOTION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "motions": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "on": {"type": "STRING"},
                    "result": {"type": "STRING", "enum": ["pass", "fail", "deferred", "unknown"]},
                    "tally": {"type": "STRING", "nullable": True},
                    "summary": {"type": "STRING"},
                },
                "required": ["on", "result", "tally", "summary"],
            },
        }
    },
    "required": ["motions"],
}

MOTION_PROMPT = """These excerpts are the vote calls inside one section. The words are automatic speech recognition.

Return one motion for each distinct vote. on is what the motion was about. result is pass, fail, deferred, or unknown. tally is the spoken count, or null when no number was spoken. Do not invent a count such as 10 of 15. summary is two sentences on the outcome.
"""

VOICES_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "voices": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "address": {"type": "STRING", "nullable": True},
                    "role": {"type": "STRING", "nullable": True},
                    "kind": {
                        "type": "STRING",
                        "enum": ["petitioner", "resident", "council", "staff", "other"],
                    },
                    "department": {"type": "STRING", "nullable": True},
                    "stance": {
                        "type": "STRING",
                        "enum": ["support", "oppose", "condition", "question", "uncertain", "neutral"],
                    },
                    "evidence_kind": {
                        "type": "STRING",
                        "enum": ["direct", "reported", "formal_action", "speculation"],
                    },
                    "signals": {"type": "ARRAY", "items": {"type": "STRING", "enum": list(SIGNALS)}},
                    "project": {"type": "STRING", "nullable": True},
                    "project_code": {"type": "STRING", "nullable": True},
                    "excerpt": {"type": "STRING"},
                    "summary": {"type": "STRING"},
                },
                "required": [
                    "name",
                    "address",
                    "role",
                    "kind",
                    "department",
                    "stance",
                    "evidence_kind",
                    "signals",
                    "project",
                    "project_code",
                    "excerpt",
                    "summary",
                ],
            },
        }
    },
    "required": ["voices"],
}

VOICES_PROMPT = """This is one section of a public meeting that may bear on a data center. The words are automatic speech recognition.

Extract each person who states their own view, asks a question, or takes a formal action about a data center or about water, power, noise, radiation, jobs, taxes, or siting of a large facility. Include residents giving public comment, petitioners, council members, and staff when they state a view.

Skip the chair when they are only calling the next speaker. Do not infer a position from attendance or from a name on a roll. A question stays a question.

kind is petitioner, resident, council, staff, or other. stance is support, oppose, condition, question, uncertain, or neutral. evidence_kind is direct, reported, formal_action, or speculation. signals uses data_center, water, power, noise, radiation, jobs, tax, siting. project is the project or policy name, or null. project_code is the petition, case, ordinance, or project code when spoken, otherwise null. excerpt is a short span of their words. summary is two sentences on what they said.
"""

PROJECT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "projects": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "code": {"type": "STRING", "nullable": True},
                    "kind": {"type": "STRING", "enum": ["project", "policy"]},
                    "about": {"type": "STRING"},
                    "stage": {
                        "type": "STRING",
                        "enum": ["proposed", "hearing", "approved", "denied", "moratorium", "withdrawn", "unknown"],
                    },
                    "data_center": {"type": "BOOLEAN"},
                    "signals": {"type": "ARRAY", "items": {"type": "STRING", "enum": list(SIGNALS)}},
                    "excerpt": {"type": "STRING", "nullable": True},
                    "findings": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "kind": {
                                    "type": "STRING",
                                    "enum": ["stage_change", "update", "decision", "concern", "negative"],
                                },
                                "stage": {
                                    "type": "STRING",
                                    "enum": [
                                        "proposed",
                                        "hearing",
                                        "approved",
                                        "denied",
                                        "moratorium",
                                        "withdrawn",
                                        "unknown",
                                    ],
                                    "nullable": True,
                                },
                                "body": {"type": "STRING"},
                                "excerpt": {"type": "STRING", "nullable": True},
                                "coverage": {
                                    "type": "STRING",
                                    "enum": ["sufficient", "limited", "insufficient"],
                                },
                                "signals": {
                                    "type": "ARRAY",
                                    "items": {"type": "STRING", "enum": list(SIGNALS)},
                                },
                            },
                            "required": ["kind", "stage", "body", "excerpt", "coverage", "signals"],
                        },
                    },
                },
                "required": [
                    "name",
                    "code",
                    "kind",
                    "about",
                    "stage",
                    "data_center",
                    "signals",
                    "excerpt",
                    "findings",
                ],
            },
        }
    },
    "required": ["projects"],
}

PROJECT_PROMPT = """This is one section of a public meeting. The words are automatic speech recognition.

List each distinct project or policy under discussion that is a data center, or that is broadly tied to one through water, power, noise, radiation, jobs, taxes, or siting. A project is a specific facility or application. A policy is a rule, moratorium, or incentive that is not one facility.

name is the name spoken, or a short label taken from the words when no proper name is spoken. Do not invent a developer or a city.

code is the petition number, case number, application number, ordinance number, or project code when one is spoken (examples: Petition 12-34, Case PZ-2025-01, Ordinance 2025-23, Project Loon, SUP-18). Copy it as spoken. code is null when no such identifier appears. Do not invent a code.

data_center is true only when the section names a data center or equivalent facility. stage is proposed, hearing, approved, denied, moratorium, withdrawn, or unknown. Do not treat a proposal as an approval.

findings is the dated evidence from THIS section only. Use stage_change when a permit advances, a hearing is set, a vote passes or fails, or a moratorium is considered or adopted. Use decision for a formal board action. Use concern for a raised issue that is not yet a decision. Use update for other material progress. Use negative only when the transcript coverage is sufficient to support that something did not happen or was rejected; if coverage is thin, omit the negative finding or mark coverage as insufficient so it will be dropped. excerpt is a short span of the words. If nothing here is a data center or one of those tied subjects, return an empty list.
"""


