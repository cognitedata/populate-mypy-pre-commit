import argparse
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

PRE_COMMIT_CONFIG_FILE_PATH = ".pre-commit-config.yaml"
MYPY_PRE_COMMIT_REPO = "https://github.com/pre-commit/mirrors-mypy"
MYPY_PRE_COMMIT_HOOK_ID = "mypy"


def get_poetry_dependencies() -> List[str]:
    cmd = ["poetry", "export", "-f", "requirements.txt", "--without-hashes"]
    poetry_subprocess = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    deps = list()
    assert poetry_subprocess.stdout is not None, "No dependencies exported from poetry"
    for line in poetry_subprocess.stdout.readlines():
        res = re.match(r"^(.+==\d+\.\d+(?:\.\d+)?(?:\.\d+)?).*$", line.decode())
        if res:
            deps.append(res.group(1))
    return deps


def get_existing_mypy_dependencies() -> List[str]:
    with open(PRE_COMMIT_CONFIG_FILE_PATH, "r") as fh:
        res = yaml.safe_load(fh)
        repo_i, hook_i = find_mypy_repo_and_hook_index(res)
        existing_dependencies = res["repos"][repo_i]["hooks"][hook_i].get("additional_dependencies", [])
    return existing_dependencies


def find_mypy_repo_and_hook_index(pre_commit_config_dict: Dict) -> Tuple[int, int]:
    repos = pre_commit_config_dict["repos"]
    for repo_i, repo in enumerate(repos):
        if repo["repo"] == MYPY_PRE_COMMIT_REPO:
            hooks = repo["hooks"]
            for hook_i, hook in enumerate(hooks):
                if hook["id"] == MYPY_PRE_COMMIT_HOOK_ID:
                    return repo_i, hook_i
    raise ValueError("Could not find the mypy hook in .pre-commit-config.yaml")


def update_dependencies() -> None:
    deps = get_poetry_dependencies()
    with open(PRE_COMMIT_CONFIG_FILE_PATH, "r+") as fh:
        res = yaml.safe_load(fh)
        repo_i, hook_i = find_mypy_repo_and_hook_index(res)
        res["repos"][repo_i]["hooks"][hook_i]["additional_dependencies"] = deps
        fh.truncate(0)
        fh.seek(0)
        yaml.dump(res, fh)


def dependencies_are_up_to_date() -> bool:
    existing_deps = get_existing_mypy_dependencies()
    poetry_dependencies = get_poetry_dependencies()
    return set(existing_deps) == set(poetry_dependencies)


def main():
    exit_code = 0 if dependencies_are_up_to_date() else 1
    if exit_code == 1:
        print(f"Dependencies are not up to date. Updating {PRE_COMMIT_CONFIG_FILE_PATH}.")
        update_dependencies()
    exit(exit_code)


if __name__ == "__main__":
    main()
