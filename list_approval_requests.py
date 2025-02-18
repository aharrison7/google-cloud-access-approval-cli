#!/usr/bin/env python3

import os
import sys
import json
import argparse
import logging
import csv
from typing import List, Dict
from datetime import datetime
import google.auth
from google.oauth2 import service_account
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from google.auth.exceptions import DefaultCredentialsError
from halo import Halo

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='List and manage Google Cloud Access Approval requests')
    parser.add_argument('--state', choices=['PENDING', 'APPROVED', 'DISMISSED', 'ALL'],
                      default='PENDING',
                      help='Filter requests by state (default: PENDING)')
    parser.add_argument('--approve',
                      help='Approve a specific request by name (e.g., projects/123/approvalRequests/abc)')
    parser.add_argument('--dismiss',
                      help='Dismiss a pending request by name (e.g., projects/123/approvalRequests/abc)')
    parser.add_argument('--revoke',
                      help='Revoke an approved request by name (e.g., projects/123/approvalRequests/abc)')
    parser.add_argument('--export',
                      choices=['json', 'csv'],
                      help='Export the results in specified format')
    parser.add_argument('--output',
                      help='Output file path for export (default: approval_requests.<format>)')
    parser.add_argument('--interactive', '-i', action='store_true',
                      help='Launch interactive request viewer')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug output')
    return parser.parse_args()

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

def get_approval_requests(client, project_id: str, state: str = 'PENDING') -> List[Dict]:
    """
    Retrieve approval requests for the project filtered by state.

    Args:
        client: The API client instance
        project_id: The Google Cloud project ID
        state: Filter state ('PENDING', 'APPROVED', 'DISMISSED', or 'ALL')
    """
    try:
        parent = f'projects/{project_id}'
        logger.debug(f"Making API request with parent: {parent}")

        spinner = Halo(text='Fetching approval requests...', spinner='dots')
        spinner.start()

        try:
            # List requests without filter first
            request_kwargs = {'parent': parent}
            request = client.projects().approvalRequests().list(**request_kwargs)

            approval_requests = []
            while request is not None:
                try:
                    response = request.execute()
                    logger.debug(f"Received response: {json.dumps(response, indent=2)}")
                    requests = response.get('approvalRequests', [])

                    # Filter locally if state is specified
                    if state != 'ALL':
                        # Treat requests without state as PENDING
                        requests = [r for r in requests if (r.get('state', 'PENDING') == state)]

                    approval_requests.extend(requests)
                    request = client.projects().approvalRequests().list_next(
                        previous_request=request,
                        previous_response=response
                    )
                except HttpError as e:
                    error_details = json.loads(e.content.decode())
                    logger.error(f"Error details: {json.dumps(error_details, indent=2)}")
                    if hasattr(e, 'resp'):
                        logger.error(f"Response status: {e.resp.status}")
                        logger.error(f"Response headers: {e.resp.headers}")
                    raise
            spinner.succeed('Successfully retrieved approval requests')
            return approval_requests

        except Exception as e:
            spinner.fail(f'Failed to fetch approval requests: {str(e)}')
            raise
        finally:
            if spinner.spinner_id:
                spinner.stop()

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

def display_approval_requests(approval_requests: List[Dict], state: str):
    """
    Format and display approval requests in a readable format with detailed information.
    """
    if not approval_requests:
        state_msg = f" with state '{state}'" if state != 'ALL' else ""
        print(f"\nNo approval requests found{state_msg}.")
        return

    print(f"\nApproval Requests{' (State: ' + state + ')' if state != 'ALL' else ''}:")
    print("=" * 100)

    for request in approval_requests:
        # Basic Information
        print(f"Request Name: {request.get('name', 'N/A')}")
        print(f"State: {request.get('state', 'N/A')}")
        print(f"Request Time: {format_timestamp(request.get('requestTime', 'N/A'))}")

        # Resource Information
        print("\nResource Details:")
        print(f"  Requested Resource: {request.get('requestedResourceName', 'N/A')}")
        resource_properties = request.get('requestedResourceProperties', {})
        if resource_properties:
            print("  Resource Properties:")
            for key, value in resource_properties.items():
                print(f"    {key}: {value}")

        # Request Reason
        print("\nRequest Context:")
        requested_reason = request.get('requestedReason', {})
        reason_type = requested_reason.get('type', 'N/A')
        reason_detail = requested_reason.get('detail', '')
        print(f"  Type: {reason_type}")
        if reason_detail:
            print(f"  Detail: {reason_detail}")

        # Location Information
        requested_locations = request.get('requestedLocations', {})
        if requested_locations:
            print("\nRequested Locations:")
            for key, value in requested_locations.items():
                formatted_key = key.replace('principal', 'Principal ').replace('Country', ' Country')
                print(f"  {formatted_key}: {value}")

        # Time Information
        print("\nTime Details:")
        print(f"  Created: {format_timestamp(request.get('requestTime', 'N/A'))}")

        # Handle expiration time, which can be either a string or a dictionary
        expiration = request.get('requestedExpiration', 'N/A')
        if isinstance(expiration, dict):
            expire_time = expiration.get('expireTime', 'N/A')
        else:
            expire_time = expiration
        if expire_time != 'N/A':
            expire_time = format_timestamp(expire_time)
        print(f"  Expires: {expire_time}")

        requested_duration = request.get('requestedDuration', 'N/A')
        if requested_duration != 'N/A':
            # Convert duration from seconds string (e.g., "432000s") to human-readable format
            try:
                duration_seconds = int(requested_duration.rstrip('s'))
                days = duration_seconds // 86400
                hours = (duration_seconds % 86400) // 3600
                duration_str = f"{days} days, {hours} hours"
                print(f"  Duration: {duration_str}")
            except (ValueError, AttributeError):
                print(f"  Duration: {requested_duration}")

        # Approval Information
        approve_info = request.get('approve', {})
        if approve_info:
            print("\nApproval Details:")
            print(f"  Approved Time: {format_timestamp(approve_info.get('approveTime', 'N/A'))}")
            print(f"  Approval Expiration: {format_timestamp(approve_info.get('expireTime', 'N/A'))}")

            # Include signature information if present
            signature_info = approve_info.get('signatureInfo', {})
            if signature_info:
                print("  Signature Information:")
                print(f"    Algorithm: {signature_info.get('googleKeyAlgorithm', 'N/A')}")
                # Only show first 32 chars of signature for security
                signature = signature_info.get('signature', '')
                if signature:
                    print(f"    Signature: {signature[:32]}...")

        print("=" * 100)

def approve_request(client, request_name: str) -> bool:
    """
    Approve a specific access request.
    """
    spinner = Halo(text=f'Approving request: {request_name}...', spinner='dots')
    spinner.start()

    try:
        logger.info(f"Approving request: {request_name}")
        approve_body = {
            'expireTime': None  # Let the system use the default expiration time
        }
        response = client.projects().approvalRequests().approve(
            name=request_name,
            body=approve_body
        ).execute()
        logger.info(f"Successfully approved request. New state: {response.get('state', 'UNKNOWN')}")
        spinner.succeed(f'Successfully approved request: {request_name}')
        return True
    except Exception as e:
        spinner.fail(f'Failed to approve request: {str(e)}')
        return False
    finally:
        if spinner.spinner_id:
            spinner.stop()

def dismiss_request(client, request_name: str) -> bool:
    """
    Dismiss a pending access request.
    """
    try:
        logger.info(f"Dismissing request: {request_name}")
        response = client.projects().approvalRequests().dismiss(
            name=request_name
        ).execute()
        logger.info(f"Successfully dismissed request. New state: {response.get('state', 'UNKNOWN')}")
        return True
    except HttpError as e:
        error_details = json.loads(e.content.decode())
        error_message = error_details.get('error', {}).get('message', 'Unknown error')
        error_code = error_details.get('error', {}).get('code')

        if error_code == 403:  # Permission denied
            error_message = (
                f"Permission denied: {error_message}\n\n"
                "To dismiss access requests, you need the following IAM permissions:\n"
                "1. accessapproval.approvalRequests.dismiss\n"
                "2. accessapproval.settings.update\n\n"
                "To grant these permissions:\n"
                "1. Visit the IAM & Admin console:\n"
                "   https://console.cloud.google.com/iam-admin/iam\n"
                "2. Find your account or service account\n"
                "3. Add the 'Access Approval Admin' role\n"
                "   (or add the specific permissions listed above)\n\n"
                "For more information, see:\n"
                "https://cloud.google.com/access-approval/docs/access-control"
            )
        elif error_code == 404:  # Request not found
            error_message = (
                f"Request not found: {error_message}\n"
                "The specified approval request may have expired or been deleted.\n"
                "Use --state ALL to list all available requests."
            )
        elif error_code == 400:  # Invalid request
            error_message = (
                f"Invalid request: {error_message}\n"
                "Please check that the request name is in the correct format:\n"
                "projects/[PROJECT_ID]/approvalRequests/[REQUEST_ID]"
            )
        elif error_code == 409:  # Conflict
            error_message = (
                f"Conflict error: {error_message}\n"
                "This usually means the request is already in a final state (DISMISSED or APPROVED)\n"
                "or the request has expired."
            )

        logger.error(f"Failed to dismiss request: {error_message}")
        return False

def revoke_request(client, request_name: str) -> bool:
    """
    Revoke an approved access request.
    """
    spinner = Halo(text=f'Revoking request: {request_name}...', spinner='dots')
    spinner.start()

    try:
        logger.info(f"Revoking approved request: {request_name}")
        # First, verify the request exists and check its state
        try:
            request = client.projects().approvalRequests().get(
                name=request_name
            ).execute()
            logger.debug(f"Current request state: {request.get('state')}")
            logger.debug(f"Full request details: {json.dumps(request, indent=2)}")
        except HttpError as e:
            if e.resp.status == 404:
                error_message = (
                    f"Request not found: {request_name}\n"
                    "The specified approval request may have expired or been deleted.\n"
                    "Use --state ALL to list all available requests."
                )
                logger.error(error_message)
                return False
            raise

        # Check if the request has an approval
        if 'approve' not in request:
            error_message = (
                f"Cannot revoke request that is not approved.\n"
                "Only approved requests can be revoked."
            )
            logger.error(error_message)
            return False

        # Use the invalidate method to revoke the approved request
        response = client.projects().approvalRequests().invalidate(
            name=request_name
        ).execute()

        new_state = response.get('state')
        logger.info(f"Successfully revoked request. New state: {new_state}")
        spinner.succeed(f'Successfully revoked request: {request_name}')
        return True

    except HttpError as e:
        error_details = json.loads(e.content.decode())
        error_message = error_details.get('error', {}).get('message', 'Unknown error')
        error_code = error_details.get('error', {}).get('code')

        if error_code == 403:  # Permission denied
            error_message = (
                f"Permission denied: {error_message}\n\n"
                "To revoke approved requests, you need the following IAM permissions:\n"
                "1. accessapproval.approvalRequests.invalidate\n"
                "2. accessapproval.settings.update\n\n"
                "To grant these permissions:\n"
                "1. Visit the IAM & Admin console:\n"
                "   https://console.cloud.google.com/iam-admin/iam\n"
                "2. Find your account or service account\n"
                "3. Add the 'Access Approval Admin' role\n"
                "   (or add the specific permissions listed above)\n\n"
                "For more information, see:\n"
                "https://cloud.google.com/access-approval/docs/access-control"
            )
        elif error_code == 400:  # Invalid request
            error_message = (
                f"Invalid request: {error_message}\n"
                "Please check that the request name is in the correct format:\n"
                "projects/[PROJECT_ID]/approvalRequests/[REQUEST_ID]"
            )
        elif error_code == 409:  # Conflict
            error_message = (
                f"Conflict error: {error_message}\n"
                "This usually means the request has already been revoked or has expired."
            )

        logger.error(f"Failed to revoke request: {error_message}")
        spinner.fail(f'Failed to revoke request: {error_message}')
        return False
    finally:
        if spinner.spinner_id:
            spinner.stop()

def export_requests(requests: List[Dict], format: str, output_path: str = None):
    """
    Export approval requests to JSON or CSV format.
    Args:
        requests: List of approval request dictionaries
        format: Output format ('json' or 'csv')
        output_path: Optional output file path
    """
    if not output_path:
        output_path = f"approval_requests.{format}"

    try:
        if format == 'json':
            with open(output_path, 'w') as f:
                json.dump(requests, f, indent=2)
        else:  # CSV format
            if not requests:
                logger.warning("No requests to export")
                return

            # Extract fields from the first request to use as CSV headers
            headers = ['name', 'state', 'requestTime', 'requestedResourceName',
                      'requestedReason.type', 'requestedReason.detail',
                      'requestedExpiration', 'requestedLocations']

            with open(output_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for request in requests:
                    # Flatten nested structures for CSV
                    row = {
                        'name': request.get('name'),
                        'state': request.get('state', 'N/A'),
                        'requestTime': request.get('requestTime'),
                        'requestedResourceName': request.get('requestedResourceName'),
                        'requestedReason.type': request.get('requestedReason', {}).get('type'),
                        'requestedReason.detail': request.get('requestedReason', {}).get('detail'),
                        'requestedExpiration': (
                            request.get('requestedExpiration', {}).get('expireTime')
                            if isinstance(request.get('requestedExpiration'), dict)
                            else request.get('requestedExpiration')
                        ),
                        'requestedLocations': json.dumps(request.get('requestedLocations', {}))
                    }
                    writer.writerow(row)

        logger.info(f"Successfully exported requests to {output_path}")
    except Exception as e:
        logger.error(f"Failed to export requests: {str(e)}")
        raise

def main():
    """
    Main function to list and manage approval requests.
    """
    try:
        # Parse command line arguments
        args = parse_arguments()

        # Set logging level based on debug flag
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)

        # Set up authentication
        auth_spinner = Halo(text='Authenticating with Google Cloud...', spinner='dots')
        auth_spinner.start()
        try:
            credentials, project_id = setup_credentials()
            auth_spinner.succeed('Authentication successful')
        except Exception as e:
            auth_spinner.fail(f'Authentication failed: {str(e)}')
            raise
        finally:
            if auth_spinner.spinner_id:
                auth_spinner.stop()

        # Initialize API client
        client_spinner = Halo(text='Initializing Access Approval API client...', spinner='dots')
        client_spinner.start()
        try:
            client = initialize_api_client(credentials)
            client_spinner.succeed('API client initialized')
        except Exception as e:
            client_spinner.fail(f'Failed to initialize API client: {str(e)}')
            raise
        finally:
            if client_spinner.spinner_id:
                client_spinner.stop()

        # Handle various operations with spinners
        if args.approve:
            if approve_request(client, args.approve):
                print(f"Successfully approved request: {args.approve}")
                return
            else:
                print(f"Failed to approve request: {args.approve}", file=sys.stderr)
                sys.exit(1)

        if args.revoke:
            if revoke_request(client, args.revoke):
                print(f"Successfully revoked request: {args.revoke}")
                return
            else:
                print(f"Failed to revoke request: {args.revoke}", file=sys.stderr)
                sys.exit(1)

        if args.dismiss:
            dismiss_spinner = Halo(text=f'Dismissing request: {args.dismiss}...', spinner='dots')
            dismiss_spinner.start()
            try:
                if dismiss_request(client, args.dismiss):
                    print(f"Successfully dismissed request: {args.dismiss}")
                    dismiss_spinner.succeed(f'Successfully dismissed request: {args.dismiss}')
                    return
                else:
                    dismiss_spinner.fail(f'Failed to dismiss request: {args.dismiss}')
                    print(f"Failed to dismiss request: {args.dismiss}", file=sys.stderr)
                    sys.exit(1)
            except Exception as e:
                dismiss_spinner.fail(f"Failed to dismiss request: {str(e)}")
                raise
            finally:
                if dismiss_spinner.spinner_id:
                    dismiss_spinner.stop()


        # Get approval requests
        approval_requests = get_approval_requests(client, project_id, args.state)

        if args.interactive:
            from interactive_viewer import view_requests
            result = view_requests(approval_requests)
            if result:
                request_name = result['request']['name']
                if result['action'] == 'approve':
                    if approve_request(client, request_name):
                        print(f"Successfully approved request: {request_name}")
                    else:
                        print(f"Failed to approve request: {request_name}", file=sys.stderr)
                        sys.exit(1)
                elif result['action'] == 'dismiss':
                    if dismiss_request(client, request_name):
                        print(f"Successfully dismissed request: {request_name}")
                    else:
                        print(f"Failed to dismiss request: {request_name}", file=sys.stderr)
                        sys.exit(1)
                elif result['action'] == 'revoke':
                    if revoke_request(client, request_name):
                        print(f"Successfully revoked request: {request_name}")
                    else:
                        print(f"Failed to revoke request: {request_name}", file=sys.stderr)
                        sys.exit(1)
            return

        # Export or display results
        if args.export:
            export_spinner = Halo(text=f'Exporting requests to {args.export} format...', spinner='dots')
            export_spinner.start()
            try:
                export_requests(approval_requests, args.export, args.output)
                export_spinner.succeed(f'Successfully exported requests to {args.output or f"approval_requests.{args.export}"}')
            except Exception as e:
                export_spinner.fail(f'Failed to export requests: {str(e)}')
                raise
            finally:
                if export_spinner.spinner_id:
                    export_spinner.stop()
        else:
            # Display results
            display_approval_requests(approval_requests, args.state)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()