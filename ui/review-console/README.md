# Torii Run Console

Ops UI for a full Torii run: **PR · result · findings · diff · trace · agent loop · cost · memory · artifacts**.

Design follows **Impeccable** Operate mode + Neo kinpaku tokens (`PRODUCT.md`, `DESIGN.md`; source `/tmp/impeccable`).

## Run

```bash
# Pack a showcase / .torii-out directory into the fixture
npm run pack-fixture

npm install
npm run dev    # http://localhost:5177
npm run build
```

Load any `run-bundle.json` via **Load bundle** in the UI.

## Pack a run

```bash
python3 scripts/pack-run-for-ui.py \
  --dir docs/showcase/e2e-odoo-pr3-opus5-agentic-loop \
  --host gha \
  --comment-url https://github.com/Mr-Ashish/odoo/pull/3 \
  -o ui/review-console/public/fixtures/run-bundle.json
```
