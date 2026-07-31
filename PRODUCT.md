# Torii Gate — product brief

## One sentence
Torii Gate is a PR/CI security gate that reviews AI-written and human code with agent tools, evidence, and merge protection.

## User
Platform / AppSec engineer who needs every PR checked for security without drowning in SAST noise.

## v1 scope
- GitHub comment trigger `@torii review this pr`
- Security pack default
- Comment + labels (`torii/*`)
- Local `.torii/` memory + FP patterns
- Redacted traces as Actions artifacts

## Non-goals (v1)
- Full ASPM dashboard
- Autonomous offensive red team
- Auto-merge patches without human

## Success metrics
- Time-to-first-signal on PR
- Measured FP rate (memory growth of suppressions)
- PRs blocked with path-evidenced findings
