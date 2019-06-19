import os
from src.worker.processor.base import BaseProcessor
from src.worker.utils import klee_stats


class StatsProcessor(BaseProcessor):
    name = "stats"
    notify_message = ""

    def __init__(self, runner, args):
        BaseProcessor.__init__(self, runner, args)

    def process(self):
        klee_last = os.path.join(self.runner.tempdir, 'klee-out-0')
        return list(klee_stats.generate_stats([klee_last]))
