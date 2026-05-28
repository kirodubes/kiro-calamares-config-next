# TODO — kiro-calamares-config-next

> Beta/testing Calamares installer config — paired with `kiro-iso-next`.

## Active

- [ ] **Validate `chwd` Calamares module on a real install** — _added 2026-05-28._ After `kiro-iso-next` rebuilds with the new package, boot in a VM and run a full install. Check `/var/log/Calamares.log` for `chwd:` debug lines. Confirm both branches: `driver=free` skips the module (kiro_remove_nvidia keeps owning that path); `driver=nonfree` runs `chwd --autoconfigure` and ends up with the right driver bundle installed in the target. Verify `chwd` survives `kiro_final`'s removal pass — it should, since chwd is in `[nemesis_repo]` and not in `kiro_final`'s removal list.
- [ ] **Consider folding `kiro_remove_nvidia` into `chwd`** — _added 2026-05-28._ Long-term cleanup once chwd is fully trusted. chwd's nouveau profile (priority 18) handles the `driver=free` path natively; a single module is simpler than two complementary ones. Risk: kiro_remove_nvidia is well-tested, chwd's exact selection algorithm for `driver=free` needs verification. Defer until after a couple of release cycles of both running side-by-side.

## Done

- [x] Test full install run with Liquorix kernel (`linux-lqx`) from `unpackfs2.conf`
- [x] Mirror validated changes to `kiro-calamares-config` (production) — 2026-05-19
