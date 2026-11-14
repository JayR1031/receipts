# syntax=docker/dockerfile:1
# The api image. The chosen cloud's container service runs it (infra/terraform: api_image, api_port).
FROM python:3.12-slim AS build
ARG UV_VERSION=0.11.24
RUN pip install --no-cache-dir "uv==${UV_VERSION}"
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-default-groups

FROM python:3.12-slim
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA} PATH="/app/.venv/bin:${PATH}" GRADIO_ANALYTICS_ENABLED=False
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=build /app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "receipts.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
