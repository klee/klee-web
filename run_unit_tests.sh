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

_Run "Running Python Unit tests" "(sudo docker run --rm -it --network $(sudo docker network ls | grep bridge | sed -n '2 p' | awk '{print $2}') -v /var/run/docker.sock:/var/run/docker.sock -v /etc/profile.d/:/etc/profile.d/ -v /tmp/:/tmp/ -v /titb/:/titb/ celery_worker /bin/bash /titb/src/klee_web/tests/python_tests/unit_tests.sh)"
