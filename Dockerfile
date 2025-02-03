
FROM python:3.10 as requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN poetry self add poetry-plugin-export && poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM python:3.10

WORKDIR /code

COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /code/

ARG RENDER_EXTERNAL_HOSTNAME
# This finds instances of the placeholder domain and replaces them with the actual domain
RUN grep -rl "your-app-url.com" . | xargs sed -i "s/your-app-url.com/${RENDER_EXTERNAL_HOSTNAME}/g"

# The Blueprint file can inject the hostname into the environment, but source code expects http://hostname format
ARG WEAVIATE_HOSTNAME
ENV WEAVIATE_HOST=http://${WEAVIATE_HOSTNAME}

# Render and Heroku use PORT, Azure App Services uses WEBSITES_PORT, Fly.io uses 8080 by default
CMD ["sh", "-c", "uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-${WEBSITES_PORT:-8080}}"]
