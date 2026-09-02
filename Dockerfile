FROM python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir . && \
    addgroup --system --gid 10001 catalog && \
    adduser --system --uid 10001 --ingroup catalog --home /home/catalog catalog && \
    mkdir -p /data/output /data/cache && chown -R catalog:catalog /data /home/catalog

USER 10001:10001
WORKDIR /data
ENV HL_CATALOG_OUTPUT_DIR=/data/output \
    HL_CATALOG_CACHE_DIR=/data/cache

ENTRYPOINT ["hl-catalog"]
CMD ["--help"]
