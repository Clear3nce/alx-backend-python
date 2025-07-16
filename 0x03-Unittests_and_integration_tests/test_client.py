#!/usr/bin/env python3
"""Test module for client.GithubOrgClient class"""
import unittest
from parameterized import parameterized
from unittest.mock import patch, PropertyMock
from client import GithubOrgClient


class TestGithubOrgClient(unittest.TestCase):
    """Test class for GithubOrgClient"""
    @parameterized.expand([
        ("google",),
        ("abc",),
    ])
    @patch('client.get_json')
    def test_org(self, org_name, mock_get_json):
        """
        Test that GithubOrgClient.org returns correct value
        and makes exactly one call to get_json with expected argument
        """
        # Set up the mock return value
        expected_response = {"login": org_name, "id": 123456}
        mock_get_json.return_value = expected_response

        # Create client instance and call the org property
        client = GithubOrgClient(org_name)
        result = client.org

        # Verify get_json was called once with correct URL
        mock_get_json.assert_called_once_with(
            f"https://api.github.com/orgs/{org_name}"
        )
        
        # Verify the result matches expected response
        self.assertEqual(result, expected_response)


if __name__ == '__main__':
    unittest.main()
