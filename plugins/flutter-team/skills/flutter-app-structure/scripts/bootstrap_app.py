#!/usr/bin/env python3
"""Turn a fresh `flutter create` project into the team app shell.

What it does (each step is idempotent and skips work that is already done):
  1. Copies assets/shell/ into the project (core/ contracts, shared/ impls,
     DI, three flavor entry points, l10n, theme, tests, local CI, README,
     VS Code launch configs), substituting the package name, app name, etc.
  2. Removes the `flutter create` counter boilerplate.
  3. Adds dependencies (flutter_bloc, get_it, fpdart, dio, go_router, ...).
  4. Enables l10n code generation and declares assets in pubspec.yaml.
  5. Adds native flavors — Android productFlavors and iOS build
     configurations, schemes, xcconfigs and Podfile mapping.
  6. Runs pub get, gen-l10n, dart format, and (unless --skip-verify)
     flutter analyze + flutter test.

Usage:
  python3 bootstrap_app.py --root path/to/app --app-name "Acme Wallet"
  python3 bootstrap_app.py --root . --app-name "Acme" --dry-run

Requires: python3, flutter (or fvm), and on macOS for iOS flavors: ruby with
the xcodeproj gem (ships with CocoaPods).
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SHELL_DIR = SKILL_DIR / "assets" / "shell"
TEXT_SUFFIXES = {".dart", ".md", ".yaml", ".yml", ".json", ".sh", ".arb", ".tmpl"}

FLAVORS = [
    # name, applicationId/bundle suffix, app-name prefix
    ("development", ".dev", "[DEV] "),
    ("staging", ".stg", "[STG] "),
    ("production", "", ""),
]

DEPENDENCIES = [
    "flutter_bloc",
    "bloc",
    "get_it",
    "fpdart",
    "dio",
    "go_router",
    "logger",
    "flutter_svg",
    "flutter_secure_storage",
    "intl:any",
]
DEV_DEPENDENCIES = ["dev:bloc_test", "dev:mocktail"]

# Files `flutter create` generates that the shell replaces. Overwritten only
# while they still contain their boilerplate marker.
BOILERPLATE = {
    "README.md": "A new Flutter project.",
    "analysis_options.yaml": "This file configures the analyzer",
}
REMOVE_IF_BOILERPLATE = {
    "lib/main.dart": "MyHomePage",
    "test/widget_test.dart": "Counter increments",
}


class Log:
    dry_run = False

    @staticmethod
    def step(msg):
        print(f"\n==> {msg}")

    @staticmethod
    def info(msg):
        print(f"    {msg}")


# ---------------------------------------------------------------- helpers


def run(cmd, cwd, check=True, quiet=False):
    if Log.dry_run:
        Log.info("would run: " + " ".join(cmd))
        return 0
    result = subprocess.run(cmd, cwd=cwd, capture_output=quiet, text=True)
    if check and result.returncode != 0:
        if quiet:
            sys.stderr.write((result.stdout or "") + (result.stderr or ""))
        sys.exit(f"Command failed: {' '.join(cmd)}")
    return result.returncode


def write(path: Path, content: str):
    if Log.dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def detect_flutter(root: Path):
    uses_fvm = any((d / name).exists() for d in (root, root.parent) for name in (".fvmrc", ".fvm"))
    if uses_fvm and shutil.which("fvm"):
        return ["fvm", "flutter"], ["fvm", "dart"]
    if not shutil.which("flutter"):
        sys.exit("flutter not found on PATH (and no fvm config detected)")
    return ["flutter"], ["dart"]


def flutter_version(flutter_cmd, root):
    try:
        out = subprocess.run(flutter_cmd + ["--version", "--machine"], cwd=root, capture_output=True, text=True)
        return json.loads(out.stdout).get("frameworkVersion", "stable")
    except Exception:
        return "stable"


def read_pubspec(root: Path):
    text = (root / "pubspec.yaml").read_text()
    name = re.search(r"^name:\s*([A-Za-z0-9_]+)", text, re.M)
    if not name:
        sys.exit("Could not read `name:` from pubspec.yaml")
    return name.group(1), text


def android_application_id(root: Path):
    for gradle in ("android/app/build.gradle.kts", "android/app/build.gradle"):
        path = root / gradle
        if path.exists():
            m = re.search(r'applicationId\s*=?\s*"([^"]+)"', path.read_text())
            if m:
                return m.group(1)
    return None


# ---------------------------------------------------------------- steps


def copy_shell(root: Path, tokens: dict, force: bool):
    Log.step("Copying the app shell")
    for src in sorted(SHELL_DIR.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(SHELL_DIR).as_posix()
        dest_rel = rel[: -len(".tmpl")] if rel.endswith(".tmpl") else rel
        dest = root / dest_rel

        if dest.exists() and not force:
            marker = BOILERPLATE.get(dest_rel)
            if not (marker and marker in dest.read_text()):
                Log.info(f"skip (exists): {dest_rel}")
                continue

        if src.suffix in TEXT_SUFFIXES:
            content = src.read_text()
            for key, value in tokens.items():
                content = content.replace("{{" + key + "}}", value)
            write(dest, content)
        elif not Log.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        if dest_rel.endswith(".sh") and not Log.dry_run:
            dest.chmod(0o755)
        Log.info(f"wrote: {dest_rel}")

    for rel, marker in REMOVE_IF_BOILERPLATE.items():
        path = root / rel
        if path.exists() and marker in path.read_text():
            if not Log.dry_run:
                path.unlink()
            Log.info(f"removed boilerplate: {rel}")


def add_dependencies(root: Path, flutter_cmd):
    Log.step("Adding dependencies")
    _, pubspec = read_pubspec(root)
    if "flutter_localizations:" not in pubspec:
        run(flutter_cmd + ["pub", "add", "flutter_localizations", "--sdk=flutter"], root, quiet=True)
    missing = [d for d in DEPENDENCIES if f"\n  {d.split(':')[0]}:" not in pubspec]
    missing += [d for d in DEV_DEPENDENCIES if f"\n  {d.split(':')[1]}:" not in pubspec]
    if missing:
        run(flutter_cmd + ["pub", "add", *missing], root, quiet=True)
    Log.info("ok: " + ", ".join(["flutter_localizations", *DEPENDENCIES, *DEV_DEPENDENCIES]))


def configure_pubspec(root: Path, description: str):
    Log.step("Configuring pubspec.yaml (l10n generation, assets)")
    path = root / "pubspec.yaml"
    text = path.read_text()
    if description:
        text = re.sub(r'^description:.*$', f'description: "{description}"', text, count=1, flags=re.M)
    if "generate: true" not in text:
        text = re.sub(
            r"^(\s*)uses-material-design: true\s*$",
            r"\1uses-material-design: true\n\1generate: true",
            text,
            count=1,
            flags=re.M,
        )
    if "assets/images/" not in text:
        text = re.sub(
            r"^(\s*)generate: true\s*$",
            r"\1generate: true\n\n\1assets:\n\1  - assets/images/\n\1  - assets/icons/",
            text,
            count=1,
            flags=re.M,
        )
    write(path, text)
    Log.info("ok")


def android_flavors(root: Path, app_name: str):
    Log.step("Android flavors")
    kts = root / "android/app/build.gradle.kts"
    groovy = root / "android/app/build.gradle"
    gradle = kts if kts.exists() else groovy
    if not gradle.exists():
        Log.info("skip: no android/app/build.gradle(.kts)")
        return
    text = gradle.read_text()
    res_name = lambda prefix: (prefix + app_name).replace("'", "\\'").replace('"', '\\"')

    if "productFlavors" in text:
        Log.info("skip: productFlavors already defined")
    else:
        if gradle == kts:
            blocks = "".join(
                f'        create("{name}") {{\n'
                f'            dimension = "environment"\n'
                + (f'            applicationIdSuffix = "{suffix}"\n' if suffix else "")
                + f'            resValue("string", "app_name", "{res_name(prefix)}")\n'
                f"        }}\n"
                for name, suffix, prefix in FLAVORS
            )
            snippet = (
                '    flavorDimensions += "environment"\n'
                f"    productFlavors {{\n{blocks}    }}\n\n"
            )
        else:
            blocks = "".join(
                f"        {name} {{\n"
                f'            dimension "environment"\n'
                + (f'            applicationIdSuffix "{suffix}"\n' if suffix else "")
                + f'            resValue "string", "app_name", "{res_name(prefix)}"\n'
                f"        }}\n"
                for name, suffix, prefix in FLAVORS
            )
            snippet = (
                '    flavorDimensions "environment"\n'
                f"    productFlavors {{\n{blocks}    }}\n\n"
            )
        if "\n    buildTypes {" not in text:
            sys.exit(f"Could not find `buildTypes {{` in {gradle}; add productFlavors manually")
        text = text.replace("\n    buildTypes {", "\n" + snippet + "    buildTypes {", 1)
        write(gradle, text)
        Log.info(f"added productFlavors to {gradle.relative_to(root)}")

    manifest = root / "android/app/src/main/AndroidManifest.xml"
    if manifest.exists():
        m = manifest.read_text()
        new = re.sub(r'android:label="[^"]*"', 'android:label="@string/app_name"', m, count=1)
        if new != m:
            write(manifest, new)
            Log.info("AndroidManifest label → @string/app_name")


PODFILE = """# Uncomment this line to define a global platform for your project
# platform :ios, '13.0'

# CocoaPods analytics sends network stats synchronously affecting flutter build latency.
ENV['COCOAPODS_DISABLE_STATS'] = 'true'

project 'Runner', {
__CONFIGS__
}

def flutter_root
  generated_xcode_build_settings_path = File.expand_path(File.join('..', 'Flutter', 'Generated.xcconfig'), __FILE__)
  unless File.exist?(generated_xcode_build_settings_path)
    raise "#{generated_xcode_build_settings_path} must exist. If you're running pod install manually, make sure flutter pub get is executed first"
  end

  File.foreach(generated_xcode_build_settings_path) do |line|
    matches = line.match(/FLUTTER_ROOT\\=(.*)/)
    return matches[1].strip if matches
  end
  raise "FLUTTER_ROOT not found in #{generated_xcode_build_settings_path}. Try deleting Generated.xcconfig, then run flutter pub get"
end

require File.expand_path(File.join('packages', 'flutter_tools', 'bin', 'podhelper'), flutter_root)

flutter_ios_podfile_setup

target 'Runner' do
  use_frameworks!

  flutter_install_all_ios_pods File.dirname(File.realpath(__FILE__))
  target 'RunnerTests' do
    inherit! :search_paths
  end
end

post_install do |installer|
  installer.pods_project.targets.each do |target|
    flutter_additional_ios_build_settings(target)
  end
end
"""


def ios_flavors(root: Path, app_name: str):
    Log.step("iOS flavors")
    ios = root / "ios"
    if not (ios / "Runner.xcodeproj").exists():
        Log.info("skip: no ios/Runner.xcodeproj")
        return

    # 1. Build configurations + per-config xcconfigs (Ruby + xcodeproj gem).
    ruby = shutil.which("ruby")
    spec = {
        "default_app_name": app_name,
        "flavors": [{"name": n, "suffix": s, "app_name": p + app_name} for n, s, p in FLAVORS],
    }
    if not ruby:
        sys.exit("ruby not found — needed for iOS flavors (or pass --skip-ios)")
    if Log.dry_run:
        Log.info("would add Debug/Release/Profile-<flavor> build configurations")
    else:
        code = subprocess.run([ruby, str(SKILL_DIR / "scripts/ios_flavors.rb"), str(ios), json.dumps(spec)]).returncode
        if code != 0:
            sys.exit("iOS flavor setup failed (see above). Install the xcodeproj gem or pass --skip-ios.")

    # 2. Pods includes for the plain configs (what flutter would add itself).
    for base, pods in (("Debug", "debug"), ("Release", "release")):
        path = ios / f"Flutter/{base}.xcconfig"
        include = f'#include? "Pods/Target Support Files/Pods-Runner/Pods-Runner.{pods}.xcconfig"\n'
        if path.exists() and "Pods-Runner" not in path.read_text():
            write(path, include + path.read_text())

    # 3. One shared scheme per flavor, cloned from Runner.xcscheme.
    schemes = ios / "Runner.xcodeproj/xcshareddata/xcschemes"
    runner_scheme = schemes / "Runner.xcscheme"
    if runner_scheme.exists():
        template = runner_scheme.read_text()
        for name, _, _ in FLAVORS:
            target = schemes / f"{name}.xcscheme"
            if target.exists():
                continue
            content = re.sub(
                r'buildConfiguration = "(Debug|Release|Profile)"',
                lambda m: f'buildConfiguration = "{m.group(1)}-{name}"',
                template,
            )
            write(target, content)
            Log.info(f"scheme: {name}")

    # 4. Podfile mapping every configuration to debug/release.
    configs = ["'Debug' => :debug", "'Profile' => :release", "'Release' => :release"]
    for name, _, _ in FLAVORS:
        configs += [f"'Debug-{name}' => :debug", f"'Profile-{name}' => :release", f"'Release-{name}' => :release"]
    mapping = "\n".join(f"  {c}," for c in configs)
    podfile = ios / "Podfile"
    if podfile.exists():
        text = podfile.read_text()
        if "Debug-development" not in text:
            text = re.sub(r"project 'Runner', \{.*?\n\}", "project 'Runner', {\n" + mapping + "\n}", text, count=1, flags=re.S)
            write(podfile, text)
            Log.info("Podfile: configuration mapping updated")
    else:
        write(podfile, PODFILE.replace("__CONFIGS__", mapping))
        Log.info("Podfile: created with flavor configuration mapping")

    # 5. Info.plist: flavor display name + declared localizations.
    plist = ios / "Runner/Info.plist"
    if plist.exists():
        text = plist.read_text()
        text = re.sub(
            r"(<key>CFBundleDisplayName</key>\s*<string>)[^<]*(</string>)",
            r"\1$(FLAVOR_APP_NAME)\2",
            text,
            count=1,
        )
        if "CFBundleLocalizations" not in text:
            text = re.sub(
                r"</dict>\s*</plist>\s*$",
                "\t<key>CFBundleLocalizations</key>\n\t<array>\n\t\t<string>en</string>\n\t</array>\n</dict>\n</plist>\n",
                text,
                count=1,
            )
        write(plist, text)
        Log.info("Info.plist: CFBundleDisplayName → $(FLAVOR_APP_NAME), CFBundleLocalizations [en]")


def finish(root: Path, flutter_cmd, dart_cmd, verify: bool):
    Log.step("pub get, gen-l10n, format")
    run(flutter_cmd + ["pub", "get"], root, quiet=True)
    run(flutter_cmd + ["gen-l10n"], root, quiet=True)
    run(dart_cmd + ["format", "lib", "test"], root, quiet=True)
    Log.info("ok")

    if verify:
        Log.step("Verifying: flutter analyze")
        run(flutter_cmd + ["analyze", "--fatal-infos", "--fatal-warnings"], root)
        Log.step("Verifying: flutter test")
        run(flutter_cmd + ["test"], root)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="Flutter project root (created with `flutter create`)")
    ap.add_argument("--app-name", help="Human-readable app name (default: from package name)")
    ap.add_argument("--description", default="", help="One-line description for pubspec and README")
    ap.add_argument("--skip-android", action="store_true", help="Do not touch android/")
    ap.add_argument("--skip-ios", action="store_true", help="Do not touch ios/")
    ap.add_argument("--skip-verify", action="store_true", help="Skip flutter analyze / test at the end")
    ap.add_argument("--force", action="store_true", help="Overwrite existing files with shell versions")
    ap.add_argument("--dry-run", action="store_true", help="Show what would happen without changing anything")
    args = ap.parse_args()
    Log.dry_run = args.dry_run

    root = Path(args.root).resolve()
    if not (root / "pubspec.yaml").exists():
        sys.exit(f"No pubspec.yaml in {root}. Run `flutter create` first.")
    package, _ = read_pubspec(root)
    app_name = args.app_name or " ".join(w.capitalize() for w in package.split("_"))
    bundle_id = android_application_id(root) or f"com.example.{package}"
    flutter_cmd, dart_cmd = detect_flutter(root)
    uses_fvm = flutter_cmd[0] == "fvm"

    tokens = {
        "package": package,
        "app_name": app_name,
        "bundle_id": bundle_id,
        "description": args.description or f"The {app_name} Flutter app.",
        "flutter": " ".join(flutter_cmd),
        "flutter_version": flutter_version(flutter_cmd, root),
        "fvm_note": " (managed with [fvm](https://fvm.app) — prefix commands with `fvm`)" if uses_fvm else "",
    }
    print(f"Bootstrapping {package} ({app_name}, {bundle_id}) with `{' '.join(flutter_cmd)}`")

    copy_shell(root, tokens, args.force)
    if not args.dry_run:
        add_dependencies(root, flutter_cmd)
        configure_pubspec(root, args.description)
    if not args.skip_android:
        android_flavors(root, app_name)
    if not args.skip_ios:
        ios_flavors(root, app_name)
    if not args.dry_run:
        finish(root, flutter_cmd, dart_cmd, verify=not args.skip_verify)

    print(
        "\nDone. Next:\n"
        f"  - Set real base URLs in lib/main_<flavor>.dart\n"
        f"  - Run: {' '.join(flutter_cmd)} run --flavor development -t lib/main_development.dart\n"
        "  - Full gate (builds all platforms): scripts/local_ci.sh\n"
        "  - Add features: python3 <skill-dir>/scripts/scaffold_feature.py --feature <name> --entity <Entity>"
    )


if __name__ == "__main__":
    main()
