"""Tests for the deterministic negation-aware claim layer."""
import unittest

from trustdesc.dynver.negation import adjudicate_claim, combine, polarity

OK = 'ok'
FILE = './watched_topics.json'


def obs(files, status=OK):
    return {'status': status, 'files': files}


class PolarityTests(unittest.TestCase):
    def test_cue_classification(self):
        self.assertEqual(polarity('The call saves the watch.'), 'affirmative')
        self.assertEqual(polarity('The call does not save the watch.'), 'negated')
        self.assertEqual(polarity('It is not true that no file is created.'), 'double_negated')
        self.assertEqual(polarity('It is not never the case that no file is created.'),
                         'ambiguous')


class PositiveClaimTests(unittest.TestCase):
    def test_file_present_is_supported(self):
        d = adjudicate_claim(f'The call writes {FILE}.', obs({FILE: '{}'}))
        self.assertEqual((d['verdict'], d['rule']), ('supported', 'claimed_file_exists'))

    def test_file_absent_is_refuted(self):
        d = adjudicate_claim(f'The call writes {FILE}.', obs({}))
        self.assertEqual((d['verdict'], d['rule']), ('refuted', 'claimed_file_missing'))

    def test_other_file_only_is_contradictory_evidence(self):
        d = adjudicate_claim(f'The call writes {FILE}.', obs({'./other.json': '{}'}))
        self.assertEqual(d['verdict'], 'refuted')


class NegatedClaimTests(unittest.TestCase):
    def test_recorded_s1_claim_is_refuted_when_file_exists(self):
        claim = 'No file is created by creating a watch.'
        d = adjudicate_claim(claim, obs({FILE: '{}'}))
        self.assertEqual((d['verdict'], d['rule']),
                         ('refuted', 'absence_claim_but_files_exist'))

    def test_absence_claim_supported_when_no_files(self):
        d = adjudicate_claim('No file is created by creating a watch.', obs({}))
        self.assertEqual((d['verdict'], d['rule']), ('supported', 'absence_claim_and_no_files'))

    def test_negated_path_claim_refuted_when_file_present(self):
        d = adjudicate_claim(f'The tool does not write {FILE}.', obs({FILE: '{}'}))
        self.assertEqual((d['verdict'], d['rule']),
                         ('refuted', 'negated_claim_but_file_exists'))

    def test_negated_path_claim_supported_when_file_absent(self):
        d = adjudicate_claim(f'The tool does not write {FILE}.', obs({}))
        self.assertEqual(d['verdict'], 'supported')


class ConservativeTests(unittest.TestCase):
    def test_double_negative_is_inconclusive(self):
        d = adjudicate_claim('It is not true that no file is created.', obs({FILE: '{}'}))
        self.assertEqual((d['verdict'], d['rule']), ('inconclusive', 'polarity_double_negated'))

    def test_ambiguous_wording_is_inconclusive(self):
        d = adjudicate_claim('It is not never the case that no file is created.',
                             obs({FILE: '{}'}))
        self.assertEqual((d['verdict'], d['rule']), ('inconclusive', 'polarity_ambiguous'))

    def test_missing_evidence_is_inconclusive(self):
        d = adjudicate_claim(f'The call writes {FILE}.', {'status': OK})
        self.assertEqual((d['verdict'], d['rule']), ('inconclusive', 'missing_file_evidence'))

    def test_failed_call_is_inconclusive(self):
        d = adjudicate_claim(f'The call writes {FILE}.', obs({FILE: '{}'}, status='error'))
        self.assertEqual(d['verdict'], 'inconclusive')

    def test_non_existence_claims_defer_to_the_model(self):
        self.assertIsNone(adjudicate_claim('The call returns a success message.',
                                           obs({FILE: '{}'})))
        self.assertIsNone(adjudicate_claim('Listing returns count 0.', obs({})))

    def test_combine_records_override(self):
        claim = 'No file is created by creating a watch.'
        d = combine(claim, obs({FILE: '{}'}), 'supported', 'model inverted the claim')
        self.assertEqual((d['verdict'], d['source'], d['overrode']),
                         ('refuted', 'deterministic', True))
        d = combine('The call returns a message.', obs({}), 'supported', 'model')
        self.assertEqual((d['source'], d['overrode']), ('model', False))


if __name__ == '__main__':
    unittest.main()
