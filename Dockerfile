FROM python:3.7-slim
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=true

RUN pip install pipenv --no-cache-dir

# Allows docker to cache installed dependencies between builds
COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock
COPY requirements.txt requirements.txt
RUN apt-get -y update && apt-get -y install libpq-dev gcc zlib1g
ENV LIBRARY_PATH=/lib:/usr/lib
RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install importlib-metadata==4.13.0
RUN pip install -r requirements.txt

# Adds our application code to the image
COPY . code
WORKDIR code

EXPOSE 8000

# Migrates the database, uploads staticfiles, and runs the production server
CMD ./manage.py migrate && \
    ./manage.py collectstatic --noinput && \
    newrelic-admin run-program gunicorn --bind 0.0.0.0:$PORT --access-logfile - kerckhoff.wsgi:application
