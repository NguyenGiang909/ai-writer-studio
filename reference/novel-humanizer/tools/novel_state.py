#!/usr/bin/env python3
"""Small file-state helper for Novel Humanizer Universal v3.

Structural persistence/checks only. This script does NOT perform semantic story QC.
No third-party dependencies. Invoke with `python novel_state.py --help`.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def write_atomic(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".tmp_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.remove(temp)


def json_load(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return obj


def json_save(path: Path, obj: dict):
    write_atomic(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backup(path: Path, root: Path):
    if not path.exists():
        return
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    relative = path.relative_to(root)
    b = root / ".history" / stamp / relative
    b.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, b)


def ensure_project(root: Path) -> str:
    profile = root / "CHAPTER_INDEX.json"
    if not profile.is_file():
        raise FileNotFoundError(f"Project not initialized: {root}; run init first")
    return str(json_load(profile)["project_id"])


def init_cmd(args):
    root = Path(args.project).resolve()
    pid = args.project_id or root.name
    if not re.fullmatch(r"[a-zA-Z0-9_.-]{1,128}", pid):
        raise ValueError("project-id must contain letters/digits/dot/underscore/hyphen")
    root.mkdir(parents=True, exist_ok=True)
    for name in ["PROJECT_PROFILE.md", "STORY_BIBLE.md", "STYLE_MEMORY.json", "CONTINUITY_LEDGER.json", "CHAPTER_INDEX.json", "AUTHOR_FEEDBACK.jsonl"]:
        target = root / name
        if target.exists():
            continue
        content = (TEMPLATES / name).read_text(encoding="utf-8").replace("REPLACE_WITH_PROJECT_ID", pid)
        if name.endswith(".json"):
            obj = json.loads(content)
            obj["project_id"] = pid
            json_save(target, obj)
        else:
            write_atomic(target, content)
    (root / "chapters").mkdir(exist_ok=True)
    (root / "qc_reports").mkdir(exist_ok=True)
    (root / ".history").mkdir(exist_ok=True)
    print(json.dumps({"ok": True, "project_id": pid, "root": str(root)}, ensure_ascii=False))


def register_cmd(args):
    root = Path(args.project).resolve()
    ensure_project(root)
    source = Path(args.file).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    n = args.chapter
    if n < 1:
        raise ValueError("chapter must be >=1")
    dest = root / "chapters" / f"CH{n:03d}.md"
    index_path = root / "CHAPTER_INDEX.json"
    index = json_load(index_path)
    entries = index.setdefault("chapters", [])
    existing = next((x for x in entries if x["chapter_id"] == n), None)
    if existing and not args.replace:
        raise ValueError("Chapter already registered. Use --replace to replace with a new draft and invalidate prior QC.")
    if dest.exists() and not args.replace:
        raise ValueError(f"Chapter file exists: {dest}")
    data = source.read_text(encoding="utf-8")
    if args.replace:
        backup(dest, root)
        backup(index_path, root)
    write_atomic(dest, data)
    row = {
        "chapter_id": n,
        "path": str(dest.relative_to(root)),
        "sha256": digest(dest),
        "status": "draft",
        "summary": None,
        "scenes": [],
        "time_markers": [],
        "characters": [],
        "fact_refs": [],
        "open_threads": [],
        "index_ready": False,
        "qc_status": "not_run",
        "last_audit": None,
        "updated_at": now()
    }
    if existing:
        entries[:] = [r if r is not existing else row for r in entries]
        ledger_path = root / "CONTINUITY_LEDGER.json"
        ledger = json_load(ledger_path)
        stale = ledger.setdefault("stale_chapters", [])
        for ch in entries:
            if ch["chapter_id"] >= n:
                ch["qc_status"] = "stale"
                ch["last_audit"] = None
                if ch["chapter_id"] not in stale:
                    stale.append(ch["chapter_id"])
        backup(ledger_path, root)
        ledger["version"] = int(ledger.get("version", 0)) + 1
        ledger["last_updated"] = now()
        json_save(ledger_path, ledger)
    else:
        entries.append(row)
    entries.sort(key=lambda r: r["chapter_id"])
    index["version"] = int(index.get("version", 0)) + 1
    json_save(index_path, index)
    print(json.dumps({"ok": True, "chapter_id": n, "sha256": row["sha256"], "note": "Structural registration only; semantic QC/index extraction still required."}, ensure_ascii=False))


def index_chapter_cmd(args):
    root = Path(args.project).resolve()
    ensure_project(root)
    details = json_load(Path(args.file))
    n = args.chapter
    idx_path = root / "CHAPTER_INDEX.json"
    index = json_load(idx_path)
    entry = next((x for x in index.get("chapters", []) if x["chapter_id"] == n), None)
    if entry is None:
        raise ValueError("register chapter first")
    if digest(root / entry["path"]) != entry["sha256"]:
        raise ValueError("chapter hash changed; re-register chapter with --replace")
    if not details.get("summary") or not isinstance(details.get("scenes"), list):
        raise ValueError("index JSON must contain nonempty summary and scenes list")
    for key in ("summary", "scenes", "time_markers", "characters", "fact_refs", "open_threads"):
        if key in details:
            entry[key] = details[key]
    entry["index_ready"] = True
    entry["updated_at"] = now()
    backup(idx_path, root)
    index["version"] = int(index.get("version", 0)) + 1
    json_save(idx_path, index)
    print(json.dumps({"ok":True, "chapter":n, "index_ready":True, "note":"Synopsis and facts must come from actually reading the chapter; script does not verify semantic accuracy."}, ensure_ascii=False))


def feedback_cmd(args):
    root = Path(args.project).resolve()
    pid = ensure_project(root)
    event = json_load(Path(args.file))
    if event.get("project_id") not in (None, pid):
        raise ValueError("Feedback belongs to a different project")
    event["project_id"] = pid
    event.setdefault("at", now())
    if not any(x in event for x in ("author_comment", "original", "revised", "rule")):
        raise ValueError("Feedback must include author_comment, original, revised or rule")
    if isinstance(event.get("rule"), dict):
        rule_check = event["rule"]
        if not rule_check.get("id") or not rule_check.get("attribute") or not rule_check.get("preference"):
            raise ValueError("rule needs id, attribute and preference")
    feedback_path = root / "AUTHOR_FEEDBACK.jsonl"
    with feedback_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    if isinstance(event.get("rule"), dict):
        style_path = root / "STYLE_MEMORY.json"
        style = json_load(style_path)
        rule = event["rule"].copy()
        if not rule.get("id") or not rule.get("attribute") or not rule.get("preference"):
            raise ValueError("rule needs id, attribute and preference")
        # A model's inference MUST remain candidate; explicit author preference can be confirmed.
        confirmed = event.get("source") in ("explicit_author_instruction", "author_approved_rule", "author_approved_edit")
        rule["status"] = "confirmed" if confirmed else "candidate"
        rule["source"] = event.get("source", "inferred")
        rule["updated_at"] = now()
        for col in ("confirmed_rules", "candidates"):
            style[col] = [x for x in style.get(col, []) if x.get("id") != rule["id"]]
        style["confirmed_rules" if confirmed else "candidates"].append(rule)
        style["version"] = int(style.get("version", 0)) + 1
        style["last_updated"] = now()
        backup(style_path, root)
        json_save(style_path, style)
    print(json.dumps({"ok": True, "feedback_saved": True, "style_rule_saved": isinstance(event.get("rule"), dict), "project_id": pid}, ensure_ascii=False))


def preflight_cmd(args):
    root = Path(args.project).resolve()
    pid = ensure_project(root)
    idx = json_load(root / "CHAPTER_INDEX.json")
    rows = {x["chapter_id"]: x for x in idx.get("chapters", [])}
    through = args.through or max(rows.keys(), default=0)
    missing, drift, not_indexed, not_approved = [], [], [], []
    for n in range(1, through+1):
        row = rows.get(n)
        if row is None:
            missing.append(n)
            continue
        path = root / row["path"]
        if not path.exists():
            missing.append(n)
            continue
        hash_now = digest(path)
        if hash_now != row.get("sha256"):
            drift.append(n)
        if not row.get("index_ready"):
            not_indexed.append(n)
        if row.get("status") != "approved":
            not_approved.append(n)
    result = {
        "project_id": pid, "through": through,
        "covered_chapters": [n for n in range(1,through+1) if n not in missing],
        "missing_chapters": missing, "hash_mismatch": drift,
        "unindexed_chapters": not_indexed,
        "not_approved_chapters": not_approved,
        "ready_for_semantic_full_history_audit": not missing and not drift and not not_indexed,
        "note": "Only validates file/hash/index presence. Does NOT detect logic or continuity issues. Draft chapter N need not be approved prior to QC."
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.strict and (missing or drift or not_indexed):
        sys.exit(2)


def audit_cmd(args):
    root = Path(args.project).resolve()
    ensure_project(root)
    data = json_load(Path(args.meta))
    n = int(data.get("chapter_id", 0))
    covered = sorted(set(int(x) for x in data.get("covered_chapters", [])))
    if n <= 0:
        raise ValueError("meta must include chapter_id")
    if data.get("coverage") not in ("FULL_TEXT", "HYBRID_100_PERCENT_INDEX", "PARTIAL"):
        raise ValueError("meta.coverage invalid")
    if data.get("coverage") != "PARTIAL" and covered != list(range(1,n+1)):
        raise ValueError("FULL_TEXT/HYBRID claims require covered_chapters exactly 1..N")
    if data.get("coverage") == "FULL_TEXT" and sorted(set(data.get("raw_read_chapters", []))) != list(range(1,n+1)):
        raise ValueError("FULL_TEXT requires raw_read_chapters exactly 1..N")
    if data.get("result") not in ("PASS","NEEDS_REVISION","BLOCKED","INCOMPLETE"):
        raise ValueError("meta.result invalid")
    idxpath=root/"CHAPTER_INDEX.json"
    idx=json_load(idxpath)
    row=next((r for r in idx.get("chapters",[]) if r["chapter_id"]==n),None)
    if row is None:
        raise ValueError("chapter must be registered first")
    if data["coverage"] != "PARTIAL":
        lookup = {r["chapter_id"]:r for r in idx.get("chapters",[])}
        for chapter_no in range(1,n+1):
            candidate = lookup.get(chapter_no)
            if candidate is None or not candidate.get("index_ready"):
                raise ValueError(f"chapter {chapter_no} lacks chapter index: cannot claim 100% coverage")
            path_i = root / candidate["path"]
            if not path_i.is_file() or digest(path_i) != candidate["sha256"]:
                raise ValueError(f"chapter {chapter_no} file/hash mismatch")
    chapter_file = root / row["path"]
    if not chapter_file.is_file() or digest(chapter_file) != row["sha256"]:
        raise ValueError("chapter text missing or changed since registration")
    reportfile=Path(args.report).resolve()
    if not reportfile.is_file():
        raise FileNotFoundError(reportfile)
    report_dest=root/"qc_reports"/f"CH{n:03d}_QC.md"
    backup(report_dest,root)
    backup(idxpath,root)
    write_atomic(report_dest, reportfile.read_text(encoding="utf-8"))
    row["qc_status"] = data["result"]
    row["last_audit"] = {**data,"recorded_at":now(),"chapter_hash":row["sha256"]}
    if data["result"] == "PASS" and data["coverage"] != "PARTIAL":
        row["status"] = "reviewed"
    idx["last_cumulative_audit"]={"through":n,"result":data["result"],"coverage":data["coverage"],"at":now()}
    idx["version"] = int(idx.get("version",0))+1
    json_save(idxpath,idx)
    print(json.dumps({"ok":True,"qc_status":row["qc_status"],"coverage":data["coverage"],"report":str(report_dest)},ensure_ascii=False))


def approve_cmd(args):
    root = Path(args.project).resolve()
    ensure_project(root)
    path=root/"CHAPTER_INDEX.json"
    idx=json_load(path)
    n=args.chapter
    row=next((r for r in idx.get("chapters",[]) if r["chapter_id"]==n),None)
    if row is None:
        raise ValueError("chapter missing")
    if row["qc_status"] != "PASS" or not row.get("last_audit") or row["last_audit"]["coverage"] == "PARTIAL":
        raise ValueError("chapter cannot be approved: need a non-partial PASS audit")
    if digest(root / row["path"]) != row["sha256"]:
        raise ValueError("chapter file changed since last audit")
    if row["last_audit"].get("chapter_hash") != row["sha256"]:
        raise ValueError("last audit does not match current chapter hash")
    backup(path,root)
    row["status"]="approved"
    row["approved_at"]=now()
    idx["latest_approved_chapter"]=max(int(idx.get("latest_approved_chapter",0)),n)
    idx["version"]=int(idx.get("version",0))+1
    json_save(path,idx)
    print(json.dumps({"ok":True,"chapter":n,"status":"approved","warning":"Only approves chapter snapshot; canon facts must be explicitly committed to ledger by a capable agent after author approval."},ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("init",help="initialize persistent per-story files without overwriting existing state")
    p.add_argument("--project",required=True)
    p.add_argument("--project-id")
    p.set_defaults(func=init_cmd)
    p=sub.add_parser("register-chapter",help="save a chapter draft and invalidate old audits if replacing")
    p.add_argument("--project",required=True)
    p.add_argument("--chapter",type=int,required=True)
    p.add_argument("--file",required=True)
    p.add_argument("--replace",action="store_true")
    p.set_defaults(func=register_cmd)
    p=sub.add_parser("index-chapter",help="store LLM-generated chapter summary/scenes after actual chapter reading")
    p.add_argument("--project",required=True)
    p.add_argument("--chapter",type=int,required=True)
    p.add_argument("--file",required=True,help="JSON with summary and scenes, optionally timeline/facts")
    p.set_defaults(func=index_chapter_cmd)
    p=sub.add_parser("feedback",help="append author feedback and optionally save rule with approval provenance")
    p.add_argument("--project",required=True)
    p.add_argument("--file",required=True,help="UTF-8 JSON event")
    p.set_defaults(func=feedback_cmd)
    p=sub.add_parser("preflight",help="check chapters 1..N present/hash/index_ready; NOT semantic QC")
    p.add_argument("--project",required=True)
    p.add_argument("--through",type=int)
    p.add_argument("--strict",action="store_true")
    p.set_defaults(func=preflight_cmd)
    p=sub.add_parser("record-audit",help="store semantic QC report generated by LLM; validate coverage claims")
    p.add_argument("--project",required=True)
    p.add_argument("--meta",required=True,help="JSON meta with chapter_id, coverage, result, covered_chapters, raw_read_chapters")
    p.add_argument("--report",required=True)
    p.set_defaults(func=audit_cmd)
    p=sub.add_parser("approve-chapter",help="mark PASS audited chapter approved, with hash match")
    p.add_argument("--project",required=True)
    p.add_argument("--chapter",type=int,required=True)
    p.set_defaults(func=approve_cmd)
    args=parser.parse_args()
    try:
        args.func(args)
    except (OSError,KeyError,ValueError,json.JSONDecodeError) as exc:
        print(json.dumps({"ok":False,"error":str(exc)},ensure_ascii=False),file=sys.stderr)
        sys.exit(1)


if __name__=="__main__":
    main()
