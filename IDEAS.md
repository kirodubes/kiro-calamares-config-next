# IDEAS — kiro-calamares-config-next

> Experimental and future ideas for the Kiro Calamares installer config.

## Claude's Ideashop

**2026-05-19 — Automated promotion diff report**
Before mirroring -next → production, generate a markdown summary of every file that differs and why (kernel-specific vs kernel-agnostic, package-name refs, cosmetic). Output it as a `PROMOTION_NOTES.md` in the -next repo root, commit it, then delete it after the production commit. This gives a paper trail of every promotion decision without cluttering the CHANGELOG, and makes the grep-for-stale-refs step part of a reproducible checklist rather than a manual memory task.
