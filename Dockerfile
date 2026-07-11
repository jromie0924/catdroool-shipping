FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIPENV_VENV_IN_PROJECT=1

RUN pip install pipenv

WORKDIR /app
COPY Pipfile Pipfile.lock ./
# PIPENV_VENV_IN_PROJECT puts the virtualenv at /app/.venv so the runtime stage can copy
# it wholesale and leave pipenv itself behind.
RUN pipenv sync


FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY src/ src/
COPY html/ html/

# generate_report() writes the CSVs and the workbook under output/, and the log handler
# writes under logs/. Both sit on the task's ephemeral disk and disappear with it -- the
# files leave the container as email attachments.
RUN useradd --create-home --uid 10001 catdroool \
 && mkdir -p output logs \
 && chown -R catdroool:catdroool /app

USER catdroool

CMD ["python", "src/app.py"]
