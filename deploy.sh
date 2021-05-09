#!/bin/bash
# This script simplifies deploying the script as a Lambda function

###### IMPORTANT ######
# Create a virtual environment first. When running this script for the first time,
# uncomment the first 3 lines. Recomment them when running this script again!!

#python -m virtualenv deploy
#source deploy/bin/activate
#python -m pip install -r requirements.txt
cd deploy/lib/python3.8/site-packages
zip -r9 ${OLDPWD}/lambda.zip .
cd $OLDPWD
zip -g lambda.zip nightcorei.py
