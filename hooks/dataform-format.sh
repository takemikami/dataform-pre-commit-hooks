#!/bin/bash

PROJECT_DIR="."
WORKFLOW_SETTINGS=""
COPIED=false
TARGET_FILES=()

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
      TARGET_FILES+=("$1")
      shift
      ;;
  esac
done

if [[ -n "$WORKFLOW_SETTINGS" ]] && [[ ! -f "$PROJECT_DIR/workflow_settings.yaml" ]]; then
  cp "$WORKFLOW_SETTINGS" "$PROJECT_DIR/workflow_settings.yaml"
  COPIED=true
fi

PROCESSED_FILES=()
for file in "${TARGET_FILES[@]}"; do
  if [[ "$PROJECT_DIR" != "." ]]; then
    if [[ "$file" == "$PROJECT_DIR"* ]]; then
      file="${file#$PROJECT_DIR}"
    fi
    if [[ "$file" == /* ]]; then
      file="${file#/}"
    fi
  fi
  PROCESSED_FILES+=("--actions")
  PROCESSED_FILES+=("$file")
done

npx -y @dataform/cli@^3.0.0 format "$PROJECT_DIR" "${PROCESSED_FILES[@]}"
EXIT_CODE=$?

if [[ "$COPIED" == true ]]; then
  rm "$PROJECT_DIR/workflow_settings.yaml"
fi

exit $EXIT_CODE
