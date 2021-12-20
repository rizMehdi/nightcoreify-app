#!/bin/bash
# This script simplifies deploying nightcoreify in AWS Lambda

###### IMPORTANT ######
# Create a virtual environment first -- when running this script for the first time,
# uncomment the 4 commented lines below. Recomment them when running this script in the future!!

#python3 -m pip install virtualenv
#python3 -m virtualenv deploy
#source deploy/bin/activate
#python3 -m pip install -r requirements.txt
rm -f lambda.zip
cd deploy/lib/python3.8/site-packages
zip -r9 ${OLDPWD}/lambda.zip . -x pip\* dotenv python_dotenv\* googleapiclient/discovery_cache/documents/\*
zip ${OLDPWD}/lambda.zip googleapiclient/discovery_cache/documents/youtube.v3.json
cd $OLDPWD
zip -g lambda.zip nightcorei.py
