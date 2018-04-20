import json
import time
import boto3
from boto3.dynamodb.conditions import Key, Attr
import logging
import os

logger = logging.getLogger()
logLevelTable={
               'DEBUG':logging.DEBUG,
               'INFO':logging.INFO,
               'WARNING':logging.WARNING,
               'ERROR':logging.ERROR,
               'CRITICAL':logging.CRITICAL
              }
if 'logging_level' in os.environ and os.environ['logging_level'] in logLevelTable :
    logLevel=logLevelTable[os.environ['logging_level']]
else:
    logLevel=logging.INFO
logger.setLevel(logLevel)

def get_checkenv():
 dynamodb = boto3.resource('dynamodb')
 table = dynamodb.Table('checkenv')
 response = table.scan()
 checkenvs = response["Items"]
 return checkenvs

def dispatcher(event, context):
 logger.info ('dispatcher lambda function start')
 checkenvs = get_checkenv()

 for checkenv  in checkenvs:
  try:
   if checkenv['status'] == 'enable':
    payload = {
      "url": str(checkenv['url']),
      "retry_cnt": int(checkenv['retry_cnt']),
      "retry_interval": int(checkenv['retry_interval']),
      "slow_res_time": float(checkenv['slow_res_time']),
      "topic_arn": str(checkenv['topic_arn'])
    }

    logger.info('payload variable '+ str(payload))
    logger.info('invoke checker lambda function ')

    client = boto3.client('lambda')
    client.invoke(
         FunctionName='checker',
         InvocationType="Event",
         Payload=json.dumps(payload)
    )
  
  except Exception as ex:
   logger.error('Exception '+str(ex))
