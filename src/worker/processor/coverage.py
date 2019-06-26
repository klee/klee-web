import os
import glob

from gcovparse import gcovparse
from src.worker.processor.base import BaseProcessor


class CoverageProcessor(BaseProcessor):
    name = 'coverage'
    notify_message = 'Generating coverage reports'

    def __init__(self, runner, args):
        BaseProcessor.__init__(self, runner, args)

    @property
    def enabled(self):
        return self.args.get('coverage_enabled')

    def process(self):
        runner = self.runner
        mount_dir = runner.DOCKER_MOUNT_DIR
        coverage_obj_file = os.path.join(mount_dir, 'code_cov.o')
        docker_result_path = os.path.join(mount_dir, 'klee-out-0')

        clang_command = ['/usr/bin/clang-3.4', '-g', '--coverage', '-L',
                         '/home/klee/klee_build/klee/Release+Asserts/lib/',
                         runner.DOCKER_CODE_FILE, '-lkleeRuntest',
                         '-o', coverage_obj_file]
        runner.run_with_docker(clang_command)

        result_dir = os.path.join(self.runner.tempdir, 'klee-out-0')
        ktest_files = glob.glob(os.path.join(result_dir, "*.ktest"))

        for abs_ktest_file in ktest_files:
            base_ktest_file = os.path.basename(abs_ktest_file)
            ktest_file = os.path.join(docker_result_path, base_ktest_file)

            klee_replay_command = ['klee-replay', coverage_obj_file,
                                   ktest_file]
            runner.run_with_docker(klee_replay_command,
                                   {'KTEST_FILE': ktest_file})

        llvm_cov_command = ['llvm-cov-3.4', '-gcda=code.gcda',
                            '-gcno=code.gcno', '-dump']
        gcov_data = runner.run_with_docker(llvm_cov_command)

        return gcovparse(gcov_data)
