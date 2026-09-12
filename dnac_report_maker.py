from dnac_config import DEBUG_LEVEL, LOG_FILE
from dnac_config import DNAC_PORT, DNAC_USERNAME, DNAC_PASSWORD, REPORT_TYPE, REPORT_DIRECTORY_SUFFIX, HOME_PATH
from dnac_config import USER_EMAIL, SENDER_EMAIL, SMTP_SERVER, SMTP_PORT
from dnac_restapi_lib import rest_api_lib
from log_setup import log_setup
import argparse
import getpass
import logging
import re
import os
import json
import sys
import threading
import time
from datetime import datetime, timedelta
import pandas as pd
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError


def resolve_dnac_credentials(username=None, password=None):
    """Resolve DNAC credentials in this priority order:
    1. command line arguments
    2. environment variables
    3. config defaults
    4. terminal prompt
    """
    username = username or os.getenv('DNAC_USERNAME') or DNAC_USERNAME
    password = password or os.getenv('DNAC_PASSWORD') or DNAC_PASSWORD

    if not username:
        username = input('Enter DNAC username: ').strip()
    if not password:
        password = getpass.getpass('Enter DNAC password: ')

    return username, password


def mail_notification(text_body, attachment_path, subject):
    logging.info('Sending notification email: subject=%s, attachment=%s, recipients=%s', subject, attachment_path, len(USER_EMAIL))
    sender_email = SENDER_EMAIL
    receiver_emails = USER_EMAIL
    for receiver_email in receiver_emails:
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = receiver_email
        message['Subject'] = subject
        message.attach(MIMEText(text_body, 'plain'))
        filename = re.sub(r'.*\/', '', attachment_path)
        logging.debug(f'attachment_path={attachment_path}')
        logging.debug(f'filename={filename}')
        with open(attachment_path, 'rb') as att:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(att.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={filename}'
            )
            message.attach(part)
        try:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.ehlo()
            server.send_message(message)
            server.quit()
            logging.info('send email to: %s'%receiver_email)
            return True
        except Exception as e:
            logging.error('Notification email failed for recipient %s: %s', receiver_email, e, exc_info=True)
            return False

def get_last_seven_days():
    today = datetime.now()
    last_seven_days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 8)]
    return last_seven_days


def run_with_spinner(message, operation, *args, **kwargs):
    logging.debug('Starting long-running operation: %s', message)
    stop_spinner = threading.Event()

    def spin():
        spinner = '|/-\\'
        index = 0
        while not stop_spinner.is_set():
            sys.stdout.write(f'\r{spinner[index % len(spinner)]} {message}')
            sys.stdout.flush()
            index += 1
            stop_spinner.wait(0.5)

    spinner_thread = threading.Thread(target=spin, daemon=True)
    spinner_thread.start()
    try:
        return operation(*args, **kwargs)
    finally:
        stop_spinner.set()
        spinner_thread.join()
        sys.stdout.write('\r' + (' ' * (len(message) + 2)) + '\r')
        sys.stdout.flush()
        logging.debug('Finished long-running operation: %s', message)


def parse_template_vars(template_vars):
    values = {}
    for item in template_vars:
        if '=' not in item:
            raise ValueError(
                f'Invalid template variable {item!r}; expected NAME=VALUE'
            )
        name, value = item.split('=', 1)
        name = name.strip()
        if not name:
            raise ValueError('Template variable name cannot be empty')
        try:
            values[name] = json.loads(value)
        except json.JSONDecodeError:
            values[name] = value
    return values


def load_report_template(template_path, template_vars=None):
    logging.info('Loading report template: %s', template_path)
    template_path = os.path.abspath(template_path)
    template_directory = os.path.dirname(template_path)
    template_name = os.path.basename(template_path)
    environment = Environment(
        loader=FileSystemLoader(template_directory),
        undefined=StrictUndefined
    )
    template = environment.get_template(template_name)
    rendered_template = template.render(**(template_vars or {}))
    payload = json.loads(rendered_template)
    logging.debug('Rendered report template: name=%s, schedule=%s, variables=%s',
                  payload.get('name'), payload.get('schedule', {}).get('type'),
                  sorted((template_vars or {}).keys()))

    response_only_fields = {
        'viewGroupName',
        'executions',
        'children',
        'executionCount',
        'clientId',
        'reportId',
        'reportWasExecuted'
    }
    for field in response_only_fields:
        payload.pop(field, None)

    if isinstance(payload.get('view'), dict):
        payload['view'].pop('description', None)
        if isinstance(payload['view'].get('format'), dict):
            payload['view']['format'].pop('template', None)
            payload['view']['format'].pop('default', None)
        for report_filter in payload['view'].get('filters', []):
            if isinstance(report_filter, dict):
                report_filter.pop('scope', None)
                report_filter.pop('filterSpecId', None)
                report_filter.pop('timeOptions', None)

    required_fields = {
        'deliveries',
        'name',
        'schedule',
        'view',
        'viewGroupId',
        'viewGroupVersion',
        'dataCategory'
    }
    missing_fields = sorted(required_fields - payload.keys())
    if missing_fields:
        raise ValueError(f'Missing required report template fields: {", ".join(missing_fields)}')

    required_view_fields = {'fieldGroups', 'filters', 'format', 'name', 'viewId'}
    missing_view_fields = sorted(required_view_fields - payload['view'].keys())
    if missing_view_fields:
        raise ValueError(f'Missing required report view fields: {", ".join(missing_view_fields)}')

    logging.info('Report template validated: name=%s, format=%s',
                 payload.get('name'), payload.get('view', {}).get('format', {}).get('formatType'))
    return payload


def main():
    log_setup(DEBUG_LEVEL, LOG_FILE)
    parser = argparse.ArgumentParser(description='DNAC Report Maker')
    parser.add_argument('--ip', help="ip: catalyst center's iP address")
    parser.add_argument('--report_name', help="name: report name")
    parser.add_argument('--option', choices=['download', 'make', 'create'], help='option: download, make, create')
    parser.add_argument('--type', help='type: last_week, last_month')
    parser.add_argument('--number', help='number: number of files will be downloaded [1-7]')
    parser.add_argument('--template', help='path to the JSON or Jinja report template used by create mode')
    parser.add_argument(
        '--monitor-runnow-and-download',
        action='store_true',
        help='with create mode, monitor a SCHEDULE_NOW report and download its result'
    )
    parser.add_argument(
        '--delete-report-job-after-download',
        action='store_true',
        help='with create and monitor mode, delete the created report after download succeeds'
    )
    parser.add_argument(
        '--template-var',
        action='append',
        default=[],
        metavar='NAME=VALUE',
        help='template variable; may be specified multiple times'
    )
    parser.add_argument('--username', help='DNAC username. If omitted, environment variable DNAC_USERNAME is used.')
    parser.add_argument('--password', help='DNAC password. If omitted, environment variable DNAC_PASSWORD is used.')
    args = parser.parse_args()
    logging.info('Starting DNAC Report Maker: option=%s, ip=%s, report_name=%s', args.option, args.ip, args.report_name)
    logging.debug('CLI flags: monitor=%s, delete_after_download=%s, template=%s',
                  args.monitor_runnow_and_download, args.delete_report_job_after_download, args.template)

    if args.monitor_runnow_and_download and args.option != 'create':
        parser.error('--monitor-runnow-and-download can only be used with --option create')
    if args.delete_report_job_after_download and (
        args.option != 'create' or not args.monitor_runnow_and_download
    ):
        parser.error(
            '--delete-report-job-after-download requires --option create '
            'and --monitor-runnow-and-download'
        )

    dnac_username, dnac_password = resolve_dnac_credentials(args.username, args.password)
    dnac_ip = args.ip
    report_name = args.report_name
    report_type = REPORT_TYPE.upper()

    if args.option != 'create' and not dnac_ip:
        parser.error('--ip is required for download and make modes')

    if args.option == 'create':
        logging.info('Entering create workflow')
        if not dnac_ip:
            parser.error('--ip is required when --option is create')
        if not args.template:
            parser.error('--template is required when --option is create')
        try:
            template_vars = parse_template_vars(args.template_var)
            report_payload = load_report_template(args.template, template_vars)
        except (OSError, json.JSONDecodeError, ValueError, TemplateError) as err:
            parser.error(f'Unable to load report template: {err}')
        if report_name:
            report_payload['name'] = report_name
        if args.monitor_runnow_and_download and report_payload.get('schedule', {}).get('type') != 'SCHEDULE_NOW':
            parser.error('--monitor-runnow-and-download requires a template with schedule.type=SCHEDULE_NOW')
        dnac = rest_api_lib(dnac_ip=dnac_ip, dnac_port=DNAC_PORT, username=dnac_username, password=dnac_password)
        report = dnac.create_report(report_payload)
        report_id = report.get('reportId')
        if not report_id:
            parser.error('Create report response did not contain reportId')
        logging.info(f'Created report: {report_id}')
        print(f'Report ID: {report_id}')
        if args.monitor_runnow_and_download:
            logging.info('Monitoring enabled for reportId=%s', report_id)
            execution_id = run_with_spinner(
                'Waiting for report execution ID',
                dnac.get_report_execution_id,
                report_id
            )
            print(f'Execution ID: {execution_id}')
            status, warnings, errors = run_with_spinner(
                'Monitoring report execution',
                dnac.check_report_execution_status,
                report_id,
                execution_id
            )
            if not status:
                logging.error('Report execution failed: reportId=%s, executionId=%s, errors=%s', report_id, execution_id, errors)
                print(f'Report execution failed: {errors or "No error details returned"}')
                if warnings:
                    print(f'Warnings: {warnings}')
                return
            report_format = report_payload['view']['format']['formatType']
            report_directory = f'{HOME_PATH}{dnac_ip}_{report_payload["name"].replace(" ", "_")}_{REPORT_DIRECTORY_SUFFIX}'
            os.makedirs(report_directory, exist_ok=True)
            report_file = os.path.join(
                report_directory,
                f'{report_payload["name"].replace(" ", "_")}_{execution_id}.{report_format.lower()}'
            )
            download_succeeded = run_with_spinner(
                'Downloading report',
                dnac.download_report,
                reportId=report_id,
                executionId=execution_id,
                type=report_format,
                file=report_file
            )
            if download_succeeded:
                logging.info('Download succeeded: reportId=%s, file=%s', report_id, report_file)
                print(f'Report downloaded: {report_file}')
                if args.delete_report_job_after_download:
                    run_with_spinner(
                        'Deleting created report',
                        dnac.delete_report,
                        report_id
                    )
                    print(f'Report deleted: {report_id}')
                logging.info('Create workflow completed: reportId=%s', report_id)
        return

    if args.option == 'download':
        logging.info('Entering download workflow')
        if not report_name:
            parser.error('--report_name is required for download mode')
        report_directory = f'{HOME_PATH}{dnac_ip}_{report_name.replace(" ","_")}_{REPORT_DIRECTORY_SUFFIX}'
        dnac = rest_api_lib(dnac_ip=dnac_ip, dnac_port=DNAC_PORT, username=dnac_username, password=dnac_password)
        report_id = dnac.get_reportid_by_name(name=report_name)
        if not os.path.isdir(report_directory):
            os.makedirs(report_directory)
            logging.info(f"no report directory: directory '{report_directory}' created successfully.")
        report_file_list = dnac.get_all_execution_details_for_report(
            report_id,
            report_directory,
            type=report_type,
            number=int(args.number)
            )
        report_file_list.sort()
        logging.info(f'report_file_list={report_file_list}')
    
    if args.option == 'make':
        logging.info('Entering make workflow: type=%s', args.type)
        if not report_name:
            parser.error('--report_name is required for make mode')
        report_directory = f'{HOME_PATH}{dnac_ip}_{report_name.replace(" ","_")}_{REPORT_DIRECTORY_SUFFIX}'
        if args.type == 'last_week':
            if not os.path.isdir(f'{HOME_PATH}generated_reports'):
                os.makedirs(f'{HOME_PATH}generated_reports')
                logging.info(f"no generated report directory: directory '{f'{HOME_PATH}generated_reports'}' created successfully.")
            cdf = pd.DataFrame()
            last_week_report_file_list = []
            file_list = os.listdir(report_directory)
            file_list.sort()
            last_week_key = get_last_seven_days()
            logging.debug(f'last_seven_days={last_week_key}')
            weekly_report_filename = f'{HOME_PATH}generated_reports/{dnac_ip}_{report_name.replace(" ","_")}_weekly_report.csv'
            weekly_report_file_list_filename = f'{HOME_PATH}generated_reports/{dnac_ip}_{report_name.replace(" ","_")}_weekly_report_file_list.json'
            for fl_name in file_list:
                logging.debug(f'fl_name={fl_name}')
                rcol_regex = re.compile(r'(.*)(\s.*)')
                match = rcol_regex.match(fl_name)
                if match:
                    rcol_name = match.group(1)
                    logging.debug(f'rcol_name={rcol_name}')
                else:
                    rcol_name = None
                    logging.debug(f'file name not matched, fl_name={fl_name}')
                if rcol_name and rcol_name in last_week_key:
                    logging.info(f'matched last_week_key, fl_name={fl_name}')
                    fl_name = report_directory + '/' + fl_name
                    last_week_report_file_list.append(fl_name)
                    with open(fl_name, 'r') as f:
                        lines = f.readlines()
                        skiprows = 0
                        for line in lines:
                            if 'Availability (%)' in line:
                                break
                            skiprows += 1
                        logging.debug(f'skiprows={skiprows}')
                    with open(fl_name, 'r') as f:
                        df: pd.DataFrame
                        if report_type == 'CSV':
                            df = pd.read_csv(f, skiprows=skiprows)
                        elif report_type == 'JSON':
                            df = pd.read_json(f)
                        else:
                            raise ValueError(
                                f'Unsupported report type: {report_type}'
                            )
                    df['Availability (%)'] = df['Availability (%)'].str.rstrip('%').astype('float')
                    if cdf.empty:
                        cdf = df.copy()
                        cdf.rename(columns={'Availability (%)': rcol_name}, inplace=True)
                    else:
                        device_list = cdf['Device Name'].tolist()
                        cdf[rcol_name] = ''
                        for device_name in df['Device Name']:
                            n_value = df.loc[df["Device Name"] == device_name].iloc[0]["Availability (%)"]
                            if device_name not in device_list:
                                new_index = max(cdf.index) + 1
                                cdf.loc[new_index] = ''
                                cdf.loc[cdf.index[-1], rcol_name] = n_value
                                cdf.loc[cdf.index[-1], 'Device Family'] = df.loc[df["Device Name"] == device_name].iloc[0]["Device Family"]
                                cdf.loc[cdf.index[-1], 'Device Role'] = df.loc[df["Device Name"] == device_name].iloc[0]["Device Role"]
                                cdf.loc[cdf.index[-1], 'Device IP Address'] = df.loc[df["Device Name"] == device_name].iloc[0]["Device IP Address"]
                                cdf.loc[cdf.index[-1], 'Location'] = df.loc[df["Device Name"] == device_name].iloc[0]["Location"]
                                cdf.loc[cdf.index[-1], 'Software Version'] = df.loc[df["Device Name"] == device_name].iloc[0]["Software Version"]
                                cdf.loc[cdf.index[-1], 'Device Name'] = device_name
                            else:
                                cdf.loc[cdf["Device Name"] == device_name, rcol_name] = n_value
            total_columns = len(cdf.columns)
            cdf = cdf.mask(cdf=='')
            logging.debug(f'cdf:\n{cdf}')
            logging.debug(f'total_columns={total_columns}')
            cdf['Availability (%)'] = cdf.iloc[:, 6:].mean(axis=1, skipna=True)
            logging.debug(f'calculated cdf:\n{cdf}')
            if last_week_report_file_list:
                logging.info('Generating last_week report file.')
                with open(weekly_report_filename, 'w', newline='') as f:
                    cdf.to_csv(f)
                with open(weekly_report_file_list_filename, 'w') as f:
                    print(json.dumps(last_week_report_file_list, indent=4), file=f)
                mail_notification(
                    text_body=f'Please find the Device Availability weekly Report in the attached file.',
                    attachment_path=weekly_report_filename,
                    subject=f'CatC | {report_name} | Device Availability weekly Report '
                    )
            else:
                logging.info('There is no report files last week.')
        if args.type == 'last_month':
            if not os.path.isdir(f'{HOME_PATH}generated_reports'):
                os.makedirs(f'{HOME_PATH}generated_reports')
                logging.info(f"no generated report directory: directory '{f'{HOME_PATH}generated_reports'}' created successfully.")
            cdf = pd.DataFrame()
            file_list = os.listdir(report_directory)
            file_list.sort()
            current_time = time.localtime()
            current_month = '{:02}'.format(time.strftime("%m", current_time))
            current_year = time.strftime("%Y", current_time)
            last_month = '{:02}'.format((int(current_month) - 1))
            logging.debug(f'current_time={current_time}')
            logging.debug(f'current_month={current_month}')
            logging.debug(f'current_year={current_year}')
            logging.debug(f'last_month={last_month}')
            if last_month == '00':
                last_month = '12'
                current_year = str(int(current_year) - 1)
                last_month_key = current_year + '-' + last_month
            else:
                last_month_key = current_year + '-' + last_month
            logging.info(f'last_month_key={last_month_key}')
            monthly_report_filename = f'{HOME_PATH}generated_reports/{last_month_key}_{dnac_ip}_{report_name.replace(" ","_")}_monthly_report.csv'
            monthly_report_file_list_filename = f'{HOME_PATH}generated_reports/{last_month_key}_{dnac_ip}_{report_name.replace(" ","_")}_monthly_report_file_list.json'
            last_month_report_file_list = []
            for fl_name in file_list:
                if last_month_key in fl_name:
                    logging.debug(f'fl_name={fl_name}')
                    rcol_regex = re.compile(r'(.*)(\s.*)')
                    match = rcol_regex.match(fl_name)
                    if match:
                        rcol_name = match.group(1)
                        logging.debug(f'rcol_name={rcol_name}')
                    else:
                        logging.debug(f'file name error: fl_name={fl_name}')
                        continue
                    fl_name = report_directory + '/' + fl_name
                    last_month_report_file_list.append(fl_name)
                    with open(fl_name, 'r') as f:
                        lines = f.readlines()
                        skiprows = 0
                        for line in lines:
                            if 'Availability (%)' in line:
                                break
                            skiprows += 1
                        logging.debug(f'skiprows={skiprows}')
                    with open(fl_name, 'r') as f:
                        df: pd.DataFrame
                        if report_type == 'CSV':
                            df = pd.read_csv(f, skiprows=skiprows)
                        elif report_type == 'JSON':
                            df = pd.read_json(f)
                        else:
                            raise ValueError(
                                f'Unsupported report type: {report_type}'
                            )
                    df['Availability (%)'] = df['Availability (%)'].str.rstrip('%').astype('float')
                    if cdf.empty:
                        cdf = df.copy()
                        cdf.rename(columns={'Availability (%)': rcol_name}, inplace=True)
                    else:
                        device_list = cdf['Device Name'].tolist()
                        cdf[rcol_name] = ''
                        for device_name in df['Device Name']:
                            n_value = df.loc[df["Device Name"] == device_name].iloc[0]["Availability (%)"]
                            if device_name not in device_list:
                                new_index = max(cdf.index) + 1
                                cdf.loc[new_index] = ''
                                cdf.loc[cdf.index[-1], rcol_name] = n_value
                                cdf.loc[cdf.index[-1], 'Device Family'] = df.loc[df["Device Name"] == device_name].iloc[0]["Device Family"]
                                cdf.loc[cdf.index[-1], 'Device Role'] = df.loc[df["Device Name"] == device_name].iloc[0]["Device Role"]
                                cdf.loc[cdf.index[-1], 'Device IP Address'] = df.loc[df["Device Name"] == device_name].iloc[0]["Device IP Address"]
                                cdf.loc[cdf.index[-1], 'Location'] = df.loc[df["Device Name"] == device_name].iloc[0]["Location"]
                                cdf.loc[cdf.index[-1], 'Software Version'] = df.loc[df["Device Name"] == device_name].iloc[0]["Software Version"]
                                cdf.loc[cdf.index[-1], 'Device Name'] = device_name
                            else:
                                cdf.loc[cdf["Device Name"] == device_name, rcol_name] = n_value
            total_columns = len(cdf.columns)
            cdf = cdf.mask(cdf=='')
            logging.debug(f'cdf:\n{cdf}')
            logging.debug(f'total_columns={total_columns}')
            cdf['Availability (%)'] = cdf.iloc[:, 6:].mean(axis=1, skipna=True)
            logging.debug(f'calculated cdf:\n{cdf}')
            if last_month_report_file_list:
                logging.info('Generating last_month report file.')
                with open(monthly_report_filename, 'w', newline='') as f:
                    cdf.to_csv(f)
                with open(monthly_report_file_list_filename, 'w') as f:
                    print(json.dumps(last_month_report_file_list, indent=4), file=f)
                mail_notification(
                    text_body=f'Please find the Device Availability montly Report in the attached file.',
                    attachment_path=monthly_report_filename,
                    subject=f'CatC | {report_name} | Device Availability montly Report '
                    )
            else:
                logging.info('There is no report files last month.')


if __name__ == '__main__':
    main()


