---
name: cli-command-not-found-diagnosis
description: "Diagnose a missing CLI command and find alternative execution method."
version: 1.0.0
author: AI Agent Self-Evolution
---
# CLI Command Not Found Diagnosis

When a user requests a CLI command that doesn't exist in the installed version, follow these steps:

## Steps
1. **Check built-in commands**: Run `[command] --help` or list installed commands. If not found, proceed.
2. **Check cron/references**: Look for scheduled tasks, config files, or documentation that reference the missing command.
3. **Check plugin discovery**: Investigate whether the command is registered dynamically via plugins or extensions.
4. **Identify actual implementation**: Locate the standalone script or alternative entry point (e.g., Python script, shell script) that provides the functionality.
5. **Execute directly**: Run the identified script with appropriate arguments.

## Example
- **Missing**: `hermes self-opt`
- **Found**: `run_self_opt_cron.py` (independent package)
- **Action**: Execute `python run_self_opt_cron.py` with required parameters.