#!/bin/bash

PROJECT_DIR="."
WORKFLOW_SETTINGS=""
COPIED=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --project-dir)
      PROJECT_DIR="$2"
      shift 2
      ;;
    --workflow-settings)
      WORKFLOW_SETTINGS="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

if [[ -n "$WORKFLOW_SETTINGS" ]] && [[ ! -f "$PROJECT_DIR/workflow_settings.yaml" ]]; then
  cp "$WORKFLOW_SETTINGS" "$PROJECT_DIR/workflow_settings.yaml"
  COPIED=true
fi

npx -y @dataform/cli@^3.0.0 compile "$PROJECT_DIR"
EXIT_CODE=$?

if [[ "$COPIED" == true ]]; then
  rm "$PROJECT_DIR/workflow_settings.yaml"
fi

exit $EXIT_CODE