#!/bin/bash -e

_Box () {
    str="$@"
    len=$((${#str}+4))
    for i in $(seq $len); do echo -n '*'; done;
    echo; echo "* "$str" *";
    for i in $(seq $len); do echo -n '*'; done;
    echo
}

_Done() {
   echo -e "\n\e[32mDone\n"
   tput sgr0
}

_Run() {
    _Box $1
    echo ${*:2}
    eval ${*:2}
    _Done
}

DIR="$( cd "$( dirname "$0" )" && pwd )"

_Run "Running Flake8 against Python Code" "flake8 --ignore=E722 --max-complexity 12 --exclude=migrations $DIR"

_Run "Running Python Unit tests" "(source /src/worker/env/bin/activate && cd /titb/src/klee_web && /src/python_runner.sh python -m unittest discover -s worker/tests/ -p 'test_*.py')"

_Run "Waiting for webserver to come up" "sleep 10"

_Run "Checking that loading the homepage returns 200 OK" "http --check-status http://localhost/ > /dev/null"

_Run "Running E2E webdriver tests" "cd /titb/src/klee_web/tests/ && npm test"
