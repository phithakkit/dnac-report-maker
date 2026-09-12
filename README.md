# DNAC Report Maker

DNAC Report Maker creates, monitors, downloads, and processes Cisco Catalyst Center (formerly DNA Center) reports. It also contains reusable REST helpers for discovery, templates, devices, backups, wireless access points, and command runner operations.

## Requirements

- Windows PowerShell, Linux shell, or macOS Terminal
- Python 3.10 or newer recommended
- Access to Cisco Catalyst Center
- Catalyst Center username and password
- Network access to the Catalyst Center HTTPS API

The client currently sends HTTPS requests with certificate verification disabled because Catalyst Center deployments commonly use self-signed certificates. Use this only in a trusted network and consider improving certificate validation for production use.

## Project Layout

```text
dnac_report_maker.py                         CLI entry point
dnac_restapi_lib.py                          Catalyst Center REST client
dnac_config.py                               Runtime configuration
log_setup.py                                  Logging configuration
requirements.txt                             Python dependencies
report_templates/                             Jinja report templates
    network_device_availability.j2
10.*_reports/                                Downloaded source reports
generated_reports/                            Weekly/monthly generated reports
application_run.log                           Runtime log
```

The files named `dnac_report_maker.1.py`, `dnac_report_maker.2.py`, and `dnac_report_maker.3.py` are historical variants. Use `dnac_report_maker.py` for current work.

## Installation On Windows

Open PowerShell in the repository directory:

```powershell
cd "D:\Local Repo\dnac-report-maker"
```

Create a virtual environment:

```powershell
py -3 -m venv .venv
```

If the `py` launcher is unavailable, use an installed Python executable:

```powershell
python -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Upgrade packaging tools and install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify the installation:

```powershell
python -m py_compile dnac_report_maker.py dnac_restapi_lib.py log_setup.py
python dnac_report_maker.py --help
```

When the environment is no longer needed:

```powershell
deactivate
```

## Installation On Linux Or macOS

Open a shell in the repository directory:

```bash
cd /path/to/dnac-report-maker
```

Check that Python 3 is installed:

```bash
python3 --version
```

On Debian or Ubuntu, install Python and virtual-environment support if needed:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

On Fedora, RHEL, or CentOS, install the equivalent packages with:

```bash
sudo dnf install -y python3 python3-pip
```

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Upgrade packaging tools and install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify the installation:

```bash
python -m py_compile dnac_report_maker.py dnac_restapi_lib.py log_setup.py
python dnac_report_maker.py --help
```

When the environment is no longer needed:

```bash
deactivate
```

On macOS, install Python with Homebrew if Python 3 is not available:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python
```

## Credentials And Configuration

Credentials are resolved in this order:

1. `--username` and `--password` command-line arguments
2. `DNAC_USERNAME` and `DNAC_PASSWORD` environment variables
3. Values in `dnac_config.py`
4. Interactive prompt

Prefer environment variables or the interactive password prompt so passwords do not appear in shell history:

```powershell
$env:DNAC_USERNAME = "admin"
$env:DNAC_PASSWORD = "your-password"
```

Linux and macOS:

```bash
export DNAC_USERNAME="admin"
export DNAC_PASSWORD="your-password"
```

Important settings in `dnac_config.py`:

| Setting | Purpose |
|---|---|
| `DNAC_PORT` | Catalyst Center HTTPS port, normally `443` |
| `REPORT_TYPE` | Download type used by the legacy `download` mode: `CSV` or `JSON` |
| `REPORT_DIRECTORY_SUFFIX` | Suffix for downloaded report directories |
| `HOME_PATH` | Base output directory |
| `LOG_FILE` | Runtime log file, normally `application_run.log` |
| `DEBUG_LEVEL` | Logging level, normally `DEBUG` |
| `USER_EMAIL` | Notification recipients |
| `SMTP_SERVER` / `SMTP_PORT` | SMTP notification settings |

## CLI Modes

The general form is:

```bash
python dnac_report_maker.py --option <download|make|create> ...
```

### Create A Report

Create a report from a Jinja template:

```bash
python dnac_report_maker.py \
  --ip 10.122.21.37 \
  --option create \
  --template report_templates/network_device_availability.j2 \
  --template-var "report_name=Network Devices Report v2" \
  --template-var "start_date_time=1789074244157" \
  --template-var "end_date_time=1789164988958"
```

The command renders the template, removes known response-only fields, validates the required request fields, sends the POST request, and prints the created report ID.

### Dynamic Template Variables

Use `--template-var` more than once. Values are parsed as JSON when possible, so numbers, booleans, arrays, and `null` retain their types:

```powershell
--template-var "report_name=Network Devices Report v2"
--template-var "start_date_time=1789074244157"
--template-var "enabled=true"
--template-var "days=[\"MONDAY\",\"FRIDAY\"]"
```

The same variables work in Bash and Zsh:

```bash
--template-var "report_name=Network Devices Report v2"
--template-var "start_date_time=1789074244157"
--template-var "enabled=true"
--template-var 'days=["MONDAY","FRIDAY"]'
```

String values are passed as strings. A value containing `=` is supported because only the first `=` separates the name and value.

The current template uses values such as:

```jinja2
"name": "{{ report_name | default('Default report name') }}"
"startDateTime": {{ start_date_time }}
"endDateTime": {{ end_date_time }}
```

Numeric Jinja values must not be quoted in the template.

### Monitor, Download, And Delete

Use monitoring only with a template whose schedule type is `SCHEDULE_NOW`:

```powershell
$now = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$start = $now - (30 * 24 * 60 * 60 * 1000)

python dnac_report_maker.py `
  --ip 10.122.21.37 `
  --option create `
  --template report_templates/network_device_availability.j2 `
  --template-var "report_name=Network Devices Report v2" `
  --template-var "start_date_time=$start" `
  --template-var "end_date_time=$now" `
  --monitor-runnow-and-download
```

Linux and macOS equivalent:

```bash
now=$(python3 -c 'import time; print(int(time.time() * 1000))')
start=$((now - 30 * 24 * 60 * 60 * 1000))

python3 dnac_report_maker.py \
  --ip 10.122.21.37 \
  --option create \
  --template report_templates/network_device_availability.j2 \
  --template-var "report_name=Network Devices Report v2" \
  --template-var "start_date_time=$start" \
  --template-var "end_date_time=$now" \
  --monitor-runnow-and-download
```

The workflow is:

1. Create the report.
2. Print the report ID.
3. Wait for the execution ID.
4. Monitor the execution until success or failure.
5. Read `view.format.formatType` from the template.
6. Download the result as CSV or JSON.

To delete the newly created report after a successful download, add:

```powershell
--delete-report-job-after-download
```

This flag requires both `--option create` and `--monitor-runnow-and-download`:

```powershell
python dnac_report_maker.py `
  --ip 10.122.21.37 `
  --option create `
  --template report_templates/network_device_availability.j2 `
  --template-var "report_name=Temporary Availability Report" `
  --template-var "start_date_time=$start" `
  --template-var "end_date_time=$now" `
  --monitor-runnow-and-download `
  --delete-report-job-after-download
```

Linux and macOS equivalent:

```bash
python3 dnac_report_maker.py \
  --ip 10.122.21.37 \
  --option create \
  --template report_templates/network_device_availability.j2 \
  --template-var "report_name=Temporary Availability Report" \
  --template-var "start_date_time=$start" \
  --template-var "end_date_time=$now" \
  --monitor-runnow-and-download \
  --delete-report-job-after-download
```

The CLI displays a rotating ASCII spinner while waiting, monitoring, downloading, and deleting.

### Download Existing Report Executions

Download executions for an existing report by name:

```bash
python3 dnac_report_maker.py \
  --ip 10.122.21.37 \
  --option download \
  --report_name "Network Devices Report - Network Device Availability v1" \
  --number 7
```

`--number` controls how many recent successful executions are considered. The mode uses `REPORT_TYPE` from `dnac_config.py`.

### Generate Weekly Or Monthly Reports

After source reports have been downloaded, create a weekly report:

```bash
python3 dnac_report_maker.py \
  --ip 10.122.21.37 \
  --option make \
  --report_name "Network Device Availability Daily" \
  --type last_week
```

Create a monthly report:

```bash
python3 dnac_report_maker.py \
  --ip 10.122.21.37 \
  --option make \
  --report_name "Network Device Availability Daily" \
  --type last_month
```

Generated files are written under `generated_reports/`.

## Template Rules

A valid report request must contain these top-level fields:

```text
deliveries
name
schedule
view
viewGroupId
viewGroupVersion
dataCategory
```

The `view` object must contain:

```text
fieldGroups
filters
format
name
viewId
```

Templates may be copied from Catalyst Center response payloads. The loader removes these response-only fields before POSTing:

```text
viewGroupName
executions
children
executionCount
clientId
reportId
reportWasExecuted
```

It also removes response metadata from `view.format` and filters, including `template`, `default`, `scope`, `filterSpecId`, and `timeOptions`.

For monitored run-now reports, use:

```json
"schedule": {
    "type": "SCHEDULE_NOW"
}
```

The downloaded file format comes from:

```json
"view": {
    "format": {
        "formatType": "CSV"
    }
}
```

Supported formats are `CSV` and `JSON`.

## Logging And Troubleshooting

The application writes logs to `application_run.log` by default. The default level is `DEBUG`.

Logs include:

- CLI mode and selected workflow
- Template path, report name, schedule type, and format
- API request lifecycle and HTTP status
- Report ID and execution ID
- Polling status and missing execution responses
- Download path and byte count for CSV files
- Report deletion status
- Exceptions and stack traces

Authentication tokens and passwords are not logged.

For a quick syntax check:

```powershell
python -m py_compile dnac_report_maker.py dnac_restapi_lib.py log_setup.py
```

If a template fails:

1. Confirm the file path.
2. Validate that rendered Jinja output is JSON.
3. Check required top-level and `view` fields.
4. Check that numeric values are not quoted incorrectly.
5. Check `application_run.log` for the API response status and exception details.

## Python Function Reference

### `dnac_report_maker.py`

- `resolve_dnac_credentials(username=None, password=None)`: Resolves credentials from CLI arguments, environment variables, configuration, or prompts.
- `mail_notification(text_body, attachment_path, subject)`: Sends an email with a generated report attached.
- `get_last_seven_days()`: Returns the previous seven dates as `YYYY-MM-DD` strings.
- `run_with_spinner(message, operation, *args, **kwargs)`: Runs a blocking operation while displaying a terminal spinner.
- `parse_template_vars(template_vars)`: Converts repeated `NAME=VALUE` CLI arguments into a dictionary with JSON type parsing.
- `load_report_template(template_path, template_vars=None)`: Renders a Jinja template, parses JSON, removes response-only fields, and validates the report request structure.
- `main()`: Parses CLI arguments and dispatches create, download, or weekly/monthly make workflows.

### `log_setup.py`

- `log_setup(log_level, log_file, log_term=False)`: Configures rotating-file and optional terminal logging. Repeated calls replace handlers instead of duplicating them.

### `dnac_restapi_lib.py`: Authentication And General Tasks

- `rest_api_lib.__init__(dnac_ip, dnac_port, username, password)`: Creates a REST client and obtains an authentication token.
- `get_token()`: Requests a new Catalyst Center authentication token.
- `logout()`: Logs out from Catalyst Center.
- `get_task_info(tid)`: Gets task information by task ID.
- `get_task_tree(task_id)`: Gets the task tree for a task.
- `get_file(fileId)`: Gets a file by file ID.

### Discovery And Sites

- `get_discovery_info(did)`: Gets discovery job details.
- `get_discovery_result(did)`: Gets discovered network devices for a discovery job.
- `delete_alldiscovery()`: Deletes all discovery jobs.
- `add_discovery_node(node_info)`: Creates a single-node discovery task.
- `get_siteid_by_name(site_name)`: Resolves a site name to a site ID.
- `get_count_discovery()`: Gets the discovery job count.
- `get_all_discovery_jobs(num)`: Gets a requested number of discovery jobs.
- `update_existing_discovery_job(discoveryInfo, password)`: Updates credentials and reactivates an existing discovery job.
- `assign_device_to_site(site_id, device_ip)`: Assigns a device to a site and waits for the operation status.

### Templates And Reports

- `get_template_id(tname)`: Finds a Catalyst Center template ID by name.
- `deploy_template_v2(tname, targetInfo)`: Deploys a template to target devices.
- `get_tdeployment_info(did)`: Gets template deployment status.
- `make_report_schedule(payload)`: Creates or schedules a report and returns its report ID. This is the older report creation helper.
- `create_report(payload)`: Creates a report and returns the complete response dictionary.
- `get_report_execution_id(reportId)`: Waits for and returns an execution ID.
- `get_report_excecution_id(reportId)`: Backward-compatible alias for the misspelled older method name.
- `get_all_execution_details_for_report(reportId, report_directory, type, number)`: Downloads recent successful executions for an existing report.
- `check_report_execution_status(reportId, executionId)`: Polls an execution until success or a terminal failure and returns status, warnings, and errors.
- `download_report(reportId, executionId, type, file)`: Downloads a CSV or JSON report result to a file.
- `get_reportid_by_name(name)`: Finds a report ID by report name.
- `delete_report(reportId)`: Deletes a report by ID.

### Backups

- `get_backup_info()`: Returns backup ID, status, and timestamps for Catalyst Center backups.
- `delete_backup(backupId)`: Deletes a backup by ID.

### Wireless Access Points

- `get_ap_config(apEthMac)`: Gets access-point configuration information.
- `change_ap_name_and_loc(updateApInfo)`: Updates an access-point name and location and returns a task ID.
- `get_ap_config_task_info(tid)`: Gets access-point configuration task information.

### Devices And Interfaces

- `get_device_list(filter='')`: Retrieves network devices using paginated requests.
- `get_interface_by_ip(ipAddress)`: Gets the interface port name for an IP address.
- `delete_device_by_id(did)`: Deletes a network device and returns the task ID.
- `get_device_detail(**kwargs)`: Gets device details using query parameters.
- `get_device_enrich_detail(**kwargs)`: Gets device enrichment details using request headers.
- `get_config_by_id(did)`: Gets a device configuration by device ID.
- `sync_device(device_id_list)`: Synchronizes devices by ID.

### Command Runner

- `run_command_runner(deviceUuids_list, commands_list)`: Starts a CLI read request for commands on device UUIDs and returns a task ID.

Avoid hard-coding the password in source code. Use environment variables or a secret manager in real automation.

## Output And Exit Behavior

- Downloaded source files are stored in a directory based on IP and report name.
- Weekly and monthly generated reports are stored under `generated_reports/`.
- The CLI prints report IDs, execution IDs, download paths, and failure details.
- API failures are logged with stack traces and generally terminate the current operation with `SystemExit`.

## Direct Python Usage

The REST client can be used directly from another Python script:

```python
from dnac_restapi_lib import rest_api_lib

client = rest_api_lib(
    dnac_ip='10.122.21.37',
    dnac_port='443',
    username='admin',
    password='secret'
)

try:
    report = client.create_report(payload)
    print(report['reportId'])
finally:
    client.logout()
```

## Support & Contributing

For issues, suggestions, or contributions, please open a GitHub issue or pull request.

---

## License

Copyright (c) 2021 Cisco and/or its affiliates. This software is licensed to you under the terms of the Cisco Sample Code License, Version 1.1 (the "License"). You may obtain a copy of the License at [https://developer.cisco.com/docs/licenses](https://developer.cisco.com/docs/licenses). All use of the material herein must be in accordance with the terms of the License. All rights not expressly granted under the License are reserved. Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
