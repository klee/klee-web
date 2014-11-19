import re
import os
import linecache


# Returns a list containing information about failing tests.
def failing(base_dir, results_dir):
    failing_tests = [f for f in os.listdir(results_dir) if f.endswith('.err')]
    return [get_info(base_dir, results_dir, f) for f in failing_tests]


def get_info(base_dir, results_dir, file_name):
    file_path = os.path.join(results_dir, file_name)
    with open(file_path) as f:
        content = f.read().splitlines()

    line_no = int(get_line_no(content[2]))

    return {
        'reason': get_reason(content[0]).capitalize(),
        'line_no': line_no,
        'line': get_line(line_no, base_dir)
    }


def get_reason(error_line):
    pattern = re.compile(r'Error: ([a-zA-Z ]+)')
    return re.match(pattern, error_line).group(1)


def get_line_no(line):
    pattern = re.compile(r'Line: ([0-9]+)')
    return re.match(pattern, line).group(1)


def get_line(line_no, base_dir):
    file_path = os.path.join(base_dir, 'result.c')
    return linecache.getline(file_path, line_no)
