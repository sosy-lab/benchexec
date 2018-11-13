# This is a Docker image for running the tests.
# It should be pushed to registry.gitlab.com/sosy-lab/software/benchexec/test
# and will be used by CI as declared in .gitlab-ci.yml.
#
# Commands for updating the image:
# docker build -t registry.gitlab.com/sosy-lab/software/benchexec/test:python-3.2 - < test/Dockerfile.python-3.2
# docker push registry.gitlab.com/sosy-lab/software/benchexec/test

FROM python:3.2

RUN apt-get update && apt-get install -y \
  sudo

RUN pip install \
  # Coverage >= 4.0 doesn't support Python 3.2
  coverage==3.7.1 \
  # Workaround: use lxml 4.0.0 because 4.1.0 fails on Python 3.2
  lxml==4.0.0 \
  nose \
  # Workaround: use PyYAML 3.12 because 3.13 does not support Python 3.2
  pyyaml==3.12 \
  tempita==0.5.2
