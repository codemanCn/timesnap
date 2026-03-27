import argparse
import json
import os
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


APP_DIRNAME = ".timeSnap"


@dataclass
class FileEntry:
    relative_path: str
    size: int
    mode: int
    created_at: str | None
    modified_at: str
    accessed_at: str

    def to_dict(self) -> dict:
        return {
            "relative_path": self.relative_path,
            "size": self.size,
            "mode": self.mode,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "accessed_at": self.accessed_at,
        }


def isoformat_timestamp(value: float | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).astimezone().isoformat()


def parse_timestamp(value: str) -> float:
    return datetime.fromisoformat(value).timestamp()


def iter_files(target: Path) -> Iterable[Path]:
    for path in sorted(target.rglob("*")):
        if not path.is_file():
            continue
        if APP_DIRNAME in path.parts:
            continue
        yield path


def snapshot_target(target: Path, name: str | None = None) -> str:
    target = target.resolve()
    state_root = target / APP_DIRNAME / "snapshots"
    snapshot_id = name or datetime.now().strftime("%Y%m%d-%H%M%S")
    snapshot_root = state_root / snapshot_id
    snapshot_root.mkdir(parents=True, exist_ok=False)

    entries: list[dict] = []
    for file_path in iter_files(target):
        relative_path = file_path.relative_to(target)
        stats = file_path.stat()
        birthtime = getattr(stats, "st_birthtime", None)
        entries.append(
            FileEntry(
                relative_path=str(relative_path),
                size=stats.st_size,
                mode=stat.S_IMODE(stats.st_mode),
                created_at=isoformat_timestamp(birthtime),
                modified_at=isoformat_timestamp(stats.st_mtime),
                accessed_at=isoformat_timestamp(stats.st_atime),
            ).to_dict()
        )

    manifest = {
        "snapshot_id": snapshot_id,
        "target_root": str(target),
        "created_at": datetime.now().astimezone().isoformat(),
        "files": entries,
    }
    manifest_path = snapshot_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return snapshot_id


def restore_snapshot(target: Path, snapshot_id: str, overwrite: bool = True) -> int:
    target = target.resolve()
    snapshot_root = target / APP_DIRNAME / "snapshots" / snapshot_id
    manifest_path = snapshot_root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"snapshot not found: {snapshot_id}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    restored = 0
    for entry in manifest["files"]:
        relative_path = Path(entry["relative_path"])
        destination = target / relative_path

        if not destination.exists():
            continue
        if destination.exists() and not overwrite:
            continue

        os.chmod(destination, entry["mode"])
        os.utime(
            destination,
            (
                parse_timestamp(entry["accessed_at"]),
                parse_timestamp(entry["modified_at"]),
            ),
        )
        restored += 1

    return restored


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="timesnap",
        description="遍历指定目录并把文件元数据快照保存到目标目录下的 .timeSnap 中，后续可按快照恢复权限与时间戳。",
        epilog=(
            "示例:\n"
            "  python -m timesnap snapshot /path/to/project\n"
            "  python -m timesnap snapshot /path/to/project --name release-1\n"
            "  python -m timesnap restore /path/to/project 20260327-120000\n"
            "  python -m timesnap restore /path/to/project release-1 --no-overwrite\n\n"
            "说明:\n"
            "  1. 快照目录固定为 <目标目录>/.timeSnap/snapshots/<snapshot_id>/\n"
            "  2. 记录的信息包括相对路径、文件大小、权限、创建时间(若平台支持)、修改时间、访问时间\n"
            "  3. 不保存文件原始副本，因此恢复只回放现有文件的权限、修改时间、访问时间\n"
            "  4. 创建时间只记录，不保证跨平台恢复"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser(
        "snapshot",
        help="为指定目录创建一个新快照",
        description="遍历目标目录中的文件，忽略 .timeSnap 自身，并把文件元数据清单写入 .timeSnap。",
    )
    snapshot_parser.add_argument("target", help="要扫描并保存快照的目录")
    snapshot_parser.add_argument(
        "--name",
        help="自定义快照 ID；默认使用当前时间，格式如 20260327-193000",
    )
    snapshot_parser.set_defaults(func=handle_snapshot)

    restore_parser = subparsers.add_parser(
        "restore",
        help="按快照恢复指定目录",
        description="从 .timeSnap 中读取某个快照，把保存过的元数据回放到目标目录中当前仍存在的文件。",
    )
    restore_parser.add_argument("target", help="要恢复的目录，必须包含 .timeSnap")
    restore_parser.add_argument("snapshot_id", help="要恢复的快照 ID")
    restore_parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="如果目标文件已存在，则跳过，不覆盖",
    )
    restore_parser.set_defaults(func=handle_restore)

    list_parser = subparsers.add_parser(
        "list",
        help="列出目录下已有的快照",
        description="显示目标目录 .timeSnap/snapshots 中的所有快照 ID。",
    )
    list_parser.add_argument("target", help="包含 .timeSnap 的目录")
    list_parser.set_defaults(func=handle_list)
    return parser


def handle_snapshot(args: argparse.Namespace) -> int:
    snapshot_id = snapshot_target(Path(args.target), name=args.name)
    print(f"Snapshot created: {snapshot_id}")
    return 0


def handle_restore(args: argparse.Namespace) -> int:
    restored = restore_snapshot(
        Path(args.target),
        args.snapshot_id,
        overwrite=not args.no_overwrite,
    )
    print(f"Restored files: {restored}")
    return 0


def handle_list(args: argparse.Namespace) -> int:
    target = Path(args.target).resolve()
    state_root = target / APP_DIRNAME / "snapshots"
    if not state_root.exists():
        print("No snapshots found.")
        return 0
    for path in sorted(p for p in state_root.iterdir() if p.is_dir()):
        print(path.name)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileExistsError as exc:
        print(f"Error: snapshot already exists: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
