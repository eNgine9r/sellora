# Render repository recovery

This operational recovery addresses Render clone failures where `sellora-api-staging` cannot clone `eNgine9r/sellora` and returns HTTP 403.

The workflow `.github/workflows/render-recovery.yml`:

1. Uses the existing `RENDER_API_KEY` GitHub Actions secret.
2. Resolves the existing `sellora-api-staging` service through the Render API.
3. Rebinds the service source to the public repository `https://github.com/eNgine9r/sellora.git` on branch `main` with root directory `backend`.
4. Preserves all service environment variables and secrets.
5. Triggers a deployment of the exact current `main` commit.
6. Waits for the deployment to become live.
7. Verifies `/health` and the exact `runtime_commit`.

The workflow does not create a second Render service, change database settings, or replace environment variables.
