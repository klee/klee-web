import re
import os
import unittest

from worker.runner import WorkerRunner
from worker.exception import KleeRunFailure


BASE_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = os.path.join(BASE_DIR, 'fixtures')


class TestWorkerRunner(unittest.TestCase):
    def setUp(self):
        self.runner = WorkerRunner('test')
        self.runner.__enter__()

    def tearDown(self):
        self.runner.__exit__(None, None, None)

    def run_klee_test(self, fixture_name, args='', expect_failure=False):
        test_fixtures = os.path.join(FIXTURE_DIR, fixture_name)

        with open(os.path.join(test_fixtures, 'input.c')) as f:
            code = f.read()

        with open(os.path.join(test_fixtures, 'expected.stdout'), 'U') as f:
            expected_out = f.read()

        expected_regex = re.compile("{}$".format(expected_out), re.M)
        if expect_failure:
            self.assertRaisesRegexp(KleeRunFailure, expected_regex,
                                    self.runner.run_klee, code, args)
        else:
            stdout = self.runner.run_klee(code, args)
            self.assertRegexpMatches(stdout, expected_regex)

    def test_simple_run(self):
        self.run_klee_test('simple')

    def test_symargs(self):
        self.run_klee_test('symargs', '--sym-args 1 1 1')

    def test_symfiles(self):
        self.run_klee_test('symfiles', '--sym-files 0 1')

    def test_fail_on_invalid_syntax(self):
        self.run_klee_test('invalid_syntax', expect_failure=True)

if __name__ == '__main__':
    unittest.main()
