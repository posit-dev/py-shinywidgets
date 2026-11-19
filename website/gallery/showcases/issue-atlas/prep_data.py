import argparse
import subprocess
from pathlib import Path

from issues import REPOS, prep_repo

RAW = Path(__file__).parent / "data" / "raw"

JQ = """
.[] | select(.pull_request | not) | {
  repo: "%s", number, title, body: ((.body // "")[0:3000]), state, state_reason,
  created_at, closed_at, comments, reactions: .reactions.total_count,
  labels: [.labels[].name], user: .user.login, html_url
} | tojson
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="re-fetch repos already on disk")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    total = 0
    for repo in REPOS:
        n = prep_repo(repo, RAW, fetch_gh, refresh=args.refresh)
        total += n
        print(f"{repo:<28} {n:>5,}", flush=True)
    print(f"{'total':<28} {total:>5,}")


def fetch_gh(repo: str) -> str:
    result = subprocess.run(
        [
            "gh", "api", "--paginate",
            f"repos/{repo}/issues?state=all&per_page=100",
            "--jq", JQ % repo,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


if __name__ == "__main__":
    main()
