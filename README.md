# App Team Agent Skills

Our team's shared skills for AI coding agents: Claude Code, Antigravity, Codex, Cursor, Gemini CLI and others. A skill is a folder of instructions, reference docs and scripts. An agent loads it when a task matches the skill's description. That way every agent follows the same team standards, whoever is driving it.

## Skills

| Skill | What it does |
|---|---|
| [`flutter-app-structure`](plugins/flutter-team/skills/flutter-app-structure/SKILL.md) | Turns an empty `flutter create` project into our production app shell: dev/staging/prod flavors, clean architecture, DI, Cubits, networking, navigation, theme, l10n, tests, local CI. It also scaffolds features and enforces our conventions in existing apps. |

## Install

Pick one option. If the repo is private, you need read access to it first. Every option uses your existing git or GitHub login.

### Option 1: `npx skills` (recommended)

Requires [Node.js](https://nodejs.org). [`skills`](https://github.com/vercel-labs/skills) is a CLI that installs skills from a GitHub repo into any supported agent. `npx` runs it without installing anything globally.

```bash
npx skills add https://github.com/ArafatRohan93/app-team-agent-skills/tree/main/plugins/flutter-team/skills/flutter-app-structure -g
```

- `-g` installs the skill for your user, so it's available in every project. Leave it out to install only into the current project.
- The CLI asks which agents to install for. To skip the prompt, name them:
  ```bash
  npx skills add https://github.com/ArafatRohan93/app-team-agent-skills/tree/main/plugins/flutter-team/skills/flutter-app-structure \
    -g -a claude-code antigravity codex cursor -y
  ```
- If your agent doesn't pick up the skill, re-run with `--copy`. That installs a real copy instead of a symlink.

To manage it later:

```bash
npx skills list -g                           # what's installed globally
npx skills update                            # pull the latest version
npx skills remove -g flutter-app-structure   # uninstall (see Uninstall below)
```

Leave out `-g` if you installed into a single project.

### Option 2: `git clone` + `install.sh`

No Node.js needed.

```bash
git clone https://github.com/ArafatRohan93/app-team-agent-skills.git ~/app-team-agent-skills
~/app-team-agent-skills/install.sh
```

`install.sh` symlinks every skill in the repo into `~/.claude/skills` (Claude Code), `~/.codex/skills` (Codex) and `~/.agents/skills`. For other agents, add a link by hand (see Option 3), or add the agent's folder to `AGENT_DIRS` in the script and open a PR.

### Option 3: link it into one agent by hand

Clone the repo as in Option 2, then link the skill folder into the location your agent reads:

| Agent | Global folder (all projects) | Project folder |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| Antigravity (2.0, IDE, CLI) | `~/.gemini/config/skills/` | `.agents/skills/` |
| Codex | `~/.codex/skills/` | `.agents/skills/` |
| Cursor | `~/.cursor/skills/` | `.agents/skills/` |
| Gemini CLI | `~/.gemini/skills/` | `.agents/skills/` |

```bash
# example: Antigravity
mkdir -p ~/.gemini/config/skills
ln -s ~/app-team-agent-skills/plugins/flutter-team/skills/flutter-app-structure ~/.gemini/config/skills/flutter-app-structure
```

If the agent ignores symlinks, use `cp -R` instead of `ln -s`, and re-copy after each update.

### Agents without skill support

Clone the repo, then tell the agent: *"Read `~/app-team-agent-skills/plugins/flutter-team/skills/flutter-app-structure/SKILL.md` and follow it."*

### Check that it worked

Start a **new** agent session, since running sessions don't pick up new skills. Then ask: *"Where should a Dio wrapper go in a Flutter app?"* If the skill loaded, the answer mentions `core/network/` for the contract and `shared/network/` for the Dio implementation.

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

- **Installed with `npx skills`:** run `npx skills update`.
- **Installed with `git clone`:**
  ```bash
  git -C ~/app-team-agent-skills pull
  ~/app-team-agent-skills/install.sh   # only needed if new skills were added
  ```
  Symlinks pick up the change right away. Anything you installed with `cp -R` needs to be copied again.

## Uninstall

### Installed with `npx skills`

```bash
npx skills remove -g flutter-app-structure        # global install
npx skills remove flutter-app-structure           # project install (run it in that project)
npx skills remove -g -a claude-code flutter-app-structure   # remove from one agent only
```

This removes the skill from every agent `npx` installed it for. Add `-y` to skip the confirmation prompt. Don't use `--all` unless you want to remove **every** skill you've installed, not just this one.

### Installed with `install.sh` or by hand

`npx` doesn't know about these links, so delete them yourself. They're symlinks, so `rm` removes only the link, not the repo:

```bash
rm -f ~/.claude/skills/flutter-app-structure \
      ~/.codex/skills/flutter-app-structure \
      ~/.agents/skills/flutter-app-structure \
      ~/.gemini/config/skills/flutter-app-structure
```

If you used `cp -R` instead of a symlink, use `rm -rf` on that folder.

To remove the clone as well, run `rm -rf ~/app-team-agent-skills`.

### Check it's gone

```bash
npx skills list -g
ls ~/.claude/skills ~/.codex/skills ~/.agents/skills ~/.gemini/config/skills 2>/dev/null \
  | grep flutter-app-structure || echo "removed"
```

Then start a new agent session. Sessions that are already running keep the skill loaded until they end.

## Contributing

Skills change through pull requests, like code.

1. Edit the skill under `plugins/<plugin>/skills/<skill>/`.
2. **Verify it still works.** For `flutter-app-structure`, bootstrap a fresh app and run its CI:
   ```bash
   flutter create --org com.acme --project-name demo_app --platforms android,ios /tmp/demo_app
   # fvm users: use `fvm spawn <version> create ...` above, then pin the version so the scripts use fvm:
   #   echo '{"flutter":"<version>"}' > /tmp/demo_app/.fvmrc
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
