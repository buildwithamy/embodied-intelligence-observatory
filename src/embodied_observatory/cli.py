import argparse
import json
import logging
import tempfile
from datetime import date
from pathlib import Path

from .http import HttpClient
from .pipeline import analyze, clear_cache, collect, publish, report, week_id


def parser():
    cli = argparse.ArgumentParser(description="具身智能观察站：人工采集、解读、草稿与审核发布")
    cli.add_argument("--root", type=Path, default=Path.cwd(), help="项目目录（含 config/ 与 prompts/）")
    cli.add_argument("--log-level", choices=["INFO", "WARNING", "ERROR"], default="INFO")
    sub = cli.add_subparsers(dest="command", required=True)
    for name in ("collect", "analyze", "report", "weekly"):
        command = sub.add_parser(name)
        if name in {"collect", "weekly"}:
            command.add_argument("--start", type=date.fromisoformat, required=True)
            command.add_argument("--end", type=date.fromisoformat, required=True)
            command.add_argument("--supplement", type=Path, help="人工核验的一手来源 Candidate JSON")
        else:
            command.add_argument("--week", required=True)
        if name == 'report':
            command.add_argument('--selection', type=Path, help='V0.4人工选题文件；缺省仅生成旧版待审Markdown草稿')
            command.add_argument('--issue-file', type=Path, help='已完成事实审核的网页编辑稿')
            command.add_argument('--archive', action='store_true')
        command.add_argument("--dry-run", action="store_true", help="输出到临时目录，不改正式产物")
        command.add_argument("--offline", action="store_true", help="仅重放 HTTP 缓存")
        command.add_argument("--refresh", action="store_true", help="重新请求 HTTP 数据")
        if name in {"analyze", "weekly"}:
            command.add_argument("--llm", action="store_true", help="显式启用付费模型 API")
            command.add_argument("--analysis-file", type=Path, help="导入 human_review / codex_review JSON")
            command.add_argument("--skip-research", action="store_true", help="使用已有证据，不再获取正文")
    command = sub.add_parser("publish")
    command.add_argument("--week", required=True)
    command.add_argument("--reviewed", action="store_true", help="确认维护者已阅读并审核草稿")
    sub.add_parser("cache-clear", help="清除当前项目 .cache，不动数据与周报")
    command = sub.add_parser("major-audit", help="导入独立一手来源审计，更新重大事件记忆")
    command.add_argument("--week", required=True)
    command.add_argument("--events", type=Path, nargs="+", required=True)
    command.add_argument("--audits", type=Path, nargs="+", required=True)
    command.add_argument("--dry-run", action="store_true")
    command = sub.add_parser("edition", help="从已核验事件与解读生成网页周刊")
    command.add_argument("--week", required=True)
    command.add_argument("--issue-file", type=Path, required=True)
    command.add_argument("--archive", action="store_true", help="显式写入本地 Markdown 归档，不发布到外网")
    command.add_argument("--dry-run", action="store_true")
    command.add_argument('--selection', type=Path, help='人工闸门，缺省runs/<week>/editorial_selection.yaml')
    command = sub.add_parser('discover', help='最近14天中英开放式新闻发现，不自动视为事实')
    command.add_argument('--start', type=date.fromisoformat, required=True)
    command.add_argument('--end', type=date.fromisoformat, required=True)
    command.add_argument('--week', help='缺省按窗口结束日ISO周命名')
    command.add_argument('--results-file', type=Path, nargs='+', help='导入外部真实搜索记录，可离线重放')
    command.add_argument('--offline', action='store_true')
    command.add_argument('--refresh', action='store_true')
    command.add_argument('--dry-run', action='store_true')
    command = sub.add_parser('audit', help='独立重大新闻评分、遗漏检查、人工选题草案')
    command.add_argument('--week', required=True)
    command.add_argument('--reviews', type=Path, help='基于原文的新闻核验与六维评分JSON')
    command.add_argument('--dry-run', action='store_true')
    command = sub.add_parser('review-selection', help='维护者读完Audit和编辑稿后确认选题；不会生成或发布网页')
    command.add_argument('--week', required=True)
    command.add_argument('--selection', type=Path, required=True)
    command.add_argument('--issue-file', type=Path, required=True)
    command.add_argument('--reviewer', required=True)
    command.add_argument('--reviewed', action='store_true')
    return cli


def main(argv=None):
    args = parser().parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(levelname)s %(message)s")
    root = args.root.resolve()
    try:
        if args.command == "cache-clear":
            clear_cache(root)
            print("cache cleared")
            return 0
        if args.command == "publish":
            print(publish(root, args.week, args.reviewed))
            return 0
        if args.command == 'review-selection':
            from .editorial_gate import approve_selection

            print(json.dumps(approve_selection(root, args.week, args.selection, args.issue_file,
                                               args.reviewer, args.reviewed), ensure_ascii=False, indent=2))
            return 0
        output = Path(tempfile.mkdtemp(prefix="eio-dry-run-")) if args.dry_run else root
        week = (args.week or week_id(args.end)) if args.command == 'discover' else (
            week_id(args.start) if hasattr(args, "start") else args.week)
        if args.command in {'discover', 'audit'}:
            if args.command == 'discover':
                from .discovery import discover

                client = HttpClient(output / '.cache/http', offline=args.offline, refresh=args.refresh,
                                    read_cache=root / '.cache/http', timeout=8)
                result = discover(root, output, args.start, args.end, client=client,
                                  results_files=args.results_file, week=week)
            else:
                from .editorial_gate import audit

                result = audit(root, output, week, reviews_file=args.reviews)
            summary = {key: value for key, value in result.items() if key not in {'queries', 'query_plan'}}
            print(json.dumps({'output': str(output), 'result': summary}, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'report' and args.selection:
            from .edition import build_edition

            issue_file = args.issue_file or root / 'data/editorial' / (week + '-v04.json')
            result = build_edition(root, output, week, issue_file, selection_file=args.selection,
                                   archive=args.archive, dry_run=args.dry_run)
            print(json.dumps({'output': str(output), 'result': result}, ensure_ascii=False, indent=2))
            return 0
        if args.command in {"major-audit", "edition"}:
            if args.command == "major-audit":
                from .major_events import audit_import

                result = audit_import(root, output, week, args.events, args.audits)
            else:
                from .edition import build_edition

                result = build_edition(root, output, week, args.issue_file,
                                       archive=args.archive, dry_run=args.dry_run, selection_file=args.selection)
            print(json.dumps({"output": str(output), "dry_run": args.dry_run,
                              "result": result}, ensure_ascii=False, indent=2))
            return 0
        if args.dry_run and args.command in {"analyze", "report"}:
            import shutil

            for folder in ("runs", "data/candidates"):
                source = root / folder / (week + ".json")
                destination = output / folder / (week + ".json")
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            from .pipeline import load_json, write_json

            manifest_path = output / "runs" / (week + ".json")
            manifest = load_json(manifest_path)
            manifest["dry_run"] = True
            write_json(manifest_path, manifest)
        client = HttpClient(output / ".cache" / "http", refresh=args.refresh, offline=args.offline,
                            read_cache=root / ".cache" / "http")
        if args.command == 'weekly':
            from datetime import timedelta

            from .discovery import discover

            discover(root, output, args.end - timedelta(days=13), args.end, client=client, week=week)
        if args.command in {"collect", "weekly"}:
            result = collect(root, output, args.start, args.end, client, args.supplement, args.dry_run)
        if args.command in {"analyze", "weekly"}:
            result = analyze(root, output, week, client, use_llm=args.llm, reviews=args.analysis_file,
                             research=not args.skip_research)
        if args.command in {"report", "weekly"}:
            result = report(root, output, week)
        print(json.dumps({"week": week, "output": str(output), "dry_run": args.dry_run,
                          "status": result["status"], "raw_items": result["raw_items"],
                          "candidate_items": result["candidate_items"], "selected_items": result["selected_items"]},
                         ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        # Model transport errors sanitized in wrapper; other error types may expose URLs but not keys.
        if isinstance(exc, (ValueError, FileNotFoundError)):
            logging.error("%s", str(exc))
        else:
            logging.error("pipeline failed: %s", type(exc).__name__)
        if 'output' in locals() and args.dry_run:
            logging.error("dry-run diagnostics at %s", output)
        return 2
