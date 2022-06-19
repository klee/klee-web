import re
import os
import unittest
import codecs
import json

from worker.runner import WorkerRunner
from worker.processor.klee_run import KleeRunProcessor
from worker.processor.klee_testcases import KleeTestCaseProcessor
from worker.exceptions import KleeRunFailure

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = os.path.join(BASE_DIR, 'fixtures')


class TestWorkerRunner(unittest.TestCase):
    def setUp(self):
        self.runner = WorkerRunner(
            'test',
            pipeline=[KleeRunProcessor, KleeTestCaseProcessor]
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

        with codecs.open(os.path.join(test_fixtures, 'testcases.json'),
                         encoding='utf-8') as f:
            expected_testcases = json.load(f)

        flags = re.M | re.DOTALL | re.UNICODE
        expected_regex = re.compile(u"{}$".format(expected_out), flags)
        if expect_failure:
            self.assertRaisesRegex(KleeRunFailure, expected_regex,
                                   self.runner.execute_pipeline, code,
                                   run_configuration)
        else:
            result = self.runner.execute_pipeline(code, run_configuration)
            testcases = result['test_cases']
            # Assert num of test cases equal expected
            self.assertEqual(len(testcases), len(expected_testcases))
            prev_num = 0
            for i, case in enumerate(testcases):
                str_case = str(case)
                self.assertIn('desc', str_case)
                self.assertIn('args', str_case)
                self.assertIn('.ktest', str_case)

                # Assert number of mem objs equal to number stated in desc
                num_mem_objs = int(case['desc'][2].split(':')[1])
                mem_objs = case['mem_objs']
                self.assertEqual(num_mem_objs, len(mem_objs))

                # Assert number of mem objs equal to expected
                expected_mem_objs = expected_testcases[i]['mem_objs']
                self.assertEqual(len(expected_mem_objs), len(mem_objs))

                # Assert that klee testcases are ordered by ktest file number
                ktest_num = int(re.findall(r'\d+', case['desc'][0])[0])
                self.assertTrue(prev_num <= ktest_num)
                prev_num = ktest_num

            return testcases

    def test_simple_run(self):
        self.run_klee_test('simple')

    def test_simple_unicode_run(self):
        self.run_klee_test('simple_unicode')

    def test_symargs(self):
        testcases = self.run_klee_test('symargs', {
            'sym_args': {
                'range': [1, 1],
                'size': 1
            }
        })
        self.assertIn('arg00', str(testcases))
        self.assertIn('model_version', str(testcases))

    def test_symin(self):
        testcases = self.run_klee_test('symin', {
            'sym_in': {
                'size': 1
            }
        })
        self.assertIn('stdin', str(testcases))
        self.assertIn('stdin-stat', str(testcases))
        self.assertIn('model_version', str(testcases))

    def test_timeout_container(self):
        try:
            self.runner.run_with_docker(['/bin/sleep', '10'], timeout=1)
        except KleeRunFailure as ex:
            self.assertIn('Timeout error after 1', str(ex))
            return
        self.assertTrue(False)


if __name__ == '__main__':
    unittest.main()
