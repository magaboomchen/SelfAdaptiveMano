#!/bin/bash

cloc --exclude-dir=builtin_pb,__pycache__,.pytest_cache,.vscode  --exclude-ext=pyc .
