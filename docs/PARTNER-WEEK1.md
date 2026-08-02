<!-- torii-partner-week1 -->

# Torii Gate — design partner week-1 checklist

_Generated: `2026-08-02T05:28:49Z` · measured local install · **not** a sales deck_

> Path: install free → require **`torii/gate`** → first review → quieter · 1–2 feedback notes.

**Status:** 12/12 · core_ok=`True` · week1_ok=`True` · full=`True`

Partner week-1 12/12 · core_ok=True · week1_ok=True (install → torii/gate → review → feedback)

## Checklist

| Check | Pass | Why it matters |
|-------|:----:|----------------|
| workflow present | yes | Pack can run on PRs |
| mentions `torii/gate` | yes | Required check name exists |
| install docs | yes | 5-minute path documented |
| required-check docs | yes | Branch protection how-to |
| OPENROUTER secret docs | yes | Model key path |
| runs vault seeded | yes | Quieter chart has data |
| quieter surface | yes | Own-repo quieter path |
| doctor or smoke | yes | Day-2 health |
| feedback path docs | yes | What to send us |
| workflow-as-code yaml | yes | Declarative pipeline graph |
| workflow validate CLI | yes | Free offline before model $ |
| organic or demo run | yes | At least one local pack |

## Local vault

- runs: **7** · demo=2 · organic=5
- quieter_ok=True · getting_quieter=True
- doctor_pass=True · install_stamp=False

## Next (this week)

1. Send 1–2 feedback notes (what blocked / cost / quieter) via design-partner issue
2. python3 scripts/torii.py pilot -- readiness · pilot -- packet

## CLI

```bash
python3 scripts/torii.py pilot -- week1
python3 scripts/torii.py pilot -- readiness
python3 scripts/torii.py quieter -- status
python3 scripts/torii.py status --text
```

Apply / feedback: https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml

Docs: [PILOT.md](PILOT.md) · [INSTALL.md](INSTALL.md) · [GTM.md](GTM.md) · [QUIETER.md](QUIETER.md)
