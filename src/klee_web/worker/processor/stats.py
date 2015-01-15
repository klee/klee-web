import os
from worker.processor.base import BaseProcessor
from worker.utils import klee_stats


class StatsProcessor(BaseProcessor):
    name = "stats"
    notify_message = ""

    def __init__(self, runner, args):
        BaseProcessor.__init__(self, runner, args)

    def process(self):
        klee_last = os.path.join(self.runner.tempdir, 'klee-out-0')
        return klee_stats.generate_stats([klee_last])
