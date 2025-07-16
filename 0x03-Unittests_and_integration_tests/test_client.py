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
        """Test GithubOrgClient.org returns correct value"""
        expected_response = {"login": org_name, "id": 123456}
        mock_get_json.return_value = expected_response

        client = GithubOrgClient(org_name)
        result = client.org

        mock_get_json.assert_called_once_with(
            f"https://api.github.com/orgs/{org_name}"
        )
        self.assertEqual(result, expected_response)

    def test_public_repos_url(self):
        """Test that _public_repos_url returns correct URL"""
        test_payload = {"repos_url": "https://api.github.com/orgs/test/repos"}

        with patch('client.GithubOrgClient.org',
                 new_callable=PropertyMock,
                 return_value=test_payload) as mock_org:
            client = GithubOrgClient("test")
            result = client._public_repos_url

            self.assertEqual(result, test_payload["repos_url"])
            mock_org.assert_called_once()

    @patch('client.get_json')
    def test_public_repos(self, mock_get_json):
        """Test that public_repos returns expected repos"""
        test_payload = [
            {"name": "repo1", "license": {"key": "mit"}},
            {"name": "repo2", "license": {"key": "apache-2.0"}},
        ]
        mock_get_json.return_value = test_payload

        test_url = "https://api.github.com/orgs/test/repos"
        with patch('client.GithubOrgClient._public_repos_url',
                 new_callable=PropertyMock,
                 return_value=test_url) as mock_url:
            client = GithubOrgClient("test")
            result = client.public_repos()

            self.assertEqual(result, ["repo1", "repo2"])
            mock_get_json.assert_called_once_with(test_url)
            mock_url.assert_called_once()

    @parameterized.expand([
        ({"license": {"key": "my_license"}}, "my_license", True),
        ({"license": {"key": "other_license"}}, "my_license", False),
    ])
    def test_has_license(self, repo, license_key, expected):
        """Test that has_license returns the correct boolean"""
        client = GithubOrgClient("test")
        result = client.has_license(repo, license_key)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
