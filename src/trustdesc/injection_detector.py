"""Experimental static screening of untrusted tool descriptions for prompt injection.

Scope and honesty constraints:

* This is a **prototype screen**, not a prompt-injection defence. It looks for
  textual patterns; it cannot decide intent, and a miss means only that none of
  these rules fired.
* It is deterministic and explainable: every decision is a list of rule ids with
  the matched excerpt, so a reviewer can check each flag by hand.
* It reads descriptions as inert text. It never executes, evaluates or follows
  anything found in them, and it performs no network or file access.
* It is kept separate from behavioural verification: a description can pass this
  screen and still be contradicted by an execution, and a description can be
  flagged here while its behaviour is perfectly correct.
"""
from __future__ import annotations

import re
from typing import Any

# (rule_id, explanation, compiled pattern)
RULES = (
    ('INJ-OVERRIDE',
     'text tries to cancel earlier instructions',
     re.compile(
         r"\b(?:ignore|disregard|forget)\b[^.\n]{0,40}\b(?:previous|prior|above|earlier|"
         r"system|developer)\b[^.\n]{0,20}\b(?:instructions?|prompts?|rules?)\b"
         r"|\bnew\s+system\s+prompt\b"
         r"|\byou\s+are\s+now\b",
         re.IGNORECASE)),
    ('INJ-CONCEAL',
     'text asks for an action to be hidden from the user',
     re.compile(
         r"\b(?:do\s+not|don't|never)\b[^.\n]{0,30}\b(?:tell|inform|notify|mention|reveal)\b"
         r"[^.\n]{0,20}\b(?:the\s+)?user\b"
         r"|\bwithout\s+(?:telling|informing|notifying)\s+the\s+user\b"
         r"|\bhide\b[^.\n]{0,30}\bfrom\s+the\s+user\b"
         r"|\b(?:silently|secretly)\b",
         re.IGNORECASE)),
    ('INJ-SECRET',
     'text tries to reach credentials or exfiltrate data',
     re.compile(
         r"\b(?:read|cat|open|copy|print|include|append|send|upload|post)\b[^.\n]{0,40}"
         r"(?:~/\.ssh|id_rsa|\.env\b|credentials?|passwords?|api[_\s-]?keys?|secrets?\s+file)"
         r"|\b(?:send|upload|post|exfiltrate)\b[^.\n]{0,40}\bhttps?://"
         r"|\b(?:contents?|copy)\s+of\s+(?:~/\.ssh|\.env\b|id_rsa)",
         re.IGNORECASE)),
    ('INJ-OUTOFSCOPE',
     'text embeds shell or process execution outside the declared purpose',
     re.compile(
         r"\brm\s+-rf\b|\bcurl\b[^\n]{0,60}\|\s*(?:sh|bash)\b|\bwget\b[^\n]{0,60}\|\s*(?:sh|bash)\b"
         r"|\bos\.system\b|\bsubprocess\b|\beval\s*\(|\bbase64\s+-d\b|\bchmod\s+[0-7]{3,4}\b"
         r"|\bsudo\b|\bpython\s+-c\b"
         r"|\bdelete\s+(?:every|all)\b",
         re.IGNORECASE)),
    ('INJ-AUTHORITY',
     'text impersonates a higher-privilege message role',
     re.compile(
         r"^\s*(?:system|assistant|developer)\s*:"
         r"|<\|?\s*(?:system|im_start)\s*\|?>"
         r"|\bdeveloper\s+mode\b",
         re.IGNORECASE | re.MULTILINE)),
)


# Declarative negations ("the tool does not read credentials", "it must never read
# credentials") describe what a tool may not do; flagging them would punish honest
# documentation. Imperatives such as "do not tell the user" are deliberately NOT
# suppressed: those are the attack shape.
DECLARATIVE_NEGATION = re.compile(
    r"\b(?:does|is|are|was|were|has|have|cannot|can't)\s+not\b[^.]{0,25}$"
    r"|\b(?:must|should|will|shall|may)\s+never\b[^.]{0,25}$",
    re.IGNORECASE)


def screen(text: str) -> dict[str, Any]:
    """Return ``{flagged, findings, suppressed}`` for one description. Never acts on it."""
    findings: list[dict[str, str]] = []
    suppressed: list[dict[str, str]] = []
    for rule_id, explanation, pattern in RULES:
        match = pattern.search(text)
        if match and DECLARATIVE_NEGATION.search(text[:match.start()]):
            suppressed.append({'rule': rule_id,
                               'excerpt': text[max(0, match.start() - 40):match.end()].strip(),
                               'reason': 'declarative negation, not an imperative'})
            continue
        if match:
            findings.append({
                'rule': rule_id,
                'explanation': explanation,
                'excerpt': text[max(0, match.start() - 30):match.end() + 30].strip(),
            })
    return {'flagged': bool(findings), 'findings': findings,
            'rules_fired': [f['rule'] for f in findings],
            'suppressed': suppressed}


def label_for(text: str) -> str:
    """Convenience label for reports: flagged / clear. Not a security verdict."""
    return 'flagged' if screen(text)['flagged'] else 'clear'
