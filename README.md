1. git clone https://github.com/aharrison7/google-cloud-access-approval-cli.git
   cd google-cloud-access-approval-cli
   ```

2. Install required Python packages:
   ```bash
   pip install google-auth google-api-python-client google-auth-oauthlib halo
   ```

3. Enable the Access Approval API:
   - Visit [Google Cloud Console - Access Approval API](https://console.cloud.google.com/apis/library/accessapproval.googleapis.com)
   - Select your project and click 'Enable'
4. Create a service account for your project and generate JSON credentials. Give this Access Approval permissions to get and approve Access Approvals

## Authentication

You can authenticate using either your Google Cloud user account (recommended) or a service account:

### Option 1: User Account Authentication (OAuth 2.0)

1. Set up OAuth 2.0 credentials:
   - Go to [Google Cloud Console > APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop application" as the application type
   - Download the client configuration file
   - Rename it to `client_secret.json` and place it in the same directory as the script

2. Run any command, and you'll be prompted to authenticate in your browser

### Option 2: Service Account Authentication

1. Create a service account key:
   - Go to [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
   - Create or select a service account
   - Create a new key (JSON format)

2. Set the environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   ```

## Usage

### Basic Commands

```bash
# List pending approval requests (default)
python list_approval_requests.py

# List all requests regardless of state
python list_approval_requests.py --state ALL

# List approved requests
python list_approval_requests.py --state APPROVED

# List dismissed requests
python list_approval_requests.py --state DISMISSED

# Export requests to JSON
python list_approval_requests.py --state ALL --export json --output requests.json

# Export requests to CSV
python list_approval_requests.py --state ALL --export csv --output requests.csv

# Launch interactive viewer
python list_approval_requests.py --interactive

# Enable debug output
python list_approval_requests.py --debug
```

### Request Management

```bash
# Approve a request
python list_approval_requests.py --approve projects/[PROJECT_ID]/approvalRequests/[REQUEST_ID]

# Dismiss a request
python list_approval_requests.py --dismiss projects/[PROJECT_ID]/approvalRequests/[REQUEST_ID]

# Revoke an approved request
python list_approval_requests.py --revoke projects/[PROJECT_ID]/approvalRequests/[REQUEST_ID]
```

### Interactive Viewer Controls

When using the interactive viewer (`--interactive`):
- ↑/↓: Navigate through requests
- a: Approve selected request
- d: Dismiss selected request
- r: Revoke selected request
- q: Quit viewer

## Output Format

The tool displays approval requests in a formatted output:

```
Approval Requests (State: PENDING):
================================================================================
Request Name: projects/123456789/approvalRequests/abcd1234
State: PENDING
Request Time: 2025-02-18 10:30:00 UTC

Resource Details:
  Requested Resource: //compute.googleapis.com/projects/test

Request Context:
  Type: CUSTOMER_INITIATED_SUPPORT
  Detail: Case Number: 12345

Time Details:
  Created: 2025-02-18 10:30:00 UTC
  Expires: 2025-02-19 10:30:00 UTC
================================================================================
```

## Development

### Prerequisites

- Python 3.11 or higher
- Google Cloud project with Access Approval API enabled
- Appropriate IAM permissions for managing access approval requests

### Setting Up Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/aharrison7/google-cloud-access-approval-cli.git
   cd google-cloud-access-approval-cli
   ```

2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Run tests:
   ```bash
   pytest tests/
