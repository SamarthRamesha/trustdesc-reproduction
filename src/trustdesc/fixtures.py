"""Hand-authored replay data for engineering tests, never author data/inference."""
from __future__ import annotations

import copy

DESCRIPTION = {
    'summary': 'Validates and accepts spreadsheet formula text.',
    'functionalities': ['Adds a leading = when omitted.',
                        'Rejects HYPERLINK and INDIRECT formulas.',
                        'Uses an internal Python validation function.'],
    'input_schema': {'type': 'object', 'properties': {'formula': {'type': 'string', 'description': 'Formula text.'}}, 'required': ['formula']},
    'claims': [
        {'id': 'summary', 'text': 'Validates and accepts spreadsheet formula text.', 'target': ['summary']},
        {'id': 'auto_prefix', 'text': 'Adds a leading = when omitted.', 'target': ['functionalities', 0]},
        {'id': 'unsafe', 'text': 'Rejects HYPERLINK and INDIRECT formulas.', 'target': ['functionalities', 1]},
        {'id': 'internal', 'text': 'Uses an internal Python validation function.', 'target': ['functionalities', 2]},
        {'id': 'input', 'text': 'Formula text.', 'target': ['input_schema', 'properties', 'formula', 'description']},
    ],
}


def record(stage, response):
    return {'stage': stage, 'response': response}


def replay():
    responses = [record('identifier_filter', {'renames': {}}), record('description', copy.deepcopy(DESCRIPTION))]
    tasks = []
    objectives = {'summary': 'Accept formula =SUM(A1:A5).', 'auto_prefix': 'Try formula SUM(A1:A5) without =.',
                  'unsafe': 'Try both =INDIRECT("A1") and =HYPERLINK("x").', 'input': 'Pass formula =1+1 as text.'}
    for c in DESCRIPTION['claims']:
        verifiable = c['id'] != 'internal'
        tasks.append({'claim_id': c['id'], 'verifiable': verifiable, 'task': objectives.get(c['id']),
                      'reason': 'Observe fixture input/output or error.' if verifiable else 'Internal organization is not a runtime functional guarantee.'})
    responses.append(record('verification_plan', {'tasks': tasks}))
    for cid, values, verdict in [('summary', ['=SUM(A1:A5)'], 'supported'),
                                  ('auto_prefix', ['SUM(A1:A5)'], 'refuted'),
                                  ('unsafe', ['=INDIRECT("A1")', '=HYPERLINK("x")'], 'supported'),
                                  ('input', ['=1+1'], 'supported')]:
        for value in values:
            responses.append(record('agent', {'action': 'call', 'tool': 'apply_formula', 'arguments': {'formula': value}}))
        responses.append(record('agent', {'action': 'finish', 'answer': 'Observed the fixture results.'}))
        responses.append(record('judge', {'verdict': verdict,
                                          'reason': 'Missing-prefix input raises an error.' if cid == 'auto_prefix' else 'Observed the specific tested behavior.'}))
    return responses
