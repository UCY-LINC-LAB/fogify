#!/usr/bin/env bash
for NODE in $(docker node ls --format '{{.Hostname}}');
do echo -e "${NODE} - $(docker node inspect --format '{{.Status.Addr}}' "${NODE}")"; done