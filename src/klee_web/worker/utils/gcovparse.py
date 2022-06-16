#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# ---- Taken from gcovparse package METADATA ----
# Metadata-Version: 2.1
# Name: gcovparse
# Version: 0.0.4
# Summary: gcov to json
# Home-page: http://github.com/codecov/gcov-parse
# Author: @codecov
# Author-email: hello@codecov.io
# License: http://www.apache.org/licenses/LICENSE-2.0
# Keywords: coverage
# Classifier: Development Status :: 4 - Beta
# Classifier: Environment :: Plugins
# Classifier: Intended Audience :: Developers
# Classifier: License :: OSI Approved :: Apache Software License
# Classifier: Topic :: Software Development :: Testing

# A modified version of gcovparse available for python2.7,
# now compatible with python3
# This will return all code lines with hit: null/0/n

def gcovparse(combined):
    # clean and strip lines
    assert ':Source:' in combined, 'gcov file is missing ":Source:" line(s)'
    files = filter(lambda f: f != '',
                   combined.strip().split("0:Source:"))
    next(files)
    reports = list(map(_part, files))
    return reports


# Processing a code file gcov returned
def _part(chunk):
    report = {
        "file": chunk.split('\n', 1)[0],
        "lines": [d for li in chunk.strip().split('\n')[1:]
                  if (d := _line(li)) is not None]
    }
    return report


# Processing each code line
# modified to always return every code line including those not found
# within .bb file
def _line(li):
    line = li.split(':', 2)
    if len(line) != 3:
        return
    hit, line, data = tuple(line)
    if int(line) <= 0:
        return
    if '#' in hit and data.strip() == '}':
        # ignore lines #####:   33:}
        return
    elif '-' in hit:
        return dict(line=int(line.strip()), hit=None)
    else:
        return dict(line=int(line.strip()),
                    hit=0 if '#' in hit or '=' in hit
                    else int(hit.strip()))
