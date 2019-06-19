import os
import subprocess
from src.worker.processor.base import BaseProcessor

from src.worker.storage.dummy_storage import DummyStorage
from src.worker.storage.s3_storage import S3Storage

DEVELOPMENT = os.environ.get('DEVELOPMENT') is not None


class UploadProcessor(BaseProcessor):
    name = 'url'
    notify_message = 'Uploading KLEE output directory'

    def __init__(self, runner, args):
        BaseProcessor.__init__(self, runner, args)
        self.runner = runner
        self.storage = DummyStorage() if DEVELOPMENT else S3Storage()

    def compress_output(self, output_tar_filename):
        tar_command = ['tar', '-zcvf', output_tar_filename, 'klee-out-0']
        subprocess.check_output(tar_command, cwd=self.runner.tempdir)

    def upload_result(self, result_file_path):
        return self.storage.store_file(result_file_path)

    def process(self):
        file_name = 'klee-output-{}.tar.gz'.format(self.runner.task_id)
        compressed_output_path = os.path.join(self.runner.tempdir, file_name)

        self.compress_output(compressed_output_path)
        return self.upload_result(compressed_output_path)
