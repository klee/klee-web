import re
import os
import unittest
import codecs
import shlex

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

        with codecs.open(os.path.join(test_fixtures, 'input.c'),
                         encoding='utf-8') as f:
            code = f.read()

        with codecs.open(os.path.join(test_fixtures, 'expected.stdout'), 'U',
                         encoding='utf-8') as f:
            expected_out = f.read()

        expected_regex = re.compile(u"{}$".format(expected_out), re.M)
        arg_list = shlex.split(args)
        if expect_failure:
            self.assertRaisesRegexp(KleeRunFailure, expected_regex,
                                    self.runner.run_klee, code, arg_list)
        else:
            stdout = self.runner.run_klee(code, arg_list)
            self.assertRegexpMatches(stdout, expected_regex)

    def test_simple_run(self):
        self.run_klee_test('simple')

    def test_simple_unicode_run(self):
        self.run_klee_test('simple_unicode')

    def test_symargs(self):
        self.run_klee_test('symargs', '--sym-args 1 1 1')

    def test_symfiles(self):
        self.run_klee_test('symfiles', '--sym-files 0 1')

    def test_fail_on_invalid_syntax(self):
        self.run_klee_test('invalid_syntax', expect_failure=True)

if __name__ == '__main__':
    unittest.main()
