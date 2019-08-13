echo "Running Python Unit tests"

# export environmental variables:
. /etc/profile.d/klee-web-environment.sh

# run tests:
cd /titb/src/klee_web && python -m unittest discover -s worker/tests/ -p 'test_*.py'
