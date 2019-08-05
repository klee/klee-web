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

_Run "Running Flake8 against Python Code" "sudo docker run --rm -it -v /titb/:/titb/ e2e_test /bin/bash /titb/src/klee_web/tests/python_tests/flake8_test.sh"

_Run "Checking that loading the homepage returns 200 OK" "sudo docker run --rm -it -e WEBPAGE=$MAIN_WEBPAGE --network $(sudo docker network ls | grep bridge | sed -n '2 p' | awk '{print $2}') -v /titb/src/klee_web/tests/python_tests/:/titb/src/klee_web/tests/python_tests/ e2e_test /bin/bash /titb/src/klee_web/tests/python_tests/webserver_test.sh "

_Run "JavaScript e2e tests" "sudo docker run --rm -it -e WEBPAGE=$MAIN_WEBPAGE -e ADMIN_PASSWORD=$ADMIN_PASSWORD --network $(sudo docker network ls | grep bridge | sed -n '2 p' | awk '{print $2}') -v /titb/src/klee_web/tests/js_tests/test_files/:/titb/src/klee_web/tests/js_tests/test_files/ e2e_test_js"
