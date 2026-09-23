# App Team Agent Skills

Our team's shared skills for AI coding agents: Claude Code, Codex, Cursor, Gemini CLI and others. A skill is a folder of instructions, reference docs and scripts. An agent loads it when a task matches the skill's description. That way every agent follows the same team standards, whoever is driving it.

## Skills

| Skill | What it does |
|---|---|
| [`flutter-app-structure`](plugins/flutter-team/skills/flutter-app-structure/SKILL.md) | Turns an empty `flutter create` project into our production app shell: dev/staging/prod flavors, clean architecture, DI, Cubits, networking, navigation, theme, l10n, tests, local CI. It also scaffolds features and enforces our conventions in existing apps. |

## Install

```bash
git clone https://github.com/ArafatRohan93/app-team-agent-skills.git ~/app-team-agent-skills
~/app-team-agent-skills/install.sh
```

`install.sh` symlinks every skill into the skills folder of Claude Code (`~/.claude/skills`), Codex (`~/.codex/skills`) and `~/.agents/skills`. If your agent uses a different folder, add it to `AGENT_DIRS` in the script and open a PR.

Restart your agent session afterwards so it picks the skill up.

**Agents without skill support:** tell the agent, *"Read `~/app-team-agent-skills/plugins/flutter-team/skills/flutter-app-structure/SKILL.md` and follow it."*

## Use

You don't need to call a skill by name. Just describe the task. Some examples:

- *"Create a new Flutter app called Acme Wallet, org com.acme."*
- *"Bootstrap this empty Flutter project with our app shell."*
- *"Add an orders feature that loads orders from `/orders`."*
- *"Where should a Firebase Analytics wrapper live?"*
- *"Review this branch against our Flutter architecture."*

In Claude Code you can also invoke it explicitly with `/flutter-app-structure`.

### Prerequisites for the Flutter skill

- Flutter, or [fvm](https://fvm.app) with a `.fvmrc`. The scripts detect fvm automatically.
- `python3`
- For iOS flavors: macOS, Xcode, and the `xcodeproj` Ruby gem (installed with CocoaPods). Check with `gem list xcodeproj`.

## Update

```bash
git -C ~/app-team-agent-skills pull
~/app-team-agent-skills/install.sh   # only needed if new skills were added
```

## Contributing

Skills change through pull requests, like code.

1. Edit the skill under `plugins/<plugin>/skills/<skill>/`.
2. **Verify it still works.** For `flutter-app-structure`, bootstrap a fresh app and run its CI:
   ```bash
   flutter create --org com.acme --project-name demo_app --platforms android,ios /tmp/demo_app
   python3 plugins/flutter-team/skills/flutter-app-structure/scripts/bootstrap_app.py --root /tmp/demo_app --app-name "Demo App"
   (cd /tmp/demo_app && scripts/local_ci.sh)
   ```
3. Bump `version` in `plugins/<plugin>/.claude-plugin/plugin.json` (patch for fixes, minor for new conventions, major for breaking changes to the generated shell).
4. Open a PR. Describe what changed and why.

**Adding a skill:** create `plugins/<plugin>/skills/<new-skill>/SKILL.md` with `name` and `description` frontmatter. Put the details in `references/` and deterministic steps in `scripts/`. Then re-run `install.sh`.

## Layout

```
plugins/
└── flutter-team/
    ├── .claude-plugin/plugin.json      # name + version (also lets us publish a marketplace later)
    └── skills/
        └── flutter-app-structure/      # SKILL.md, references/, scripts/, assets/
install.sh                              # symlinks skills into each agent's folder
```
