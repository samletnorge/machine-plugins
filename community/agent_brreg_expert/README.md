# agent_brreg_expert

## TODO

1. Convert ingest to a job model for more robust long-running operation handling.

- Request starts a job
- Job gets an id
- Worker runs outside the request lifecycle
- Shutdown can explicitly cancel/reap workers
- Frontends poll status

This is the clean long-term answer for bulk ingest, but it is a larger refactor and not required for the current path.
