import json
import os
import time
import boto3
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key, Attr
##import requirements
import requests
import logging

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

checker_slack_param_name = 'CHECKER_SLACK_POST_URL'
ssm = boto3.client('ssm')
ssm_res = ssm.get_parameters(
    Names = [
        checker_slack_param_name
    ],
    WithDecryption = True
)
SLACK_POST_URL = ssm_res['Parameters'][0]['Value']
  

def send_alert(error_msg,topic_arn):
 subject = 'sitechecker alert'
 msg = error_msg 
 client = boto3.client('sns')

 request = {
     'TopicArn': topic_arn,
     'Message': msg,
     'Subject': subject
 }
 response = client.publish(**request)

def send_slack(error_msg):
 logger.info('send slack message')
 slackmsg = {
   "text": error_msg,
   "channel": 'monitoring',
   "icon": ':katty:'
 }
 slack_res = requests.post(SLACK_POST_URL,data=json.dumps(slackmsg))
 logger.info('slack response '+str(slack_res))


def put_result(record):
 dynamodb = boto3.resource('dynamodb')
 table = dynamodb.Table('checkresult')
 table.put_item(Item = record)

def checker(event, context):
 url = str(event['url'])
 retry_cnt = int(event['retry_cnt'])
 retry_interval = int(event['retry_interval'])
 slow_res_time = float(event['slow_res_time'])
 topic_arn = str(event['topic_arn'])

 success = 0
  
 record = {}
 date = datetime.now() + timedelta(hours=9)
 expire_date = long(time.time() + 86400)
 response_timeout = slow_res_time
 for i in range(retry_cnt):
  logger.info('====== HTTP GET FROM '+url+' ==========')
  try:
   res = requests.get(url,timeout=response_timeout)
   if res.status_code == 200 and res.elapsed.total_seconds() <= slow_res_time:
     logger.info('======= HTTP GET SUCCESS ==========')
     success = 1
     break
   else:
     logger.info('======= HTTP GET ERROR(Status Code is invalid) ==========')
     time.sleep(retry_interval)
     continue
  except Exception as ex:
     logger.info('====== HTTP GET ERROR(Exception) ==========')
     error_msg = "site("+url+") is down. "+str(ex)
     success = -1

 if success == 1:
   record = {
            "url": url,
            "date": date.strftime("%Y/%m/%d %H:%M"),
            "status": res.status_code,
            "time": str(res.elapsed.total_seconds()),
            "ttl": expire_date
   }
 elif success == 0:
   logger.info('========== HTTP Status invalid  ==========')
   error_msg = url+" status code is "+str(res.status_code)+". response time is "+str(res.elapsed.total_seconds())+" sec"
   record = {
            "url": url,
            "date": date.strftime("%Y/%m/%d %H:%M"),
            "status": res.status_code,
            "time": str(res.elapsed.total_seconds()),
            "ttl": expire_date
   }
   send_alert(error_msg,topic_arn)
   send_slack(error_msg)
 elif success == -1:
   logger.info('========== Connection Exception  ==========')
   record = {
            "url": url,
            "date": date.strftime("%Y/%m/%d %H:%M"),
            "status": 0,
            "time": " ",
            "ttl": expire_date
   }
   send_alert(error_msg,topic_arn)
   send_slack(error_msg)
 put_result(record)
