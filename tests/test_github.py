import base64
import unittest
from unittest.mock import patch

from providers.github import GitHubClient, GitHubError


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status
        self.content = b"{}"

    def json(self):
        return self.payload


class GitHubClientTest(unittest.TestCase):
    def test_repo_validation(self):
        self.assertEqual(GitHubClient.validate_repo("owner/repo"), "owner/repo")
        for value in ("https://github.com/a/b", "a/b/c", "../b", ""):
            with self.assertRaises(GitHubError):
                GitHubClient.validate_repo(value)

    def test_token_is_required(self):
        with self.assertRaises(GitHubError):
            GitHubClient("").list_files("owner/repo", "main")

    @patch("providers.github.requests.request")
    def test_read_text_file(self, request):
        payload = {"encoding": "base64", "size": 4,
                   "content": base64.b64encode(b"test").decode()}
        request.return_value = FakeResponse(payload)
        client = GitHubClient("secret")
        self.assertEqual(client.get_text_file("owner/repo", "src/a.py", "main"), "test")
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer secret")

    @patch("providers.github.requests.request")
    def test_create_branch_commit_and_pull_request(self, request):
        request.side_effect = [
            FakeResponse({"object": {"sha": "base-sha"}}),
            FakeResponse({"tree": {"sha": "base-tree"}}),
            FakeResponse({"sha": "blob-sha"}),
            FakeResponse({"sha": "tree-sha"}),
            FakeResponse({"sha": "commit-sha"}),
            FakeResponse({}),
            FakeResponse({"number": 7, "html_url": "https://github.com/o/r/pull/7"}),
        ]
        result = GitHubClient("secret").create_pull_request(
            "o/r", "main", "ai/update-1", "Update", "Details", {"a.py": "print(1)"})
        self.assertEqual(result["number"], 7)
        self.assertEqual(result["branch"], "ai/update-1")
        self.assertEqual(request.call_args_list[-2].args[0], "POST")
        self.assertTrue(request.call_args_list[-1].args[1].endswith("/pulls"))

    def test_reject_path_traversal(self):
        with self.assertRaises(GitHubError):
            GitHubClient("secret").get_text_file("o/r", "../secret", "main")


if __name__ == "__main__":
    unittest.main()
