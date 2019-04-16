#!/bin/bash

echo "Loading data..."

docker-compose exec web ./manage.py loaddata fixture.json

echo "Done! Default superuser is 'admin' with password 'bruin111'"