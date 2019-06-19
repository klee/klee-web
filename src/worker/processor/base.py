class BaseProcessor():
    name = None
    notify_message = None

    def __init__(self, runner, args):
        self.runner = runner
        self.args = args

    @property
    def enabled(self):
        return True

    def process(self):
        raise NotImplementedError()
