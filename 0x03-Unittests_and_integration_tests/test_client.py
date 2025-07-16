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
        expected_response = {"login": org_name, "id": 123456}
        mock_get_json.return_value = expected_response

        client = GithubOrgClient(org_name)
        result = client.org

        mock_get_json.assert_called_once_with(
            f"https://api.github.com/orgs/{org_name}"
        )
        self.assertEqual(result, expected_response)

    def test_public_repos_url(self):
        """Test that _public_repos_url returns the correct URL"""
        test_payload = {
            "repos_url": "https://api.github.com/orgs/test-org/repos"
        }

        with patch('client.GithubOrgClient.org',
                   new_callable=PropertyMock,
                   return_value=test_payload) as mock_org:
            client = GithubOrgClient("test-org")
            result = client._public_repos_url

            self.assertEqual(result, test_payload["repos_url"])
            mock_org.assert_called_once()


if __name__ == '__main__':
    unittest.main()
