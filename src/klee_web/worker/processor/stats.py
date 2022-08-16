import os
import csv
from io import StringIO
from worker.processor.base import BaseProcessor


class StatsProcessor(BaseProcessor):
    name = "stats"
    notify_message = ""

    def __init__(self, runner, args):
        BaseProcessor.__init__(self, runner, args)
        self.klee_result_dir = os.path.join(runner.DOCKER_MOUNT_DIR,
                                            'klee-out-0')

    def process(self):
        klee_stats_command = ['klee-stats', '--table-format', 'csv',
                              self.klee_result_dir]
        stats_csv = self.runner.run_with_docker(klee_stats_command)
        stats_csv = csv.DictReader(StringIO(stats_csv))

        # Process the CSV stats into a list of pairs (stat key, list of stats)
        # each stat in the list referring to each passed klee-out folder
        first = True
        for row in stats_csv:
            if first:
                combined = [(key, []) for key in row]
                first = False
            [combined[ind][1].append(item[1]) for ind, item
             in enumerate(row.items())]

        return combined[1:]
