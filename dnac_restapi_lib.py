"""
DNAC Discovery Script.
Copyright (c) 2021 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
               https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

__author__ = "Phithakkit Phasuk"
__email__ = "phphasuk@cisco.com"
__version__ = "0.1.5"
__copyright__ = "Copyright (c) 2021 Cisco and/or its affiliates."
__license__ = "Cisco Sample Code License, Version 1.1"


import urllib3
import requests
import json
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning
import logging
import time
from time import strftime, localtime
import pandas as pd


class rest_api_lib:
    def __init__(self, dnac_ip, dnac_port, username, password):
        urllib3.disable_warnings(InsecureRequestWarning)  # disable insecure https warnings
        self.dnac_ip = dnac_ip
        self.dnac_port = dnac_port
        self.username = username
        self.password = password
        logging.debug('Initializing DNAC REST client for %s:%s', dnac_ip, dnac_port)
        self.get_token()


    def get_token(self):
        url = 'https://%s:%s/dna/system/api/v1/auth/token'%(self.dnac_ip, self.dnac_port)
        auth = HTTPBasicAuth(self.username, self.password)
        headers = {'content-type' : 'application/json'}
        logging.debug('Requesting DNAC authentication token from %s', url)
        try:
            response = requests.post(url, auth=auth, headers=headers, verify=False)
            response.raise_for_status()
            token = response.json()['Token']
            logging.info('Got DNAC authentication token; HTTP %s', response.status_code)
            self.token = token
            self.token_time = time.time()
            return
        except requests.exceptions.HTTPError as err:
            status_code = err.response.status_code if err.response is not None else 'unknown'
            logging.error('DNAC authentication failed with HTTP %s: %s', status_code, err, exc_info=True)
            raise SystemExit()
        except (requests.exceptions.RequestException, KeyError, ValueError) as err:
            logging.error('DNAC authentication request failed: %s', err, exc_info=True)
            raise SystemExit()

    def logout(self):
        """Logout from dnac"""
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'X-XSRF-TOKEN': self.token}
        url = "https://%s:%s/logout?nocache"%(self.dnac_ip, self.dnac_port)
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            logging.info(f'Logout from DNAC successful')
            logging.debug(f'Logout from DNAC successful response: {response}')
            return
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()

    def get_task_info(self, tid):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/task/{tid}"
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            info = response.json()['response']
            logging.info(f'Got Task Info for: {tid}')
            logging.debug(f'Task Info: {info}')
            return info
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()

    def get_discovery_info(self, did):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/discovery/{did}"
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            info = response.json()['response']
            logging.info(f'Got Discovery Info for: {did}')
            logging.debug(f'Task Info: {info}')
            return info
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def get_discovery_result(self, did):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = { 'x-auth-token': self.token,
                    'content-type': 'application/json' }
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/discovery/{did}/network-device"
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            info = response.json()['response']
            logging.info(f'Got Discovery Result for: {did}')
            logging.debug(f'Task Info: {info}')
            return info
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def delete_alldiscovery(self):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/discovery"
        try:
            response = requests.delete(url, headers=headers, verify=False)
            response.raise_for_status()
            logging.info(f'Delete all discovery tasks complete.')
            return
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def add_discovery_node(self, node_info):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        mount_point = 'dna/intent/api/v1/discovery'
        url = "https://%s:%s/%s"%(self.dnac_ip, self.dnac_port, mount_point)
        payload = { "cdpLevel": 1,
                    "lldpLevel": 1,
                    "discoveryType": "SINGLE",
                    "protocolOrder": "ssh,telnet", }
        for key, value in node_info.items():
            if 'List' in key and key != "ipAddressList":
                payload[key] = [value]
            else:
                payload[key] = value
        logging.info(f'Adding discovery task for: {node_info["ipAddressList"]}')
        logging.debug(f'Adding discovery task payload: {payload}')
        try:
            response = requests.post(url=url, headers=headers, data=json.dumps(payload), verify=False)
            response.raise_for_status()
            info = response.json()['response']
            logging.info(f'Adding discovery task done for: {node_info["ipAddressList"]}')
            logging.debug(f'Adding discovery ta: {info}')
            return info['taskId']
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def get_siteid_by_name(self, site_name):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = { 'x-auth-token': self.token,
                    'content-type': 'application/json' }
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/site?name=" + site_name
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            info = response.json()['response']
            logging.info(f'Got Site ID for: {site_name}')
            logging.debug(f'info: {info}')
            return info[0]['id']
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def get_count_discovery(self):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = { 'x-auth-token': self.token,
                    'content-type': 'application/json' }
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/discovery/count"
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            info = response.json()['response']
            logging.info(f'Got count of all discovery jobs')
            return info
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def get_all_discovery_jobs(self, num):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        recordsToReturn = num
        headers = { 'x-auth-token': self.token,
                    'content-type': 'application/json' }
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/discovery/1/{recordsToReturn}"
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            info = response.json()['response']
            logging.info(f'Got count of all discovery jobs')
            return info
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def update_existing_discovery_job(self, discoveryInfo, password):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = { 'x-auth-token': self.token,
                    'content-type': 'application/json' }
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/discovery"
        discoveryInfo['discoveryStatus'] = 'active'
        discoveryInfo['discoveryCondition'] = 'Yet to Start'
        discoveryInfo['passwordList'] = password
        discoveryInfo['enablePasswordList'] = password
        discoveryInfo['snmpRoCommunity'] = password
        discoveryInfo['snmpRwCommunity'] = password
        try:
            response = requests.put(url, headers=headers, data=json.dumps(discoveryInfo), verify=False)
            response.raise_for_status()
            info = response.json()['response']
            logging.info(f'Update existing discovery job')
            return info
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def assign_device_to_site(self, site_id, device_ip):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = { 'x-auth-token': self.token,
                    'content-type': 'application/json' }
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/system/api/v1/site/{site_id}/device"
        payload = { 'device': [ { 'ip': device_ip } ] }
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
            response.raise_for_status()
            info = response.json()
            executionStatusPath = info['executionStatusUrl']
            url = f"https://{self.dnac_ip}:{self.dnac_port}" + executionStatusPath
            while True:
                response = requests.get(url, headers=headers, verify=False)
                executionStatus = response.json()['status']
                if executionStatus == 'SUCCESS':
                    executionError = ''
                    logging.debug(f'{device_ip}-{site_id}-{executionStatusPath}: {executionStatus}, {executionError}')
                    break
                elif executionStatus == 'FAILURE':
                    executionError = response.json()['bapiError']
                    logging.debug(f'{device_ip}-{site_id}-{executionStatusPath}: {executionStatus}, {executionError}')
                    break
                else:
                    logging.debug(f'{device_ip}-{site_id}-{executionStatusPath}: {executionStatus}')
            return executionStatus, executionError
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def get_template_id(self, tname):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v2/template-programmer/template?name={tname}"
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            tid = response.json()['response'][0]['id']
            logging.info(f'Got Template Info for: {tname}')
            logging.info(f'Got Template ID: {tid}')
            logging.debug(f'Template Info: {response.json()["response"]}')
            return tid
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def deploy_template_v2(self, tname, targetInfo):
        '''
        Sample targetInfo:
            'targetInfo':  [
                {
                    'id': 'hostname',
                    'params': {
                        'key': 'value'
                    },
                    'type': 'MANAGED_DEVICE_HOSTNAME',
                    "resourceParams": [
                        {
                            "type": "MANAGED_DEVICE_HOSTNAME",
                            "scope": "RUNTIME",
                            "value": "hostname"
                        }
                    ]
                }
            ]
        '''
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v2/template-programmer/template/deploy"
        tempid = self.get_template_id(tname)
        payload = {
            'forcePushTemplate': 'True',
            'isComposite': 'False',
            'targetInfo': targetInfo,
            'templateId': tempid
        }
        logging.debug(f'Template Payload: {payload}')
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
            response.raise_for_status()
            info = response.json()['response']
            logging.debug(f'response={response.json()}')
            match response.status_code:
                case 202:
                    return True, response.json()['response']['taskId']
                case 400:
                    return False, response.json()['response']
                case _:
                    return False, response.json()['response']
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def get_tdeployment_info(self, did):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/template-programmer/template/deploy/status/{did}"
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            info = response.json()
            logging.info(f'Got Template Deployment Info for: {did}')
            logging.debug(f'Task Info: {info}')
            return info
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()

    
    def make_report_schedule(self, payload):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/data/reports"
        logging.info('Creating or scheduling report: name=%s, format=%s, schedule=%s',
                     payload.get('name'), payload.get('view', {}).get('format', {}).get('formatType'),
                     payload.get('schedule', {}).get('type'))
        try:
            response = requests.post(url, headers=headers, json=payload, verify=False)
            response.raise_for_status()
            logging.debug(f'Create report response: {response.text}')
            reportId = response.json()['reportId']
            logging.info('Report created successfully: reportId=%s, HTTP %s', reportId, response.status_code)
            return reportId
        except requests.exceptions.HTTPError as err:
            status_code = err.response.status_code if err.response is not None else 'unknown'
            logging.error('Report creation failed with HTTP %s: %s', status_code, err, exc_info=True)
            raise SystemExit()
        except (requests.exceptions.RequestException, KeyError, ValueError) as err:
            logging.error('Report creation request failed: %s', err, exc_info=True)
            raise SystemExit()


    def create_report(self, payload):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/data/reports"
        logging.info('Creating report: name=%s, format=%s, schedule=%s',
                     payload.get('name'), payload.get('view', {}).get('format', {}).get('formatType'),
                     payload.get('schedule', {}).get('type'))
        try:
            response = requests.post(url, headers=headers, json=payload, verify=False)
            response.raise_for_status()
            report = response.json()
            logging.info('Create report successful: reportId=%s, HTTP %s', report.get('reportId'), response.status_code)
            logging.debug('Create report response fields: %s', sorted(report.keys()))
            return report
        except requests.exceptions.HTTPError as err:
            status_code = err.response.status_code if err.response is not None else 'unknown'
            logging.error('Create report failed with HTTP %s: %s', status_code, err, exc_info=True)
            raise SystemExit()
        except (requests.exceptions.RequestException, ValueError) as err:
            logging.error('Create report request failed: %s', err, exc_info=True)
            raise SystemExit()


    def get_report_execution_id(self, reportId):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/data/reports/{reportId}"
        logging.info('Waiting for report execution ID: reportId=%s', reportId)
        poll_count = 0
        while True:
            try:
                response = requests.get(url, headers=headers, verify=False)
                response.raise_for_status()
                report = response.json()
                poll_count += 1
                executions = report.get('executions') or []
                execution = next(
                    (item for item in executions if item.get('executionId')),
                    None
                )
                if execution:
                    executionId = execution['executionId']
                    logging.info('Report execution ID received: reportId=%s, executionId=%s, polls=%s', reportId, executionId, poll_count)
                    return executionId
                else:
                    logging.debug('Report execution not available yet: reportId=%s, poll=%s, HTTP %s', reportId, poll_count, response.status_code)
                    time.sleep(60)
            except requests.exceptions.HTTPError as err:
                status_code = err.response.status_code if err.response is not None else 'unknown'
                logging.error('Report execution lookup failed with HTTP %s: %s', status_code, err, exc_info=True)
                raise SystemExit()
            except (requests.exceptions.RequestException, ValueError) as err:
                logging.error('Report execution lookup request failed: %s', err, exc_info=True)
                raise SystemExit()


    def get_report_excecution_id(self, reportId):
        return self.get_report_execution_id(reportId)


    def get_all_execution_details_for_report(self, reportId, report_directory, type, number:int):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/data/reports/{reportId}/executions"
        try:
            rpf_list = []
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            logging.debug(f'get_all_execution_details_for_report: response.json()={response.json()}')
            if len(response.json().get('executions')):
                for index, item in enumerate(response.json().get('executions')[0:number]):
                    logging.debug(f'get_all_execution_details_for_report: index={index}, item={item}')
                    if item.get('processStatus') == 'SUCCESS' and item.get('downloadFile'):
                        startTime = strftime('%Y-%m-%d %H:%M:%S', localtime(item.get('startTime')/1000))
                        endTime = strftime('%Y-%m-%d %H:%M:%S', localtime(item.get('endTime')/1000))
                        executionId = item.get("executionId")
                        dfile_name = report_directory + '/' + str(startTime).replace(':','_') + f'.{type.lower()}'
                        logging.info(f'get_all_execution_details_for_report: dfile_name={dfile_name}')
                        logging.debug(f'get_all_execution_details_for_report: startTime={startTime}, endTime={endTime}, executionId={executionId}')
                        self.download_report(reportId=reportId, executionId=executionId, type=type, file=dfile_name)
                        rpf_list.append(dfile_name)
            else:
                logging.debug('get_all_execution_details_for_report: no excutions')
            return rpf_list
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def check_report_execution_status(self, reportId, executionId):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/data/reports/{reportId}/executions"
        logging.info('Monitoring report execution: reportId=%s, executionId=%s', reportId, executionId)
        while True:
            try:
                r_error = []
                r_warn = []
                r_status = False
                response = requests.get(url, headers=headers, verify=False)
                response.raise_for_status()
                executions = response.json().get('executions', [])
                execution = next((item for item in executions if item.get('executionId') == executionId), None)
                if execution:
                    processStatus = execution.get('processStatus')
                    logging.info('Report execution status: reportId=%s, executionId=%s, status=%s', reportId, executionId, processStatus)
                    if processStatus == 'SUCCESS':
                        r_status = True
                        if execution.get('warnings'):
                            r_warn = execution['warnings']
                        return r_status, r_warn, r_error
                    elif processStatus == 'IN_PROGRESS' or processStatus == None:
                        time.sleep(30)
                        continue
                    elif processStatus:
                        if execution.get('warnings'):
                            r_warn = execution['warnings']
                        if execution.get('errors'):
                            r_error = execution['errors']
                        return r_status, r_warn, r_error
                else:
                    logging.warning('Execution ID not present in status response yet: reportId=%s, executionId=%s', reportId, executionId)
                    time.sleep(30)
            except requests.exceptions.HTTPError as err:
                status_code = err.response.status_code if err.response is not None else 'unknown'
                logging.error('Report execution status failed with HTTP %s: %s', status_code, err, exc_info=True)
                raise SystemExit()
            except (requests.exceptions.RequestException, ValueError) as err:
                logging.error('Report execution status request failed: %s', err, exc_info=True)
                raise SystemExit()

    
    def download_report(self, reportId, executionId, type, file):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/data/reports/{reportId}/executions/{executionId}"
        logging.info('Downloading report: reportId=%s, executionId=%s, format=%s, file=%s', reportId, executionId, type, file)
        try:
            response = requests.get(url, headers=headers, verify=False, stream=True)
            response.raise_for_status()
            if type.upper() == 'JSON':
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump(response.json(), f, indent=4)
            elif type.upper() == 'CSV':
                byte_count = 0
                with open(file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        byte_count += len(chunk)
            else:
                raise ValueError(f'Unsupported report format: {type}')
            logging.info('Report download completed: reportId=%s, file=%s, bytes=%s', reportId, file, locals().get('byte_count', 'json'))
            return True
        except requests.exceptions.HTTPError as err:
            status_code = err.response.status_code if err.response is not None else 'unknown'
            logging.error('Report download failed with HTTP %s: %s', status_code, err, exc_info=True)
            raise SystemExit()
        except (requests.exceptions.RequestException, OSError, ValueError) as err:
            logging.error('Report download failed: %s', err, exc_info=True)
            raise SystemExit()

    
    def get_reportid_by_name(self, name):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f'https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/data/reports?viewGroupId=6f68ac1e-0d26-4d57-baaa-f440c3c9e488'
        logging.info('Looking up report by name: %s', name)
        rid = None
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            rlist = response.json()
            logging.info(f'Get report list')
            logging.debug(f'rlist={rlist}')
            for rp in rlist:
                if rp['name'] == name:
                    rid = rp['reportId']
                    break
            if not rid:
                logging.warning('Report not found by name: %s', name)
            else:
                logging.info('Report found by name: reportId=%s', rid)
            return rid
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def delete_report(self, reportId):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/data/reports/{reportId}"
        logging.info('Deleting report: reportId=%s', reportId)
        try:
            response = requests.delete(url, headers=headers, verify=False)
            response.raise_for_status()
            logging.info('Report deleted: reportId=%s, HTTP %s', reportId, response.status_code)
            return
        except requests.exceptions.HTTPError as err:
            status_code = err.response.status_code if err.response is not None else 'unknown'
            logging.error('Report deletion failed with HTTP %s: %s', status_code, err, exc_info=True)
            raise SystemExit()
        except (requests.exceptions.RequestException, ValueError) as err:
            logging.error('Report deletion request failed: %s', err, exc_info=True)
            raise SystemExit()


    def get_backup_info(self):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/api/system/v1/maglev/backup"
        bkp_info = []
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            logging.debug(f'get_backup_info response={response.json()}')
            for bkp in response.json()['response']:
                bkp_item = {
                                'backup_id': bkp['backup_id'],
                                'status': bkp['status'],
                                'start_timestamp': bkp['start_timestamp'],
                                'end_timestamp': bkp['end_timestamp']
                            }
                bkp_info.append(bkp_item)
            logging.debug(f'backup_info: {bkp_info}')
            return bkp_info
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            return bkp_info
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()

    def delete_backup(self, backupId):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/api/system/v1/maglev/backup/{backupId}"
        try:
            response = requests.delete(url, headers=headers, verify=False)
            response.raise_for_status()
            logging.debug(f'delete_backup response={response.json()}')
            logging.info(f'delete backup, backupId={backupId}')
            return
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def get_ap_config(self, apEthMac):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f"https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/wireless/access-point-configuration?key={apEthMac}"
        try:
            ap_config = {}
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            logging.debug(f'{apEthMac} ap_config response={response.json()}')
            if response.json:
                logging.info(f'{apEthMac} ap_config received')
            else:
                logging.info(f'{apEthMac} ap_config None')
            return ap_config
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def change_ap_name_and_loc(self, updateApInfo):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f'https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/wireless/access-point-configuration'
        payload = updateApInfo
        logging.debug(f'updateApInfo payload: {payload}')
        try:
            response = requests.post(url, headers=headers, json=payload, verify=False)
            response.raise_for_status()
            logging.debug(f'ap provisioning response: {response.json()}')
            taskId = response.json()['response']['taskId']
            logging.info(f'taskId: {taskId}')
            return taskId
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def get_ap_config_task_info(self, tid):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f'https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/wireless/access-point-configuration/task/{tid}'
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            info = response.json()
            logging.info(f'Got Task Info for: {tid}')
            logging.debug(f'Task Info: {info}')
            return info
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def get_device_list(self, filter=''):
        offset = 1
        limit = 3
        network_device = []
        nd = ['']
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        try:
            while nd:
                url = f'https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/network-device?offset={offset}&limit={limit}'
                response = requests.get(url, headers=headers, verify=False)
                response.raise_for_status()
                nd = response.json()['response']
                logging.debug(f'response={nd}')
                network_device += nd
                offset += limit
            return network_device
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def get_interface_by_ip(self, ipAddress):
        intf_info = {}
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f'https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/interface/ip-address/{ipAddress}'
        try:
            response = requests.get(url, headers=headers, verify=False)
            logging.debug(f'response={response.text}')
            intf_info = response.json()
            if response.status_code == 404:
                portName = intf_info['response']['errorCode']
                logging.debug(f'portName={portName}')
                return portName
            elif response.status_code == 200:
                portName = intf_info['response'][0]['portName']
                logging.debug(f'portName={portName}')
                return portName
            else:
                response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def delete_device_by_id(self, did):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f'https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/network-device/{did}'
        try:
            response = requests.delete(url, headers=headers, verify=False)
            response.raise_for_status()
            logging.debug(f'response={response.json()}')
            taskId = response.json()['response']['taskId']
            logging.info(f'taskId: {taskId}')
            return taskId
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def run_command_runner(self, deviceUuids_list, commands_list):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        payload = {
            'commands': commands_list,
            'deviceUuids': deviceUuids_list
        }
        url = f'https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/network-device-poller/cli/read-request'
        logging.debug(f'payload={payload}')
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
            response.raise_for_status()
            logging.debug(f'response={response.json()}')
            taskId = response.json()['response']['taskId']
            logging.info(f'taskId: {taskId}')
            return taskId
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        

    def get_config_by_id(self, did):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'
                }
        url = f'https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/network-device/{did}/config'
        try:
            response = requests.get(url, headers=headers, verify=False)
            logging.debug(f'response.status_code={response.status_code}')
            logging.debug(f'response={response.json()}')
            match response.status_code:
                case 200:
                    return response.json()['response']
                case 400:
                    return ''
                case _:
                    return ''
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        

    def get_device_detail(self, **kwargs):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        query_params = []
        for key, value in kwargs.items():
            query_params.append(f'{key}={value}')
        url = f'https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/device-detail?{"&".join(query_params)}'
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            logging.debug(f'response={response.json()}')
            return response.json()['response']
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def get_file(self, fileId):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f'https://{self.dnac_ip}:{self.dnac_port}/api/v1/file/{fileId}'
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            logging.debug(f'response={response.json()}')
            return response.json()
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        
        
    def sync_device(self, device_id_list):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f'https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/network-device/sync'
        try:
            response = requests.put(url, headers=headers, json=device_id_list, verify=False)
            response.raise_for_status()
            logging.debug(f'response={response.json()}')
            return response.json()
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()


    def get_task_tree(self, task_id):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        url = f'https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/task/{task_id}/tree'
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            logging.debug(f'response={response.json()}')
            return response.json()
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        

    def get_device_enrich_detail(self, **kwargs):
        if time.time() - self.token_time > 3000:
            logging.debug('token is expired.')
            self.get_token()
        headers = {
                'x-auth-token': self.token,
                'content-type': 'application/json'}
        for key, value in kwargs.items():
            headers[key] = value
        url = f'https://{self.dnac_ip}:{self.dnac_port}/dna/intent/api/v1/device-enrichment-details'
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            logging.debug(f'response={response.json()}')
            return response.json()[0]['deviceDetails']
        except requests.exceptions.HTTPError as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        except Exception as err:
            logging.error(err, exc_info=True)
            raise SystemExit()
        
        
        

