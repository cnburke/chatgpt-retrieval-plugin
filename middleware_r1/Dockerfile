FROM python:3.9

WORKDIR /app

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Copy the pyproject.toml and poetry.lock files
COPY ../pyproject.toml ../poetry.lock ./

# Install dependencies using Poetry
RUN poetry install --no-root

# Copy application code
COPY middleware_r1/main.py ./

# Expose the port FastAPI runs on
EXPOSE 8001

# Start the application using Poetry
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]