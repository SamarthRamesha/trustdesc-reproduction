"""Tests for the independent challenge set and the screen's recorded behaviour.

These tests pin the measured outcome. They do not assert that the detector is good:
the challenge set shows keyword rules missing paraphrases, and the assertions below
record that as a known result so a future rule change cannot silently rewrite it.
"""
import json
import unittest
from pathlib import Path

from trustdesc.injection_detector import screen

ROOT = Path(__file__).resolve().parents[1]
CHALLENGE = ROOT / 'data' / 'experiments' / 'injection_robustness_v2.json'
DEV = ROOT / 'data' / 'experiments' / 'synthetic_injection_cases.json'
RESULTS = ROOT / 'reports' / 'INJECTION_ROBUSTNESS_V2.json'


class ChallengeSetTests(unittest.TestCase):
    def setUp(self):
        self.cases = json.loads(CHALLENGE.read_text())['cases']

    def test_size_and_labels(self):
        labels = [c['label'] for c in self.cases]
        self.assertEqual(len(self.cases), 30)
        self.assertEqual(labels.count('malicious'), 19)
        self.assertEqual(labels.count('benign'), 8)
        self.assertEqual(labels.count('ambiguous'), 3)

    def test_every_case_has_rationale_and_provenance(self):
        for case in self.cases:
            self.assertTrue(case['rationale'])
            self.assertIn('after_rules_frozen', case['provenance'])

    def test_challenge_texts_are_not_reused_from_development_set(self):
        dev = {c['text'] for c in json.loads(DEV.read_text())['cases']}
        overlaps = [c['case_id'] for c in self.cases if c['text'] in dev]
        self.assertEqual(overlaps, [])

    def test_screening_is_pure(self):
        before = [c['text'] for c in self.cases]
        for case in self.cases:
            screen(case['text'])
        self.assertEqual(before, [c['text'] for c in self.cases])

    def test_three_case_examples_behave_as_recorded(self):
        by_id = {c['case_id']: c for c in self.cases}
        self.assertFalse(screen(by_id['P1-earlier-guidance']['text'])['flagged'])
        self.assertFalse(screen(by_id['P9-env-prefix-append']['text'])['flagged'])
        self.assertTrue(screen(by_id['N3-audit-logging']['text'])['flagged'])

    def test_modal_prohibition_is_suppressed(self):
        text = 'The tool must never read credentials, and must never transmit file contents.'
        result = screen(text)
        self.assertFalse(result['flagged'])
        self.assertEqual(result['suppressed'][0]['rule'], 'INJ-SECRET')


class RecordedOutcomeTests(unittest.TestCase):
    """Keep the report, the JSON and the code in sync."""

    def test_recorded_confusion_matches_a_fresh_run(self):
        recorded = json.loads(RESULTS.read_text())['confusion']
        cases = json.loads(CHALLENGE.read_text())['cases']
        tp = fp = tn = fn = 0
        for case in cases:
            flagged = screen(case['text'])['flagged']
            if case['label'] == 'malicious':
                tp, fn = (tp + 1, fn) if flagged else (tp, fn + 1)
            elif case['label'] == 'benign':
                fp, tn = (fp + 1, tn) if flagged else (fp, tn + 1)
        self.assertEqual((tp, fp, tn, fn),
                         (recorded['tp'], recorded['fp'], recorded['tn'], recorded['fn']))
        self.assertEqual((tp, fp, tn, fn), (0, 1, 7, 19))


if __name__ == '__main__':
    unittest.main()
