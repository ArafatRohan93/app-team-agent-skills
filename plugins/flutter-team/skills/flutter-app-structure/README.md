# flutter-app-structure (agent skill)

This skill lets a coding agent do two things:

- Turn an empty `flutter create` project into the team's production app shell.
- Keep existing apps on the same conventions.

It follows the open [Agent Skills](https://agentskills.io) format: a `SKILL.md` with `name`/`description` frontmatter, plus `references/`, `scripts/` and `assets/`. Nothing in it depends on a particular agent.

## Layout

```
SKILL.md                    # entry point: bootstrap vs. existing-app workflows, non-negotiables
references/                 # architecture, bootstrap, feature layers, testing, abstractions/*.md
scripts/bootstrap_app.py    # empty project → shell (flavors, l10n, deps, DI, theme, tests, CI, README)
scripts/ios_flavors.rb      # Xcode build configurations per flavor (needs the xcodeproj gem)
scripts/scaffold_feature.py # new feature: data/domain/presentation + DI module + tests
assets/shell/               # real, compiling source copied into new apps (source of truth)
```

## Installing

Keep one copy of the skill, ideally in a team git repo, and link it into each agent's skills directory:

| Agent | Location |
|---|---|
| Claude Code | `~/.claude/skills/flutter-app-structure` (personal) or `<repo>/.claude/skills/flutter-app-structure` (project) |
| OpenAI Codex CLI | `~/.codex/skills/flutter-app-structure` |
| Gemini CLI, Cursor, GitHub Copilot, others with skill support | the agent's skills directory (often `.agents/skills/`), per its docs |
| Agents without skill support | tell the agent: "Read `<path>/flutter-app-structure/SKILL.md` and follow it", or reference it from `AGENTS.md` |

```bash
ln -s /path/to/team-skills/flutter-app-structure ~/.claude/skills/flutter-app-structure
ln -s /path/to/team-skills/flutter-app-structure ~/.codex/skills/flutter-app-structure
```

## Requirements

- `python3`
- Flutter, or fvm with a `.fvmrc`. This is detected automatically.
- iOS flavors: macOS, `ruby` and the `xcodeproj` gem (installed with CocoaPods).

## Verifying changes to the skill

After editing `assets/shell/` or the scripts, check the result on a fresh project:

```bash
flutter create --org com.acme --project-name demo_app --platforms android,ios /tmp/demo_app
python3 scripts/bootstrap_app.py --root /tmp/demo_app --app-name "Demo App"
(cd /tmp/demo_app && scripts/local_ci.sh)
```

The last run of this produced 55 passing tests, 96% coverage, and Android and iOS builds for each flavor with distinct bundle ids and app names.
