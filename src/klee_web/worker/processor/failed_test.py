import linecache
import os
import re


class FailedTestProcessor():
    name = 'failed_tests'

    def __init__(self, runner):
        self.source_file = runner.temp_code_file
        self.klee_result_dir = os.path.join(runner.tempdir, 'klee-out-0')

    def get_line_content(self, line_no):
        return linecache.getline(self.source_file, line_no).strip()

    def process_error_file(self, file_name):
        file_path = os.path.join(self.klee_result_dir, file_name)
        with open(file_path) as f:
            content = f.read().splitlines()

        line_no = int(self.parse_line_number(content[2]))

        return {
            'reason': self.parse_reason(content[0]).capitalize(),
            'line_no': line_no,
            'line': self.get_line_content(line_no)
        }

    @staticmethod
    def parse_reason(error_line):
        pattern = re.compile(r'Error: ([a-zA-Z ]+)')
        m = re.match(pattern, error_line)
        return m.group(1) if m else ''

    @staticmethod
    def parse_line_number(line):
        pattern = re.compile(r'Line: ([0-9]+)')
        m = re.match(pattern, line)
        return m.group(1) if m else 0

    def process(self, args):
        error_files = filter(lambda f: f.endswith('.err'),
                             os.listdir(self.klee_result_dir))
        return map(self.process_error_file, error_files)
