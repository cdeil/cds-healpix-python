#!/bin/bash

# Build and deploy if the tests pass and
# the commit is tagged
if [[ $TRAVIS_TAG ]]; then
    ### Build the wheels ###
    $PIP install git+https://github.com/YannickJadoul/cibuildwheel.git@pip-19-stalling-workaround setuptools-rust
    export CIBW_BEFORE_BUILD="pip install setuptools-rust && curl https://sh.rustup.rs -sSf | sh -s -- -y"
    export CIBW_ENVIRONMENT='PATH="$HOME/.cargo/bin:$PATH"'
    cibuildwheel --output-dir dist
    ### Upload the wheels to PyPI ###
    $PIP install twine
    $PYTHON -m twine upload --repository-url https://upload.pypi.org/legacy/ dist/*.whl --skip-existing
fi