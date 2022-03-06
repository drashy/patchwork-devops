#!/bin/bash

mkdir pwdevops
cd pwdevops

pulumi new aws-python -y
pulumi config set aws:region eu-west-1

cp -r ../app ../__main__.py .

venv/bin/pip3 install -r ../requirements.txt

pulumi up -f
