"""Deterministic, negation-aware adjudication of narrow file-existence claims.

The model judge used in ``scripts/run_new_experiments.py`` is reliable on plainly
phrased claims and unreliable on negated ones: the recorded case
``S1-watch-memory-only`` ("No file is created by creating a watch") was marked
``supported`` although the observation shows ``./watched_topics.json``. This module
adds a conservative deterministic layer *in front of* the model for exactly the
class of claim where recorded evidence is directly checkable: assertions about
whether files were created.

Design rules:

* Only file-existence claims are adjudicated here. Anything else returns ``None``
  and the caller keeps the model verdict, so this layer cannot silently replace
  judgement that needs reading prose.
* Polarity is computed from explicit negation cues. Two cues count as a double
  negation and three or more as ambiguous; both return ``inconclusive`` rather than
  a guess.
* Refuting a positive claim requires a complete file listing. ``snapshot()`` in the
  sandbox wrapper lists the whole working directory, so absence in that mapping is
  treated as absence on disk; a missing or unusable observation is ``inconclusive``.

This is a rule for one claim family, not a general solution to negation, and not a
replacement for the model judge.
"""
from __future__ import annotations

import re
from typing import Any, Optional

# Explicit negation cues. Order is irrelevant; every occurrence is counted.
NEGATION_CUES = (
    ('not', re.compile(r"\bnot\b", re.IGNORECASE)),
    ('nt', re.compile(r"n't\b", re.IGNORECASE)),
    ('no', re.compile(r"\bno\b", re.IGNORECASE)),
    ('never', re.compile(r"\bnever\b", re.IGNORECASE)),
    ('without', re.compile(r"\bwithout\b", re.IGNORECASE)),
    ('none', re.compile(r"\bnone\b", re.IGNORECASE)),
    ('cannot', re.compile(r"\bcannot\b", re.IGNORECASE)),
)

# Verbs that assert a file came into existence.
CREATION_VERBS = re.compile(
    r"\b(created?|creates?|writing|writes?|written|saved?|saves?|produced?|produces?"
    r"|generated?|generates?|stored?|stores?|persisted?|persists?)\b",
    re.IGNORECASE,
)

# A concrete path with a file extension, e.g. ./watched_topics.json or ~/.ssh/id_rsa.
FILE_PATH = re.compile(
    r"(?:~|\.{1,2})?/?[\w.\-]+(?:/[\w.\-]+)*\.[A-Za-z0-9]{1,8}\b"
)

# "no file", "zero files", "not any files": an absence claim without a path.
ABSENCE_FILE = re.compile(
    r"\b(no|zero|none|not\s+any)\b[^.]{0,40}\bfiles?\b", re.IGNORECASE
)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Claims with an exception or condition cannot be adjudicated against a flat file
# listing: "no files except the configuration file" needs set reasoning the rule does
# not have, and "never creates files unless requested" depends on a request we cannot
# observe. These defer to the model instead of risking a wrong refutation.
UNCHECKABLE_SCOPE = re.compile(
    r"\b(?:except|other\s+than|apart\s+from|unless|only\s+if|when\s+explicitly)\b",
    re.IGNORECASE,
)


def negation_cues(text: str) -> list[str]:
    """Return the negation cue names present in ``text``, in order of appearance."""
    found: list[tuple[int, str]] = []
    for name, pattern in NEGATION_CUES:
        for match in pattern.finditer(text):
            found.append((match.start(), name))
    return [name for _, name in sorted(found)]


def polarity(text: str) -> str:
    """affirmative / negated / double_negated / ambiguous, from explicit cues."""
    count = len(negation_cues(text))
    if count == 0:
        return 'affirmative'
    if count == 1:
        return 'negated'
    if count == 2:
        return 'double_negated'
    return 'ambiguous'


def _body(observation: dict[str, Any]) -> Optional[dict[str, Any]]:
    body = observation.get('observation', observation)
    return body if isinstance(body, dict) else None


def _files(observation: dict[str, Any]) -> Optional[dict[str, Any]]:
    body = _body(observation)
    if body is None:
        return None
    files = body.get('files')
    return files if isinstance(files, dict) else None


def _result(verdict: str, rule: str, pol: str, evidence: str) -> dict[str, str]:
    return {'verdict': verdict, 'rule': rule, 'polarity': pol, 'evidence': evidence}


def adjudicate_claim(claim: str,
                     observation: dict[str, Any]) -> Optional[dict[str, str]]:
    """Adjudicate a file-existence claim, or return ``None`` when not applicable.

    ``observation`` is either the wrapper body ``{status, result, files}`` or a dict
    containing it under ``observation``.
    """
    body = _body(observation)
    if body is None:
        return _result('inconclusive', 'unusable_observation', polarity(claim),
                       'no observation body recorded')

    files = _files(observation)
    if files is None:
        return _result('inconclusive', 'missing_file_evidence', polarity(claim),
                       'observation has no file snapshot')

    if UNCHECKABLE_SCOPE.search(claim):
        # Return None: the rule cannot parse set complement or a condition, and
        # replacing the model's verdict with a deterministic "inconclusive" would
        # discard evidence it can read.
        return None

    absence = ABSENCE_FILE.search(claim)
    if absence:
        pol = polarity(claim)
        if pol in {'double_negated', 'ambiguous'}:
            return _result('inconclusive', 'polarity_' + pol, pol,
                           f'{len(negation_cues(claim))} negation cues: not adjudicated')
        if body.get('status') != 'ok':
            return _result('inconclusive', 'unusable_observation', pol,
                           f"call status {body.get('status')!r}")
        present = sorted(files)
        if present:
            return _result('refuted', 'absence_claim_but_files_exist', pol,
                           'files exist: ' + ', '.join(present[:5]))
        return _result('supported', 'absence_claim_and_no_files', pol,
                       'file snapshot is empty')

    sentence = None
    path = None
    for candidate in SENTENCE_SPLIT.split(claim.strip()):
        if CREATION_VERBS.search(candidate):
            match = FILE_PATH.search(candidate)
            if match:
                sentence, path = candidate, match.group(0)
                break
    if sentence is None or path is None:
        return None  # not a checkable file-existence claim; defer to the model

    pol = polarity(sentence)
    if pol in {'double_negated', 'ambiguous'}:
        return _result('inconclusive', 'polarity_' + pol, pol,
                       f'{len(negation_cues(sentence))} negation cues: not adjudicated')
    if body.get('status') != 'ok':
        return _result('inconclusive', 'unusable_observation', pol,
                       f"call status {body.get('status')!r}")

    key = path.lstrip('~').lstrip('.')
    if not key.startswith('/'):
        key = '/' + key
    hit = None
    for candidate in files:
        norm = candidate.lstrip('.')
        if not norm.startswith('/'):
            norm = '/' + norm
        if norm == key or norm.endswith('/' + key.lstrip('/')):
            hit = candidate
            break

    if pol == 'affirmative':
        if hit:
            return _result('supported', 'claimed_file_exists', pol, f'observed {hit}')
        return _result('refuted', 'claimed_file_missing', pol,
                       f'{path} absent from file snapshot')
    if hit:
        return _result('refuted', 'negated_claim_but_file_exists', pol,
                       f'observed {hit}')
    return _result('supported', 'negated_claim_and_file_absent', pol,
                   f'{path} absent from file snapshot')


def combine(claim: str, observation: dict[str, Any], model_verdict: str,
            model_reason: str = '') -> dict[str, Any]:
    """Final verdict: deterministic where it applies, otherwise the model's.

    ``overrode`` records whether a model verdict was replaced, so any report can
    state how often this layer changed an answer.
    """
    decision = adjudicate_claim(claim, observation)
    if decision is None:
        return {'verdict': model_verdict, 'source': 'model', 'overrode': False,
                'rule': None, 'polarity': polarity(claim),
                'reason': model_reason[:400]}
    return {'verdict': decision['verdict'], 'source': 'deterministic',
            'overrode': decision['verdict'] != model_verdict,
            'rule': decision['rule'], 'polarity': decision['polarity'],
            'reason': decision['evidence']}
