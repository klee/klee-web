# -*- encoding: utf-8 -*-
"""Output statistics logged by Klee."""

# use '/' to mean true division and '//' to mean floor division
from __future__ import division

import os
import re

from operator import itemgetter


Legend = [
    ('Instrs', 'number of executed instructions'),
    ('Time', 'total wall time (s)'),
    ('TUser', 'total user time'),
    ('ICov', 'instruction coverage in the LLVM bitcode (%)'),
    ('BCov', 'branch coverage in the LLVM bitcode (%)'),
    ('ICount', 'total static instructions in the LLVM bitcode'),
    ('TSolver', 'time spent in the constraint solver'),
    ('States', 'number of currently active states'),
    ('Mem', 'megabytes of memory currently used'),
    ('Queries', 'number of queries issued to STP'),
    ('AvgQC', 'average number of query constructs per query'),
    ('Tcex', 'time spent in the counterexample caching code'),
    ('Tfork', 'time spent forking'),
    ('TResolve', 'time spent in object resolution'),
]


def getLogFile(path):
    """Return the path to run.stats."""
    return os.path.join(path, 'run.stats')


class LazyEvalList:
    """Store all the lines in run.stats and eval() when needed."""

    def __init__(self, lines):
        # The first line in the records contains headers.
        self.lines = lines[1:]

    def __getitem__(self, index):
        if isinstance(self.lines[index], str):
            self.lines[index] = eval(self.lines[index])
        return self.lines[index]

    def __len__(self):
        return len(self.lines)


def getMatchedRecordIndex(records, column, target):
    """Find target from the specified column in records."""
    target = int(target)
    lo = 0
    hi = len(records) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if column(records[mid]) <= target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def aggregateRecords(records):
    # index for memUsage and stateCount in run.stats
    memIndex = 6
    stateIndex = 5

    # maximum and average memory usage
    memValues = list(map(itemgetter(memIndex), records))
    maxMem = max(memValues) / 1024 / 1024
    avgMem = sum(memValues) / len(memValues) / 1024 / 1024

    # maximum and average number of states
    stateValues = list(map(itemgetter(stateIndex), records))
    maxStates = max(stateValues)
    avgStates = sum(stateValues) / len(stateValues)

    return (maxMem, avgMem, maxStates, avgStates)


def stripCommonPathPrefix(paths):
    paths = map(os.path.normpath, paths)
    paths = [p.split('/') for p in paths]
    zipped = zip(*paths)
    i = 0
    for i, elts in enumerate(zipped):
        if len(set(elts)) > 1:
            break
    return ['/'.join(p[i:]) for p in paths]


def getKeyIndex(key, labels):
    """Get the index of the specified key in labels."""

    def normalizeKey(key):
        return re.split('\W', key)[0]

    for i, title in enumerate(labels):
        if normalizeKey(title) == normalizeKey(key):
            return i
    else:
        raise ValueError('invalid key: {0}'.format(key))


def getKleeOutDirs(dirs):
    kleeOutDirs = []
    for dir in dirs:
        if os.path.exists(os.path.join(dir, 'info')):
            kleeOutDirs.append(dir)
        else:
            for root, subdirs, _ in os.walk(dir):
                for d in subdirs:
                    path = os.path.join(root, d)
                    if os.path.exists(os.path.join(path, 'info')):
                        kleeOutDirs.append(path)
    return kleeOutDirs


def getLabels(pr):
    if pr == 'all':
        labels = ('Instrs', 'Time(s)', 'ICov(%)', 'BCov(%)', 'ICount',
                  'TSolver(%)', 'States', 'maxStates', 'avgStates', 'Mem(MB)',
                  'maxMem(MB)', 'avgMem(MB)', 'Queries', 'AvgQC', 'Tcex(%)',
                  'Tfork(%)')
    elif pr == 'reltime':
        labels = ('Time(s)', 'TUser(%)', 'TSolver(%)',
                  'Tcex(%)', 'Tfork(%)', 'TResolve(%)')
    elif pr == 'abstime':
        labels = ('Time(s)', 'TUser(s)', 'TSolver(s)',
                  'Tcex(s)', 'Tfork(s)', 'TResolve(s)')
    elif pr == 'more':
        labels = ('Instrs', 'Time(s)', 'ICov(%)', 'BCov(%)', 'ICount',
                  'TSolver(%)', 'States', 'maxStates', 'Mem(MB)', 'maxMem(MB)')
    else:
        labels = ('Instrs', 'Time(s)', 'ICov(%)',
                  'BCov(%)', 'ICount', 'TSolver(%)')
    return labels


def getRow(record, stats, pr):
    """Compose data for the current run into a row.
    
    The record holds the following information:
    ('Instructions','FullBranches','PartialBranches','NumBranches','UserTime','NumStates',
    'MallocUsage','NumQueries','NumQueryConstructs','NumObjects','WallTime','CoveredInstructions',
    'UncoveredInstructions','QueryTime','SolverTime','CexCacheTime','ForkTime','ResolveTime',
    'QueryCexCacheMisses','QueryCexCacheHits',)
    """
    I, BFull, BPart, BTot, T, St, Mem, QTot, QCon, \
        _, Treal, SCov, SUnc, _, Ts, Tcex, Tf, Tr, _, _ = record
    maxMem, avgMem, maxStates, avgStates = stats

    # special case for straight-line code: report 100% branch coverage
    if BTot == 0:
        BFull = BTot = 1

    Mem = Mem / 1024 / 1024
    AvgQC = int(QCon / max(1, QTot))

    if pr == 'all':
        row = (I, Treal, 100 * SCov / (SCov + SUnc),
               100 * (2 * BFull + BPart) / (2 * BTot), SCov + SUnc,
               100 * Ts / Treal, St, maxStates, avgStates,
               Mem, maxMem, avgMem, QTot, AvgQC,
               100 * Tcex / Treal, 100 * Tf / Treal)
    elif pr == 'reltime':
        row = (Treal, 100 * T / Treal, 100 * Ts / Treal,
               100 * Tcex / Treal, 100 * Tf / Treal,
               100 * Tr / Treal)
    elif pr == 'abstime':
        row = (Treal, T, Ts, Tcex, Tf, Tr)
    elif pr == 'more':
        row = (I, Treal, 100 * SCov / (SCov + SUnc),
               100 * (2 * BFull + BPart) / (2 * BTot),
               SCov + SUnc, 100 * Ts / Treal,
               St, maxStates, Mem, maxMem)
    else:
        row = (I, Treal, 100 * SCov / (SCov + SUnc),
               100 * (2 * BFull + BPart) / (2 * BTot),
               SCov + SUnc, 100 * Ts / Treal)
    return row


def generate_stats(dirs):
    dirs = getKleeOutDirs(dirs)
    # read contents from every run.stats file into LazyEvalList
    data = [LazyEvalList(list(open(getLogFile(d)))) for d in dirs]
    if len(data) > 1:
        dirs = stripCommonPathPrefix(dirs)

    # attach the stripped path
    data = list(zip(dirs, data))
    pr = 'NONE'
    labels = getLabels(pr)
    # build the main body of the table
    table = []
    totRecords = []  # accumulated records
    totStats = []  # accumulated stats
    for path, records in data:
        row = []
        stats = aggregateRecords(records)
        totStats.append(stats)
        row.extend(getRow(records[-1], stats, pr))
        totRecords.append(records[-1])
        table.append(row)
    return zip(labels, row)
