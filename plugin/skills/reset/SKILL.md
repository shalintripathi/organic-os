---
name: reset
description: Use when the user wants to remove a site from organic-os, deregister a site, uninstall, "reset organic-os", "remove my site", "start over", or runs /organic-os:reset. Guided teardown that shows what exists and, per user choice, deregisters the site from the local registry - it never deletes the brain repo or revokes credentials on the user's behalf.
---

# organic-os reset (guided teardown)

organic-os never deletes anything irreversible automatically. This skill
walks the user through everything that exists for a site and what to do
about each piece, then only touches the local registry with explicit
confirmation.

## Step 1: show what exists

1. Read `~/.config/organic-os/sites.yaml` via `core.registry.load()`: list
   every registered site (slug, name, url, brain path) and which one is
   active.
2. List files in `~/.config/organic-os/` - the per-site env files
   (`<slug>.env`, holding `WP_APP_PASSWORD` / `TELEGRAM_BOT_TOKEN`) and the
   registry file itself.
3. For the site the user is asking about: report whether its brain path
   exists on disk and whether it is a git repo (has a remote or not).

## Step 2: ask which site to tear down

AskUserQuestion: which registered site (or "all"). Confirm before any write.

## Step 3: walk through each piece, per site

Only item 2 below is something this skill performs, and only with explicit
confirmation. Everything else is the user's own action - state why for each.

1. **Scheduled routines**: point at the runtime's own mechanism. If runtime
   mode is `claude-scheduled`, tell the user to remove the scheduled task from
   their Claude scheduler. If `ci`, tell them to disable/delete the workflow
   file or cron entry in their CI system. organic-os does not manage the
   runtime's own scheduler and cannot deregister a routine for them.
2. **Registry entry**: with explicit confirmation, remove the site from
   `~/.config/organic-os/sites.yaml` by calling `core.registry.unregister(<slug>)`.
   If the removed site was active, tell the user no site is active until
   they register or switch to another one.
3. **Brain repo**: organic-os never deletes it, on this skill's own authority
   or the user's request in this session. It is the site's memory - signals,
   decisions, reflections, skillbook, outcomes - and often has git history the
   user wants to keep or archive. Tell the user the exact path and how to
   remove it themselves: `rm -rf <brain-path>` for the local copy, plus
   deleting the remote repo from GitHub/GitLab settings if it was pushed.
4. **WordPress Application Password**: organic-os cannot revoke it. Tell the
   user: WP Admin > Users > Profile > Application Passwords, revoke the one
   created for organic-os.
5. **Telegram bot token**: if the approval channel was telegram, tell the
   user they can revoke/regenerate it via @BotFather's `/revoke` command if
   they want to fully cut access. Deleting the env file alone stops polling
   but does not invalidate the token.
6. **Env file**: with explicit confirmation, delete
   `~/.config/organic-os/<site-slug>.env`.

## Step 4: summarize

State plainly what was done automatically in this session (registry
deregistration, env file deletion - only if confirmed) versus what the user
must still do by hand (brain repo deletion, WordPress application-password
revocation, Telegram token revocation, scheduler cleanup) and exactly where
to do each.

## Rules

- Uninstalling the plugin itself never deletes any brain repo - brains are
  ordinary git repos or folders that live outside the plugin's install
  location. State this explicitly if asked "does uninstalling delete my
  data".
- Never delete a brain repo under any instruction in this skill - that
  action is reserved for the user, always.
- Never revoke a WordPress application password or a Telegram bot token on
  the user's behalf - point them at the UI where they can do it themselves.
- Never delete or edit the registry, or an env file, without an explicit
  confirmation for that specific site in this session.
