class DummyStorage():
    BUCKET = 'klee-output'

    def __init__(self):
        pass

    def store_file(self, file_path):
        return "File upload disabled in development"
