import subprocess
import time
import urllib.request
import os
import argparse
import json
import shutil
import sys
from google.api_core import client_options
from google.auth.credentials import AnonymousCredentials
from google.cloud import bigquery

bigquery_emulator_bin = os.environ.get("BIGQUERY_EMULATOR_BIN", "bigquery-emulator")
dataform_project = os.environ.get("DATAFORM_PROJECT", "test")


class BigQueryEmulatorService:
    def __init__(self, project="test", port=9050):
        self.project = project
        self.port = port
        self.endpoint = f"http://localhost:{port}"
        self._process = None

    def up(self):
        self._process = subprocess.Popen(
            [
                bigquery_emulator_bin,
                "--project",
                self.project,
                "--port",
                str(self.port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def down(self):
        if self._process:
            self._process.terminate()
            self._process.wait()

    def is_healthy(self):
        try:
            resp = urllib.request.urlopen(
                f"{self.endpoint}/discovery/v1/apis/bigquery/v2/rest"
            )
            return resp.status == 200
        except Exception:
            return False

    def wait_for_healthy(self, retries=10, interval=1):
        for _ in range(retries):
            if self.is_healthy():
                return
            time.sleep(interval)
        raise RuntimeError("BigQuery emulator failed to start")


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
        "target_files",
        nargs="+",
        help="target files to show queries for",
    )
    args = parser.parse_args()

    project_dir = args.project_dir
    workflow_settings = args.workflow_settings
    target_files = args.target_files

    copied_file = None

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

    # start emulator
    bq_svc = BigQueryEmulatorService(project=dataform_project)
    bq_svc.up()
    bq_svc.wait_for_healthy()
    options = client_options.ClientOptions(
        api_endpoint=bq_svc.endpoint,
    )
    creds = AnonymousCredentials()
    bq_client = bigquery.Client(
        project=dataform_project,
        credentials=creds,
        client_options=options,
    )

    def check_syntax(q):
        query_job = bq_client.query(
            q, job_config=bigquery.QueryJobConfig(dry_run=True, use_legacy_sql=False)
        )
        error_message = query_job.errors[0]["message"] if query_job.errors else None
        if error_message is None:
            return []
        ignore_errors = [
            "not supported",
            "Table not found",
        ]
        is_parse_error = True
        for ignore_error in ignore_errors:
            if ignore_error in error_message:
                is_parse_error = False
        if is_parse_error:
            return [error_message]

    violations = []
    for target_file in target_files:
        if project_dir != ".":
            if not target_file.startswith(project_dir):
                continue
            e = filename_map.get(target_file[len(project_dir) + 1 :])
        else:
            e = filename_map.get(target_file)
        if not e:
            continue
        query_map = {
            "queries": [
                *([e.get("query")] if "query" in e else []),
                *e.get("queries", []),
            ],
            "preOps": e.get("preOps", []),
            "postOps": e.get("postOps", []),
        }
        violations.extend(
            [
                {
                    "target_file": target_file,
                    "ops": ops,
                    "idx": idx,
                    "result": result,
                }
                for ops, queries in query_map.items()
                for idx, sql in enumerate(queries)
                for result in check_syntax(sql)
            ]
        )

    # stop emulator
    bq_client.close()
    bq_svc.down()

    if copied_file:
        os.remove(copied_file)

    if violations:
        for e in violations:
            ops = f"#{e['ops']}" if e["ops"] != "queries" else ""
            print(f"{e['target_file']}{ops}${e['idx'] + 1}: {e['result']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
