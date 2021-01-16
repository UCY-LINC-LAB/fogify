#!/bin/bash

# run the server
uwsgi --http 0.0.0.0:5000 --module main:app --chdir /code/fogify --pyargv="--controller" --callable app --processes 2 --threads 2
#uwsgi --http :5000 --wsgi-file main.py --master --chdir /code/fogify --pyargv=--controller --processes 2 --threads 2


