"""GitHub 공개 레포에서 최신 코드를 받아 src/등록된 실행 파일을 갱신한다.

git 설치를 요구하지 않기 위해 GitHub의 zip 아카이브 다운로드 링크만 사용한다.
사용자 데이터(티커리스트.xlsx, output/, legacy/, 사용가이드.docx)는 절대 건드리지 않고,
코드/실행 스크립트에 해당하는 경로만 통째로 교체한다.
"""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

import requests

REPO_OWNER = "Jaeooo"
REPO_NAME = "kr-stock-daily-crawler"
BRANCH = "main"

API_LATEST_COMMIT_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{BRANCH}"
ZIP_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/{BRANCH}.zip"

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
VERSION_FILE = PROJECT_ROOT / ".update_version"

# 업데이트 때 통째로 교체할 경로 (전부 코드/실행 스크립트 — 사용자 데이터 아님)
UPDATE_PATHS = ["src", "run_gui.bat", "setup.bat", "automation"]

REQUEST_TIMEOUT = 15


def get_remote_latest_sha() -> str:
    resp = requests.get(
        API_LATEST_COMMIT_URL,
        headers={"Accept": "application/vnd.github+json"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["sha"]


def get_local_version() -> str | None:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    return None


def set_local_version(sha: str) -> None:
    VERSION_FILE.write_text(sha, encoding="utf-8")


def _replace_path(dst: Path, src_new: Path, tmp_path: Path) -> None:
    """dst를 src_new 내용으로 교체한다. 실패하면 원래 상태로 되돌린다."""
    backup = None
    if dst.exists():
        backup = tmp_path / f"backup_{dst.name}"
        shutil.move(str(dst), str(backup))
    try:
        if src_new.is_dir():
            shutil.copytree(src_new, dst)
        else:
            shutil.copy2(src_new, dst)
    except Exception:
        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        if backup is not None:
            shutil.move(str(backup), str(dst))
        raise


def apply_update(sha: str) -> None:
    resp = requests.get(ZIP_URL, timeout=60)
    resp.raise_for_status()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "repo.zip"
        zip_path.write_bytes(resp.content)

        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_path)

        extracted_root = next(
            p for p in tmp_path.iterdir() if p.is_dir() and p.name.startswith(REPO_NAME)
        )

        for rel in UPDATE_PATHS:
            src_new = extracted_root / rel
            if not src_new.exists():
                continue
            _replace_path(PROJECT_ROOT / rel, src_new, tmp_path)

    set_local_version(sha)


def check_and_update() -> str:
    """업데이트 확인 후 있으면 바로 적용한다. 사용자에게 보여줄 결과 메시지를 반환한다."""
    latest_sha = get_remote_latest_sha()
    local_sha = get_local_version()

    if local_sha == latest_sha:
        return "이미 최신 버전이야."

    apply_update(latest_sha)
    return "업데이트를 적용했어. 프로그램을 껐다가 다시 실행해줘."
