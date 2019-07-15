FROM python:3.7-slim
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=true

RUN pip install pipenv --no-cache-dir

# Allows docker to cache installed dependencies between builds
COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock
RUN pipenv install --deploy --system

# Adds our application code to the image
COPY . code
WORKDIR code

EXPOSE 8000

# Migrates the database, uploads staticfiles, and runs the production server
CMD ./manage.py migrate && \
    ./manage.py collectstatic --noinput && \
    newrelic-admin run-program gunicorn --bind 0.0.0.0:$PORT --access-logfile - kerckhoff.wsgi:application
