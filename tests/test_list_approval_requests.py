import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
from datetime import datetime
from io import StringIO
import logging

# Add parent directory to path to import the main script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from list_approval_requests import (
    format_timestamp,
    display_approval_requests,
    parse_arguments,
    get_approval_requests,
    main
)

class TestListApprovalRequests(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.captured_output = StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.captured_output
        # Capture logging output
        self.log_output = StringIO()
        self.log_handler = logging.StreamHandler(self.log_output)
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)

    def tearDown(self):
        sys.stdout = self.original_stdout
        logging.getLogger().removeHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)

    def test_format_timestamp(self):
        """Test timestamp formatting function"""
        # Test valid timestamp
        input_timestamp = "2025-02-18T10:30:00Z"
        expected_output = "2025-02-18 10:30:00 UTC"
        self.assertEqual(format_timestamp(input_timestamp), expected_output)

        # Test invalid timestamp
        invalid_timestamp = "invalid-timestamp"
        self.assertEqual(format_timestamp(invalid_timestamp), invalid_timestamp)

    def test_display_approval_requests_empty(self):
        """Test display function with empty requests"""
        display_approval_requests([], "PENDING")
        output = self.captured_output.getvalue()
        self.assertIn("No approval requests found with state 'PENDING'", output)

    def test_display_approval_requests_with_data(self):
        """Test display function with sample data"""
        sample_request = {
            "name": "projects/123456789/approvalRequests/abcd1234",
            "state": "PENDING",
            "requestTime": "2025-02-18T10:30:00Z",
            "requestedResourceName": "//compute.googleapis.com/projects/test",
            "requestedReason": {"type": "CUSTOMER_INITIATED_SUPPORT", "detail": "Case Number: 12345"},
            "requestedExpiration": {"expireTime": "2025-02-19T10:30:00Z"}
        }
        display_approval_requests([sample_request], "PENDING")
        output = self.captured_output.getvalue()

        expected_elements = [
            "Approval Requests (State: PENDING):",
            "Request Name: projects/123456789/approvalRequests/abcd1234",
            "State: PENDING",
            "Request Time: 2025-02-18 10:30:00 UTC",
            "Requested Resource: //compute.googleapis.com/projects/test",
            "Requested Reason: CUSTOMER_INITIATED_SUPPORT",
            "Reason Detail: Case Number: 12345",
            "Expiration Time: 2025-02-19 10:30:00 UTC"
        ]
        for element in expected_elements:
            self.assertIn(element, output)

    def test_display_approval_requests_without_state(self):
        """Test display function with request missing state field"""
        sample_request = {
            "name": "projects/123456789/approvalRequests/abcd1234",
            "requestTime": "2025-02-18T10:30:00Z",
            "requestedResourceName": "//compute.googleapis.com/projects/test",
            "requestedReason": {
                "type": "CUSTOMER_INITIATED_SUPPORT",
                "detail": "Case Number: 12345"
            },
            "requestedExpiration": "2025-02-19T10:30:00Z"
        }
        display_approval_requests([sample_request], "PENDING")
        output = self.captured_output.getvalue()

        expected_elements = [
            "Approval Requests (State: PENDING):",
            "Request Name: projects/123456789/approvalRequests/abcd1234",
            "State: N/A",
            "Request Time: 2025-02-18 10:30:00 UTC",
            "Requested Resource: //compute.googleapis.com/projects/test",
            "Requested Reason: CUSTOMER_INITIATED_SUPPORT",
            "Reason Detail: Case Number: 12345",
            "Expiration Time: 2025-02-19 10:30:00 UTC"
        ]
        for element in expected_elements:
            self.assertIn(element, output)

    def test_expiration_time_edge_cases(self):
        """Test various expiration time formats and edge cases"""
        test_cases = [
            # Dictionary format with valid time
            ({
                "name": "test1",
                "requestedExpiration": {"expireTime": "2025-02-19T10:30:00Z"}
            }, "2025-02-19 10:30:00 UTC"),
            # String format
            ({
                "name": "test2",
                "requestedExpiration": "2025-02-19T10:30:00Z"
            }, "2025-02-19 10:30:00 UTC"),
            # Missing expiration
            ({
                "name": "test3"
            }, "N/A"),
            # Invalid expiration format
            ({
                "name": "test4",
                "requestedExpiration": {"invalid": "format"}
            }, "N/A")
        ]

        for request, expected_time in test_cases:
            display_approval_requests([request], "ALL")
            output = self.captured_output.getvalue()
            self.assertIn(f"Expiration Time: {expected_time}", output)
            self.captured_output.truncate(0)
            self.captured_output.seek(0)

    @patch('argparse.ArgumentParser.parse_args')
    def test_parse_arguments_debug_flag(self, mock_args):
        """Test parsing of debug flag"""
        # Test with debug enabled
        mock_args.return_value = MagicMock(state="PENDING", debug=True)
        args = parse_arguments()
        self.assertTrue(args.debug)

        # Test with debug disabled
        mock_args.return_value = MagicMock(state="PENDING", debug=False)
        args = parse_arguments()
        self.assertFalse(args.debug)

    @patch('google.auth.default')
    @patch('googleapiclient.discovery.build')
    def test_get_approval_requests_state_filtering(self, mock_build, mock_auth):
        """Test filtering of approval requests by state"""
        # Mock the API response with a request without state field
        mock_response = {
            "approvalRequests": [
                {
                    "name": "projects/123/approvalRequests/xyz",
                    "requestTime": "2025-02-18T10:30:00Z",
                    "requestedResourceName": "//test.googleapis.com/projects/123"
                }
            ]
        }

        # Set up mock client
        mock_client = MagicMock()
        mock_list = MagicMock()
        mock_list.execute.return_value = mock_response
        mock_client.projects().approvalRequests().list.return_value = mock_list
        mock_client.projects().approvalRequests().list_next.return_value = None
        mock_build.return_value = mock_client

        # Mock credentials
        mock_auth.return_value = (MagicMock(), "123")

        # Test PENDING state - should include request without state
        requests = get_approval_requests(mock_client, "123", "PENDING")
        self.assertEqual(len(requests), 1)

        # Test APPROVED state - should not include request without state
        requests = get_approval_requests(mock_client, "123", "APPROVED")
        self.assertEqual(len(requests), 0)

    @patch('sys.argv')
    @patch('google.auth.default')
    @patch('googleapiclient.discovery.build')
    def test_debug_output(self, mock_build, mock_auth, mock_argv):
        """Test debug output with and without debug flag"""
        # Mock API response
        mock_response = {
            "approvalRequests": [
                {
                    "name": "test_request",
                    "requestTime": "2025-02-18T10:30:00Z"
                }
            ]
        }

        # Set up mocks
        mock_client = MagicMock()
        mock_list = MagicMock()
        mock_list.execute.return_value = mock_response
        mock_client.projects().approvalRequests().list.return_value = mock_list
        mock_client.projects().approvalRequests().list_next.return_value = None
        mock_build.return_value = mock_client
        mock_auth.return_value = (MagicMock(), "123")

        # Test without debug flag
        mock_argv.return_value = ["script.py"]
        logging.getLogger().setLevel(logging.INFO) # added line
        main()
        normal_output = self.log_output.getvalue()
        self.assertNotIn("Making API request with parent:", normal_output)
        self.assertNotIn("Received response:", normal_output)

        # Clear outputs
        self.log_output.truncate(0)
        self.log_output.seek(0)
        self.captured_output.truncate(0)
        self.captured_output.seek(0)

        # Test with debug flag
        mock_argv.return_value = ["script.py", "--debug"]
        logging.getLogger().setLevel(logging.INFO) # added line
        main()
        debug_output = self.log_output.getvalue()
        # Debug messages should be present when debug flag is used
        self.assertIn("Making API request with parent: projects/123", debug_output)
        self.assertIn("Received response:", debug_output)

if __name__ == '__main__':
    unittest.main()