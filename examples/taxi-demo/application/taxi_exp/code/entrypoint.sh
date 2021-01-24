#!/bin/bash


# i commit my migration files to git so i dont need to run it on server
# ./manage.py makemigrations app_name

#run crontabs
declare -px > /tmp/.env
chmod 0644 /tmp/.env
if [ "$NODE_TYPE" == "IOT_NODE" ]
then
    python collect_metrics.py
elif [ "$NODE_TYPE" == "EDGE_NODE" ]
then
    crontab cronjobs
    cron
    python edge_server.py
else
    python server.py
fi

# run the server
#uwsgi server.ini

# kafka consumer
