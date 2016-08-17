import os
import shutil


class DummyStorage():
    BUCKET = 'klee-output'
    DOCKER_MOUNT_DIR = '/tmp/'

    def __init__(self):
        pass

    def store_file(self, file_path):
        # File_path is a path internal to the docker container
        # that may or may not exist when the user wants to download it
        base_name = os.path.basename(file_path)
        # Copy to somewhere that does not get destroyed when docker terminates
        final_path = os.path.join(self.DOCKER_MOUNT_DIR, base_name)
        shutil.copy(file_path, final_path)
        return "/jobs/dl/{0}".format(base_name)
