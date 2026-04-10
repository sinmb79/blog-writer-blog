# n8n One-Click Setup Design

**Context**

`blog-writer-blog` currently ships Python bots, dashboard code, and automation scripts, but it does not provide a one-command n8n bootstrap flow or importable workflow bundle. The requested outcome is a repo-local setup flow that installs n8n, imports five workflows, starts n8n, and opens the browser at `http://localhost:5678`.

**Decision**

Add cross-platform bootstrap entrypoints at the repository root:

- `setup.sh` for Bash environments
- `setup.bat` for Windows `cmd.exe`

Add a new `n8n-workflows/` directory with five importable workflow JSON files tailored to this repository:

- Daily pipeline
- Write queue
- Publish queue
- Weekly report
- Monthly reminder

Update `README.md` so the primary installation path points to the new one-click setup flow instead of only the manual dashboard startup path.

**Constraints**

- Keep the setup flow honest about prerequisites and missing optional services.
- Do not depend on external workflow files from another repository.
- Use repo-relative paths so the scripts work when cloned anywhere.
- Preserve existing manual setup guidance by keeping the beginner guide link available.

**Validation**

- Add a structure test that fails until the setup scripts and five workflow files exist.
- Also verify that the README mentions the new setup entrypoints and n8n URL.
