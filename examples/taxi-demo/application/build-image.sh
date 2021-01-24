#!/usr/bin/env bash
#!/bin/bash

set -e

#docker build -t edgify:0.1.0 ./base
docker build -t taxi-exp:0.0.1 ./taxi_exp
