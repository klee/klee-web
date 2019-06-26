import linecache
import os
import re
from src.worker.processor.base import BaseProcessor


class FailedTestProcessor(BaseProcessor):
    name = 'failed_tests'
    notify_message = 'Processing failed tests'

    def __init__(self, runner, args):
        BaseProcessor.__init__(self, runner, args)
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

    def process(self):
        error_files = filter(lambda f: f.endswith('.err'),
                             os.listdir(self.klee_result_dir))
        return list(map(self.process_error_file, error_files))
