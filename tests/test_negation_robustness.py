"""Robustness tests for the deterministic negation layer (v2 probes)."""
import json
import unittest
from pathlib import Path

from trustdesc.dynver.negation import adjudicate_claim

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / 'data' / 'experiments' / 'negation_robustness_v2.json'


class ProbeDatasetTests(unittest.TestCase):
    def test_every_probe_matches_its_expected_verdict(self):
        cases = json.loads(CASES.read_text())['cases']
        self.assertEqual(len(cases), 14)
        for case in cases:
            decision = adjudicate_claim(case['claim'], case['observation'])
            actual = 'defer' if decision is None else decision['verdict']
            self.assertEqual(actual, case['expected'], case['case_id'])

    def test_deferral_cases_really_defer(self):
        cases = json.loads(CASES.read_text())['cases']
        deferred = [c['case_id'] for c in cases
                    if adjudicate_claim(c['claim'], c['observation']) is None]
        self.assertEqual(sorted(deferred),
                         sorted(['R10-non-file-claim', 'R11-except-config',
                                 'R12-not-avoid', 'R13-never-unless']))


class ScopeAndConditionTests(unittest.TestCase):
    def test_exception_clause_defers(self):
        decision = adjudicate_claim('No files except the configuration file are created.',
                                    {'status': 'ok', 'files': {'./config.json': '{}'}})
        self.assertIsNone(decision)

    def test_conditional_claim_defers(self):
        decision = adjudicate_claim('The tool never creates files unless explicitly requested.',
                                    {'status': 'ok', 'files': {'./watched_topics.json': '{}'}})
        self.assertIsNone(decision)

    def test_negation_of_avoidance_defers(self):
        decision = adjudicate_claim('The tool does not avoid creating files.',
                                    {'status': 'ok', 'files': {'./watched_topics.json': '{}'}})
        self.assertIsNone(decision)

    def test_failed_call_never_supports_even_a_negated_claim(self):
        decision = adjudicate_claim('No file is created.',
                                    {'status': 'error', 'files': {}})
        self.assertEqual(decision['verdict'], 'inconclusive')

    def test_unrelated_file_does_not_support_an_absence_claim(self):
        decision = adjudicate_claim('No file is created.',
                                    {'status': 'ok', 'files': {'./other.json': '{}'}})
        self.assertEqual(decision['verdict'], 'refuted')


if __name__ == '__main__':
    unittest.main()
