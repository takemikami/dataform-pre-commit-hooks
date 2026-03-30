dataform-pre-commit-hooks
---

pre-commit hooks for Dataform.

## Using dataform-pre-commit-hooks

Add this to your .pre-commit-config.yaml

```yaml
repos:
- repo: https://github.com/takemikami/dataform-pre-commit-hooks.git
  rev: v0.0.5
  hooks:
    - id: dataform-compile
    - id: dataform-format
    - id: dataform-sqlfluff-lint
    - id: dataform-syntax-check
```

## Hooks available

### dataform-compile

Check whether files can be compiled.

- `--project-dir` - Specify dataform project root dir. ex: `['--project-dir', 'project1']`

### dataform-format

Format files with dataform format command.

- `--project-dir` - Specify dataform project root dir. ex: `['--project-dir', 'project1']`

### dataform-sqlfluff-lint

Lint SQLs with sqlfluff lint command.

- `--project-dir` - Specify dataform project root dir. ex: `['--project-dir', 'project1']`
- `--config-path` - Specify sqlfluff config file path. ex: `['--project-path', '.sqlfluff']`

### dataform-syntax-check

Check SQLs syntax with bigquery-emulator. [bigquery-emulator](https://github.com/goccy/bigquery-emulator) required.

- `--project-dir` - Specify dataform project root dir. ex: `['--project-dir', 'project1']`
