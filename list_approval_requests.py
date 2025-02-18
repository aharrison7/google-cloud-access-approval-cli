#!/usr/bin/env python3

import os
import sys
import json
from typing import List, Dict
from datetime import datetime
import google.auth
from google.oauth2 import service_account
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from google.auth.exceptions import DefaultCredentialsError

def setup_credentials():
    """
    Set up Google Cloud credentials using default application credentials
    or service account key file.
    """
    try:
        # First try application default credentials
        credentials, _ = google.auth.default()
        return credentials, "320306361664"  # Using the specific project ID
    except DefaultCredentialsError:
        # If no default credentials, look for service account key file or content
        key_path_or_content = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not key_path_or_content:
            raise Exception(
                "No credentials found. Please set GOOGLE_APPLICATION_CREDENTIALS "
                "environment variable to point to your service account key file "
                "or contain the service account JSON content."
            )

        try:
            # First try to parse as JSON content
            try:
                info = json.loads(key_path_or_content)
                credentials = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                return credentials, "320306361664"  # Using the specific project ID
            except json.JSONDecodeError:
                # If not valid JSON, try as file path
                if not os.path.exists(key_path_or_content):
                    raise Exception(
                        f"Service account key file not found at: {key_path_or_content}"
                    )
                credentials = service_account.Credentials.from_service_account_file(
                    key_path_or_content,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                return credentials, "320306361664"  # Using the specific project ID
        except Exception as e:
            raise Exception(f"Failed to setup credentials: {str(e)}")

def initialize_api_client(credentials):
    """
    Initialize the Access Approval API client.
    """
    try:
        return discovery.build(
            'accessapproval',
            'v1',
            credentials=credentials,
            cache_discovery=False
        )
    except Exception as e:
        raise Exception(f"Failed to initialize API client: {str(e)}")

def format_timestamp(timestamp: str) -> str:
    """
    Format API timestamp to human-readable format.
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except ValueError:
        return timestamp

def get_approval_requests(client, project_id: str) -> List[Dict]:
    """
    Retrieve all open approval requests for the project.
    """
    try:
        parent = f'projects/{project_id}'
        print(f"Making API request with parent: {parent}")
        request = client.projects().approvalRequests().list(
            parent=parent,
            filter='state=PENDING'  # Updated filter syntax without quotes
        )

        approval_requests = []
        while request is not None:
            try:
                response = request.execute()
                print(f"Received response: {json.dumps(response, indent=2)}")
                approval_requests.extend(response.get('approvalRequests', []))
                request = client.projects().approvalRequests().list_next(
                    previous_request=request,
                    previous_response=response
                )
            except HttpError as e:
                error_details = json.loads(e.content.decode())
                print(f"Error details: {json.dumps(error_details, indent=2)}")
                raise

        return approval_requests
    except HttpError as e:
        error_details = json.loads(e.content.decode())
        error_message = f"API request failed for project {project_id}: {error_details.get('error', {}).get('message', 'Unknown error')}"
        if 'SERVICE_DISABLED' in str(e):
            error_message += (
                "\nThe Access Approval API is not enabled for this project. To enable it:\n"
                "1. Visit the Google Cloud Console:\n"
                "   https://console.cloud.google.com/apis/library/accessapproval.googleapis.com\n"
                "2. Select your project and click 'Enable'\n"
                "3. Wait a few minutes for the change to take effect\n"
                "4. Run this script again\n"
            )
        raise Exception(error_message)


def display_approval_requests(approval_requests: List[Dict]):
    """
    Format and display approval requests in a readable format.
    """
    if not approval_requests:
        print("\nNo pending approval requests found.")
        return

    print("\nPending Approval Requests:")
    print("-" * 80)

    for request in approval_requests:
        print(f"Request Name: {request.get('name', 'N/A')}")
        print(f"Request Time: {format_timestamp(request.get('requestTime', 'N/A'))}")
        print(f"Requested Resource: {request.get('requestedResourceName', 'N/A')}")
        print(f"Requested Reason: {request.get('requestedReason', {}).get('type', 'N/A')}")

        expire_time = request.get('requestedExpiration', {}).get('expireTime', 'N/A')
        if expire_time != 'N/A':
            expire_time = format_timestamp(expire_time)
        print(f"Expiration Time: {expire_time}")

        print("-" * 80)

def main():
    """
    Main function to list open approval requests.
    """
    try:
        # Set up authentication
        print("Authenticating with Google Cloud...")
        credentials, project_id = setup_credentials()

        # Initialize API client
        print("Initializing Access Approval API client...")
        client = initialize_api_client(credentials)

        # Get approval requests
        print(f"Fetching approval requests for project: {project_id}")
        approval_requests = get_approval_requests(client, project_id)

        # Display results
        display_approval_requests(approval_requests)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()