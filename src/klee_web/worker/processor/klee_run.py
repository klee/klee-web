from worker.processor.base import BaseProcessor


class KleeRunProcessor(BaseProcessor):
    name = 'klee_run'
    notify_message = 'Executing KLEE'

    def __init__(self, runner, args):
        BaseProcessor.__init__(self, runner, args)

    def generate_arguments(self):
        klee_args = self.args
        result = []

        stdin_enabled = klee_args.get('stdin_enabled')
        if stdin_enabled:
            num_files = klee_args.get('num_files')
            size_files = klee_args.get('size_files')
            result += ['--sym-files', str(num_files), str(size_files)]

        sym_args = klee_args.get('sym_args')
        if sym_args:
            min_sym_args, max_sym_args = sym_args.get('range')
            size_sym_args = sym_args.get('size')
            if min_sym_args and max_sym_args and size_sym_args:
                result += ['--sym-args', str(min_sym_args),
                           str(max_sym_args), str(size_sym_args)]

        return result

    def create_klee_command(self, arg_list):
        klee_command = ['klee']
        if arg_list:
            klee_command += ['--posix-runtime', '-libc=uclibc']

        return klee_command + [self.runner.DOCKER_OBJECT_FILE] + arg_list

    def run_llvm(self):
        code_file = self.runner.DOCKER_CODE_FILE
        object_file = self.runner.DOCKER_OBJECT_FILE
        llvm_command = ['/usr/bin/clang-3.4',
                        '-I', '/src/klee/include', '-emit-llvm', '-c', '-g',
                        code_file, '-o', object_file]
        self.runner.run_with_docker(llvm_command)

    def run_klee(self, arg_list):
        # Compile code with LLVM-GCC
        self.run_llvm()

        # Analyse code with KLEE
        klee_command = self.create_klee_command(arg_list)
        klee_output = self.runner.run_with_docker(klee_command)

        return klee_command, klee_output

    def process(self):
        klee_command, klee_output = self.run_klee(self.generate_arguments())
        return {
            'command': ' '.join(klee_command),
            'output': klee_output
        }
