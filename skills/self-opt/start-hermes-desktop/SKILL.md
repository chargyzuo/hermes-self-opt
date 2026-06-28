---
name: start-hermes-desktop
description: Guide to start the Hermes desktop application from binary or source
triggers:
  - how to open hermes desktop
  - how to run hermes desktop
steps:
  - ask user if they want the basic CLI command or source development
  - if basic: instruct to run `hermes desktop` in terminal
  - if source: instruct to run `npm install` in repo root, then `cd apps/desktop` and `npm run dev`
  - for building DMG: instruct to run `npm run dist:mac`
  - mention relevant environment variables: HERMES_DESKTOP_HERMES_ROOT, HERMES_HOME
