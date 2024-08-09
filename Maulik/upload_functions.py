###############################################################################
# This script contains functions for writing data files to Domino and using 
# the WebHDFS Proxy to write to Data Hub
###############################################################################
 
###############################################################################
# Load packages
###############################################################################
import csv
import json
import os
import pandas as pd
import requests
 
# dominoPut function is used to write log files in real-time into Domino directories
def dominoPut(projectpath,log_info):
	s = requests.Session()
	#Bearer = "Bearer " + tidAuth() + """""" 
	headers = {"X-Domino-Api-Key":os.environ["DOMINO_USER_API_KEY"]}
	#url='https://apigw.newyorklife.com/eis-domino-webhdf-pxy/gateway/default/webhdfs/v1'+hdfsfile+'?op=CREATE&overwrite=true'
	url = os.environ['DOMINO_API_HOST'] + '/v1/projects/' + projectpath  #username/project_name/path'
	#print(url)
	r = s.put(url, verify = False, headers = headers, data='\t'.join(log_info))
	#r = s.put(url, verify=False,headers=headers,data=df)
	print(r.status_code)
	if r.status_code > 300:
		insert_error = "Error in Call"
		print(insert_error) # ML01 For the logs
	s.close()
	return(r.status_code)
 
# tidAuth is used to generate an access token used for the WebHDFS proxy
def tidAuth():
	'''Authentication using ACF2ID and password'''
	#tid=acf2id.tid
	#pwd=acf2id.pwd
	url = 'https://qaint.apigw.newyorklife.com/eis-oauthprovider-prxy/access_token'
	s = requests.Session()
	headers = {"grant_type":"client_credentials","scope":"READ","client_id":"8b72553408be4402b2060c4b1c3cbcac","client_secret":"8910568E250343878EE509c641a290c2" }
	r = s.get(url, verify=False, headers=headers)
	#auth=(tid, pwd)
	print(r.json())
	return r.json()["access_token"]
 
# hdfsPUT is the PUT function of the WebHDFS proxy
# The function takes in a Pandas dataframe and writes it to a CSV file with the 
# name specified as hdfsfile
def hdfsPUT(hdfsfile,df):
	s = requests.Session()
	Bearer = "Bearer " + tidAuth() + """""" 
	headers = {"Authorization":Bearer,"X-HTTP-Method-Override":"PUT" }  
	url='https://qa.apigw.newyorklife.com/eis-domino-webhdf-pxy/gateway/default/webhdfs/v1'+hdfsfile+'?op=CREATE&overwrite=true'
	print(url)
	r = s.put(url, verify=False,headers=headers,data=df.to_csv(index=False, header=False))
	#r = s.put(url, verify=False,headers=headers,data=df)
	print(r.status_code)
	if r.status_code > 300:
		insert_error = "Error in Call"
		print(insert_error) # ML01 For the logs
	s.close()
	return(r.status_code)