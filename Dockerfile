FROM python:3.11.12-slim as requirements-stage

WORKDIR /tmp

# Install Poetry
RUN pip install poetry

# Add your pyproject + lock file
COPY ./pyproject.toml ./poetry.lock* /tmp/

# Add Poetry plugin and export requirements
RUN poetry self add poetry-plugin-export && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes

# --- Runtime stage --- 
FROM python:3.11.12-slim

WORKDIR /code

# Install system dependencies for building `tiktoken`
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    gcc \
    && curl https://sh.rustup.rs -sSf | sh -s -- -y \
    && apt-get clean

# Add Rust to PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Copy requirements from build stage
COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

RUN echo "======== REQUIREMENTS.TXT ========" >&2 && cat /code/requirements.txt >&2 && echo "==================================" >&2

# Install everything — now works even for source-built packages like `tiktoken`
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy source code
COPY . /code/

# Replace app URL
ARG RENDER_EXTERNAL_HOSTNAME
RUN grep -rl "your-app-url.com" . | xargs sed -i "s/your-app-url.com/${RENDER_EXTERNAL_HOSTNAME}/g"

# Run app
CMD ["sh", "-c", "uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-${WEBSITES_PORT:-8080}}"]