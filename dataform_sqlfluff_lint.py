import argparse
import json
import os
import shutil
import subprocess
import sys
import sqlfluff


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-dir",
        default=".",
        help="dataform repository root path",
    )
    parser.add_argument(
        "--workflow-settings",
        help="path to workflow_settings.yaml file",
    )
    parser.add_argument(
        "--config-path",
        help="path to .sqlfluff file",
    )
    parser.add_argument(
        "target_files",
        nargs="+",
        help="target files to show queries for",
    )
    args = parser.parse_args()

    project_dir = args.project_dir
    workflow_settings = args.workflow_settings
    config_path = args.config_path
    target_files = args.target_files

    copied_file = None

    sqlfluff_config = {
        "dialect": "bigquery",
        "exclude_rules": [
            "LT01", "LT02", "LT03", "LT04", "LT05", "LT06", "LT07", "LT08", "LT09", "LT10",
            "LT11", "LT12", "LT13", "LT14", "LT15", "CV03" 
        ],
    }
    if config_path:
        sqlfluff_config = {
            "config_path": config_path
        }

    workflow_settings_path = os.path.join(project_dir, "workflow_settings.yaml")
    if not os.path.exists(workflow_settings_path):
        if workflow_settings:
            shutil.copy(workflow_settings, workflow_settings_path)
            copied_file = workflow_settings_path
        else:
            print(
                f"Error: workflow_settings.yaml not found in {project_dir} and --workflow-settings not specified"
            )
            sys.exit(1)

    result = subprocess.run(
        ["npx", "-y", "@dataform/cli@^3.0.0", "compile", "--json", project_dir],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        if copied_file:
            os.remove(copied_file)
        sys.exit(result.returncode)

    try:
        compiled_graph = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON output: {e}", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        if copied_file:
            os.remove(copied_file)
        sys.exit(1)

    filename_map = {
        e.get("fileName"): e
        for e in [
            *compiled_graph.get("operations", []),
            *compiled_graph.get("tables", []),
        ]
        if "fileName" in e
    }

    violations = []
    for target_file in target_files:
        if project_dir != ".":
            if not target_file.startswith(project_dir):
                continue
            e = filename_map.get(target_file[len(project_dir)+1:])
        else:
            e = filename_map.get(target_file)
        if not e:
            continue
        query_map = {
            "queries": [
                *([e.get("query")] if "query" in e else []),
                *e.get("queries", [])
            ],
            "preOps": e.get("preOps", []),
            "postOps": e.get("postOps", []),
        }
        violations.extend([
            {
                "target_file": target_file,
                "ops": ops,
                "idx": idx,
                **result
            }
            for ops, queries in query_map.items()
            for idx, sql in enumerate(queries)
            for result in sqlfluff.lint(sql, **sqlfluff_config)
        ])

    if copied_file:
        os.remove(copied_file)

    if violations:
        for e in violations:
            ops = f'#{e["ops"]}' if e["ops"] != "queries" else ""
            print(f'{e["target_file"]}{ops}${e["idx"]+1}:{e["start_line_no"]}:{e["start_line_pos"]} {e["code"]} {e["description"]}')
        sys.exit(1)


if __name__ == "__main__":
    main()
