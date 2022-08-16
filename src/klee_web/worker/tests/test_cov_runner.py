import re
import os
import unittest
import codecs

from worker.runner import WorkerRunner
from worker.processor.klee_run import KleeRunProcessor
from worker.processor.coverage import CoverageProcessor
from worker.exceptions import KleeRunFailure

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = os.path.join(BASE_DIR, 'fixtures')


class TestWorkerRunner(unittest.TestCase):
    def setUp(self):
        self.runner = WorkerRunner(
            'test',
            pipeline=[KleeRunProcessor, CoverageProcessor]
        )
        self.runner.__enter__()

    def tearDown(self):
        self.runner.__exit__(None, None, None)

    def run_klee_test(self, fixture_name, run_configuration=None,
                      expect_failure=False):
        if not run_configuration:
            run_configuration = {}

        test_fixtures = os.path.join(FIXTURE_DIR, fixture_name)

        with codecs.open(os.path.join(test_fixtures, 'input.c'),
                         encoding='utf-8') as f:
            code = f.read()

        with codecs.open(os.path.join(test_fixtures, 'expected.stdout'),
                         encoding='utf-8') as f:
            expected_out = f.read()

        flags = re.M | re.DOTALL | re.UNICODE
        expected_regex = re.compile(u"{}$".format(expected_out), flags)
        if expect_failure:
            self.assertRaisesRegex(KleeRunFailure, expected_regex,
                                   self.runner.execute_pipeline, code,
                                   run_configuration)
        else:
            result = self.runner.execute_pipeline(code, run_configuration)
            # stdout = result['klee_run']['output']
            cov = result['coverage']
            # Assert cov list has only 1 element for 1 code file
            self.assertEqual(len(cov), 1)
            cov = cov[0]
            # Assert correct keys for cov object
            self.assertIn('file', cov)
            self.assertIn('lines', cov)
            # Assert number of lines in cov equal num of code lines
            num_lines = len(code.splitlines())
            self.assertEqual(len(cov['lines']), num_lines)
            # Assert line has the correct keys and in ascending order
            prev_line = 0
            for line in cov['lines']:
                self.assertIn('line', line)
                self.assertIn('hit', line)
                self.assertTrue(prev_line <= line['line'])
                prev_line = line['line']

    def test_simple_run(self):
        self.run_klee_test('simple', {'coverage_enabled': True})

    def test_simple_unicode_run(self):
        self.run_klee_test('simple_unicode', {'coverage_enabled': True})

    def test_symargs(self):
        self.run_klee_test('symargs', {
            'sym_args': {
                'range': [1, 1],
                'size': 1
            },
            'coverage_enabled': True
        })

    def test_symin(self):
        self.run_klee_test('symin', {
            'sym_in': {
                'size': 1
            },
            'coverage_enabled': True
        })


if __name__ == '__main__':
    unittest.main()
