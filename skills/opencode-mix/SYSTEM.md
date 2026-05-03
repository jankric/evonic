# OpenCode Mix Skill

This skill lets you delegate coding tasks to the `opencode-mix` agent running on the server.

## Available Tools

### `ocm_run` — One-shot coding task
Use this for focused, well-defined coding tasks. The agent will execute the task and return the result.

```
ocm_run(task="<describe what to do>", workdir="<absolute path>")
```

Parameters:
- `task` (required): Clear description of what to code/build/fix
- `workdir` (required): Absolute path to the project directory
- `model` (optional): Model override, defaults to `cli-claude/claude-sonnet-4-6`
- `variant` (optional): `high`, `max`, or `minimal`

### `ocm_session_start` — Start interactive session
Use for complex multi-step tasks. Returns a `session_id`.

```
ocm_session_start(workdir="<path>", initial_message="<first task>")
```

### `ocm_session_send` — Send to active session
Continue work in an existing session.

```
ocm_session_send(session_id="ses_xxx", prompt="<next task>")
```

### `ocm_session_list` — List active sessions
```
ocm_session_list()
```

### `ocm_session_stop` — Stop a session
```
ocm_session_stop(session_id="ses_xxx")
```

## Usage Guidelines

- Always use `ocm_run` for single coding tasks
- Use `ocm_session_start` + `ocm_session_send` for iterative work
- Always provide an absolute `workdir` path
- Check the `success` field in the response to verify completion
- The `output` field contains the result from opencode-mix
