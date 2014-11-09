import sys
import os
import string

sys.path.append(os.path.abspath("../python/"))
print sys.path
from worker.runner import WorkerRunner

with WorkerRunner('test') as runner:
    test_dir = os.getcwd()
    input_dir = os.path.abspath("input")
    output_dir = os.path.abspath("output")

    for input_file_path in os.listdir(input_dir):
        file_base_name = os.path.splitext(os.path.basename(input_file_path))[0]
        output_file_path = os.path.join(test_dir,
                                        "output/" + file_base_name) + ".txt"
        with open(os.path.join(test_dir, "input/" + input_file_path),
                  'r') as code:
            with open(output_file_path, 'w') as result:
                result.write(string.strip(runner.run_klee(code.read(), "")))
