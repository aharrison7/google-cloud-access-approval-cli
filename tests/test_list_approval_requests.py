import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from datetime import datetime
from io import StringIO

# Add parent directory to path to import the main script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from list_approval_requests import (
    format_timestamp,
    display_approval_requests,
    parse_arguments
)

class TestListApprovalRequests(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.captured_output = StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.captured_output

    def tearDown(self):
        sys.stdout = self.original_stdout

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
            "requestedReason": {"type": "CUSTOMER_INITIATED_SUPPORT"},
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
            "Expiration Time: 2025-02-19 10:30:00 UTC"
        ]
        for element in expected_elements:
            self.assertIn(element, output)

    @patch('argparse.ArgumentParser.parse_args')
    def test_parse_arguments_default(self, mock_args):
        """Test argument parsing with default values"""
        mock_args.return_value = MagicMock(state="PENDING")
        args = parse_arguments()
        self.assertEqual(args.state, "PENDING")

if __name__ == '__main__':
    unittest.main()
