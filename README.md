export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
   ```

2. Install required Python packages:
   ```bash
   pip install google-auth google-api-python-client
   ```

## Usage

Run the script:
```bash
python list_approval_requests.py
```

### Expected Output

The script will display pending approval requests in a formatted output:
```
Pending Approval Requests:
--------------------------------------------------------------------------------
Request Name: projects/123456789/approvalRequests/abcd1234
Request Time: 2025-02-18 10:30:00 UTC
Requested Resource: //compute.googleapis.com/projects/...
Requested Reason: CUSTOMER_INITIATED_SUPPORT
Expiration Time: 2025-02-19 10:30:00 UTC
--------------------------------------------------------------------------------