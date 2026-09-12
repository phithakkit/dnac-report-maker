import os

DEBUG_LEVEL = 'DEBUG'
LOG_FILE = 'application_run.log'
DNAC_PORT = '443'
DNAC_USERNAME = os.getenv('DNAC_USERNAME', '')
DNAC_PASSWORD = os.getenv('DNAC_PASSWORD', '')
REPORT_TYPE = 'CSV'
REPORT_DIRECTORY_SUFFIX = 'reports'
USER_EMAIL = ['']
SENDER_EMAIL = 'dnac@dnac.lab'
SMTP_SERVER = ''
SMTP_PORT = 25
HOME_PATH = './'
