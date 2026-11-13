# One thin image for every service scenario.
#
# Build from the repository root:
#   docker build -f docker/Dockerfile -t tensorgoat:local .
#
# The container only *serves* a scenario. Artefacts and the install secret are
# generated on the host by `tensorgoat create <scenario> --docker` and mounted
# read-only at /data.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TENSORGOAT_HOME=/data

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY tensorgoat ./tensorgoat
RUN pip install .

RUN useradd --create-home --uid 10001 goat
USER goat

# Inside a container the service must listen on the container's interface;
# docker/compose.yml publishes the port on the host's 127.0.0.1 only.
ENTRYPOINT ["python", "-m", "tensorgoat.core.serve"]
