2. Install required Python packages:
   ```bash
   pip install google-auth google-api-python-client
   ```

3. Enable the Access Approval API:
   - Visit [Google Cloud Console - Access Approval API](https://console.cloud.google.com/apis/library/accessapproval.googleapis.com)
   - Select your project and click 'Enable'

## Usage

Run the script with optional state filter:
```bash
python list_approval_requests.py [--state STATE]
```

Available states:
- `PENDING` (default): Show pending approval requests (includes new requests without explicit state)
- `APPROVED`: Show only approved requests
- `DISMISSED`: Show only dismissed requests
- `ALL`: Show all requests regardless of state

Example:
```bash
# List all pending requests (default)
python list_approval_requests.py

# List all approved requests
python list_approval_requests.py --state APPROVED

# List all requests regardless of state
python list_approval_requests.py --state ALL
```

### Expected Output

The script will display approval requests in a formatted output:
```
Approval Requests (State: PENDING):
--------------------------------------------------------------------------------
Request Name: projects/123456789/approvalRequests/abcd1234
State: PENDING
Request Time: 2025-02-18 10:30:00 UTC
Requested Resource: //compute.googleapis.com/projects/...
Requested Reason: CUSTOMER_INITIATED_SUPPORT
Reason Detail: Case Number: 12345  # If detail is provided
Expiration Time: 2025-02-19 10:30:00 UTC
Requested Locations:  # If locations are specified
  principalOfficeCountry: ANY
  principalPhysicalLocationCountry: ANY
--------------------------------------------------------------------------------
```

Note: New approval requests from the API might not have an explicit state field. These requests are treated as "PENDING" since they are awaiting approval. When displaying such requests, the State field will show as "N/A" in the output, but they will be included when filtering for "PENDING" state.

If no requests are found for the specified state, you'll see:
```
No approval requests found with state 'PENDING'.