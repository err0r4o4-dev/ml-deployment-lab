# ML Deployment Lab

- [x] Inspect assignment, instructions, Git status, and local tools.
- [x] Resolve Python 3.11 packages in a project-local environment.
- [x] Check failures before implementing model training, API, and form.
- [x] Build Flask service, real model, HTML form, and Dockerfile.
- [x] Verify API, errors, browser behavior, mobile layout, screenshot.
- [x] Verify Docker build/run, Linux tests, HTTP API, and browser against container.
- [x] Update README with commands and actual evidence; review diff.
- [x] Stop task-owned processes and verify artifact exclusions.

Scope: README assignment only. Main implements directly. Medium size/risk.
Dependencies: authorized public package/dataset downloads.
No Docker installation, commit, push, publication, or reviewer dispatch.
Preserve feature order and USD 100,000 output unit.
Reject malformed JSON, invalid counts, booleans, and non-finite numbers.
Keep generated models, data, environments, and secrets out of Git/Docker.
Recovery: preserve original README and Git history; remove only task outputs.
Docker CLI is outside the terminal PATH; per-user Docker Desktop was found and verified.

## Current evidence (2026-11-16)

- RED: 17 checks failed before app.py/train_model.py existed.
- GREEN: python -W error -m unittest discover -s tests -v: 17 passed.
- Regression: NumPy float32 comparison overflow reproduced with -W error;
  convert the comparison limit to a Python float; invalid-input check passed.
- Browser: real prediction 4.029472199999998, USD 402,947. Screenshots in docs/.
- R2: 0.8046244867176197. RMSE: 0.5059859946022769. MAE: 0.32773108008720936.
- Node syntax check and Python compileall passed. Git diff --check passed.
- Linux/Python 3.11 dependency dry-run resolved 18 packages including Gunicorn.
- Browser no-JavaScript reset expectation corrected to native HTML behavior:
  reset restores the values rendered by the most recent server response.
- Previous Docker runtime blocker resolved by the fresh verification below.
- No independent agent review performed. No commit, push, deployment, or form submission.
- Main reviewed source, input handling, Docker copy boundaries, and README.
- Original assignment preserved in docs/assignment.md and compared with HEAD.
- Browser/server closed by the verifier. Generated models/data/cache are Git-ignored.
- GitHub push and Google Form submission still require separate authorization.

## Docker verification (2026-11-16)

- PASS: Docker CLI/Engine 29.9.2, Docker Desktop 4.97.0, Linux/amd64 daemon.
- PASS: docker build --progress=plain -t ds-ml-service:lab-verify-20261116 .
- Image: sha256:c7b755ad2a40939996bf8ca161012559b351289eac36f04d5b903022d87a6a17.
- PASS: training inside build reproduced the recorded model metrics.
- PASS: Gunicorn 2 workers; runtime appuser UID/GID 1000; loopback port 57079.
- PASS: 17 unittest checks in 12.001 seconds inside a network-disabled container,
  with project tests mounted read-only. python -m pip check passed.
- PASS: real HTTP health/prediction, 11 invalid JSON payloads, HTTP 400/405/413,
  HTML/static assets, and 8 parallel predictions. Prediction: 4.029472199999998.
- PASS: headless Edge against container, real prediction/USD conversion,
  viewport widths 320/768/1024/1440, keyboard focus, Reset, missing inputs,
  injected network failure followed by real retry, and no-JavaScript form POST.
- PASS: no JavaScript runtime errors. Screenshots: .cache/docker-verification/.
- PASS: both task-owned containers stopped and removed; built image retained.
- No application/Dockerfile changes, installation, independent review, commit,
  push, deployment, or Google Form submission performed in this verification.
