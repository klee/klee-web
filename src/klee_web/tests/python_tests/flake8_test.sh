#!/bin/bash

echo "Running Flake8 against Python Code"
flake8 --ignore=E722 --max-complexity 12 --exclude=migrations /titb/src/
