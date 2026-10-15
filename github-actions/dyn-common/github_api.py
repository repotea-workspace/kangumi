"""Small GitHub REST client; never prints authorization headers or error bodies."""

import base64
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


class GitHubError(RuntimeError):
    def __init__(self, status, path):
        self.status = status
        super().__init__(f"GitHub API {status}: {path.split('?')[0]}")


class GitHub:
    def __init__(self, token, api_url="https://api.github.com"):
        parsed = urlsplit(api_url)
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("GitHub API must use an HTTPS origin")
        if not token:
            raise ValueError("GitHub token is required")
        self.token = token
        self.api_url = api_url.rstrip("/")

    def request(self, method, path, body=None, params=None):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("GitHub API requires an absolute API path")
        url = self.api_url + path
        if params:
            url += "?" + urlencode(params)
        data = None if body is None else json.dumps(body).encode()
        request = Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        })
        for attempt in range(3):
            try:
                with urlopen(request, timeout=30) as response:
                    return json.load(response)
            except HTTPError as error:
                if error.code in (429, 502, 503, 504) and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise GitHubError(error.code, path) from None
            except (URLError, TimeoutError):
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise GitHubError("unavailable", path) from None

    def get(self, path, **params):
        return self.request("GET", path, params=params)

    def post(self, path, body):
        return self.request("POST", path, body)

    def pages(self, path, key=None, **params):
        for page in range(1, 101):
            data = self.get(path, **params, per_page=100, page=page)
            items = data[key] if key else data
            yield from items
            if len(items) < 100:
                return
        raise RuntimeError("GitHub pagination limit reached; refusing an incomplete result")

    def file(self, repository, path, ref):
        data = self.get(f"/repos/{repository}/contents/{path}", ref=ref)
        if not isinstance(data, dict) or data.get("encoding") != "base64":
            raise ValueError("expected a small GitHub repository file")
        return base64.b64decode(data["content"], validate=False)

    def statuses(self, repository, sha):
        return self.pages(f"/repos/{repository}/commits/{sha}/statuses")


def latest_status(api, repository, sha, context):
    # The statuses endpoint is newest first. Do not use the combined status
    # endpoint: an empty list there is also summarized as 'pending'.
    return next((item for item in api.statuses(repository, sha) if item["context"] == context), None)


def post_status(api, repository, sha, context, state, description, url):
    return api.post(f"/repos/{repository}/statuses/{sha}", {
        "state": state,
        "context": context,
        "description": description[:140],
        "target_url": url,
    })


def is_source_bot(status):
    creator = status.get("creator") or {}
    return creator.get("login") == "github-actions[bot]" and creator.get("type") == "Bot"
