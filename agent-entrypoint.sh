#!/bin/bash

# run the server
uwsgi --http 0.0.0.0:5500 --chdir /code/fogify --pyargv "--agent --agent-ip=${HOST_IP}" --callable app --processes 2 --threads 2 --module main:app

