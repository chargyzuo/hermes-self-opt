---
name: cli-subcommand-handler-fix
description: "Detect and fix missing handler branches in CLI subcommand dispatch functions"
version: 1.0.0
author: AI Self-Evolution Analyzer
platforms: [linux, macos, windows]
---

# CLI Subcommand Handler Fix

## Steps

1. **Identify the symptom**  
   - User reports that a subcommand (e.g., `gap`, `rewrite`, `rollback`) shows usage help instead of executing. This indicates the subcommand is registered in argparse but not handled in the dispatch function.

2. **Locate the argparse registration**  
   - Find where `subparsers.add_parser('subcommand_name')` is called (typically in `add_arguments()` or similar). Note the function name that should be called (e.g., `hermes_self_opt.router.gap`).

3. **Find the dispatch function**  
   - Look for a function like `_handle_router()` or `_handle_<command>()` that maps parsed command names to actual implementations. It usually has a series of `if/elif` blocks checking `args.subcommand`.

4. **Add missing branch**  
   - Insert a new `elif args.subcommand == 'missing_name':` block that calls the appropriate function with the same argument pattern as other branches.

5. **Verify existing functionality**  
   - Run other subcommands (`query`, `stats`, `build`) to ensure they still work after the change.

6. **Create a temporary verification script**  
   - Import the CLI module, simulate parsing each subcommand, and assert that the dispatch function returns the expected exit code or calls the expected function (use mocking if needed). Clean up the script after verification.

7. **Final smoke test**  
   - Execute the fixed subcommand and confirm it produces the expected output (e.g., gap analysis report).

## Example

For a bug where `gap`, `rewrite`, `rollback` were missing from `_handle_router()` in `hermes_self_opt/cli.py`:

- Add: `elif args.subcommand == 'gap':` → call `hermes_self_opt.router.gap(args)`  
- Add: `elif args.subcommand == 'rewrite':` → call `hermes_self_opt.router.rewrite(args)`  
- Add: `elif args.subcommand == 'rollback':` → call `hermes_self_opt.router.rollback(args)`

## Verification

After applying the fix, all previously failing subcommands should execute without error and produce valid output.