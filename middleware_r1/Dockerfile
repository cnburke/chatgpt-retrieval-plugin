# Use Python 3.10+ to match your project requirements
FROM python:3.10

WORKDIR /app

# Install Poetry explicitly
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    export PATH="/root/.local/bin:$PATH"

# Ensure Poetry is available in the current shell session
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies using Poetry
RUN poetry install --no-root

# Copy app files
COPY middleware_r1/main.py ./

# Expose port
EXPOSE 8001

# Start the application
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]