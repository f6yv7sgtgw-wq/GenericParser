FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GENERIC_PARSER_HOST=0.0.0.0 \
    GENERIC_PARSER_PORT=8000

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir .
RUN mkdir -p /app/data/fixtures

EXPOSE 8000
CMD ["generic-parser-web"]
