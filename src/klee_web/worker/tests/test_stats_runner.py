import re
import os
import unittest
import codecs

from worker.runner import WorkerRunner
from worker.processor.klee_run import KleeRunProcessor
from worker.processor.stats import StatsProcessor
from worker.exceptions import KleeRunFailure


BASE_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = os.path.join(BASE_DIR, 'fixtures')


class TestWorkerRunner(unittest.TestCase):
    def setUp(self):
        self.runner = WorkerRunner(
            'test',
            pipeline=[KleeRunProcessor, StatsProcessor]
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
            stdout = result['klee_run']['output']
            stats = result['stats']
            # Assert stats list has 6 rows
            self.assertEqual(len(stats), 6)
            # Assert only 1 stat returned for 1 file
            for stat in stats:
                self.assertEqual(len(stat[1]), 1)
            # Assert instr equal to stdout
            expected_instr = int(re.search(
                r'(?<=total instructions = )\d+',
                stdout
            ).group())
            self.assertEqual(int(stats[0][1][0]), expected_instr)

    def test_simple_run(self):
        self.run_klee_test('simple')

    def test_simple_unicode_run(self):
        self.run_klee_test('simple_unicode')

    def test_symargs(self):
        self.run_klee_test('symargs', {
            'sym_args': {
                'range': [1, 1],
                'size': 1
            }
        })

    def test_symin(self):
        self.run_klee_test('symin', {
            'sym_in': {
                'size': 1
            }
        })


if __name__ == '__main__':
    unittest.main()
