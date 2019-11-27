import os

from worker.runner import WorkerRunner

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

with WorkerRunner('test') as runner:
    test_dir = os.getcwd()
    input_dir = os.path.join(BASE_DIR, "input")
    output_dir = os.path.join(BASE_DIR, "output")

    for input_file_path in os.listdir(input_dir):
        file_base_name = os.path.splitext(os.path.basename(input_file_path))[0]
        output_file_path = os.path.join(test_dir, "output",
                                        file_base_name + ".txt")
        input_file = os.path.join(test_dir, "input", input_file_path)
        with open(input_file, 'r') as code:
            with open(output_file_path, 'w') as result:
                result.write(runner.run_klee(code.read(), "").strip())
