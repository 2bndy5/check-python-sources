FROM ubuntu:latest

# WORKDIR option is set by the github action to the environment variable GITHUB_WORKSPACE.
# See https://docs.github.com/en/actions/creating-actions/dockerfile-support-for-github-actions#workdir

LABEL repository="https://github.com/2bndy5/check-python-sources"
LABEL maintainer="2bndy5"

RUN apt-get update
RUN apt-get -y install python3-pip
# RUN python3 -m pip install --upgrade pip

COPY python_linter/ /pkg/python_linter/
COPY setup.py /pkg/setup.py
RUN python3 -m pip install /pkg/

# github action args use the CMD option
# See https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runsargs
# also https://docs.docker.com/engine/reference/builder/#cmd
ENTRYPOINT [ "python3", "-m", "python_linter.run" ]
