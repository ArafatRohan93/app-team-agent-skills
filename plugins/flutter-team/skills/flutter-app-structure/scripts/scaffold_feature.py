#!/usr/bin/env python3
"""Scaffold a feature module following the flutter-app-structure conventions.

Generates compile-ready stubs for:
  lib/features/<feature>/data/{models,data_sources,repositories}/
  lib/features/<feature>/domain/{repositories,use_cases}/
  lib/features/<feature>/presentation/{cubits,screens}/
  lib/di/modules/<feature>_module.dart
  test/features/<feature>/... (mirrored tests)

Existing files are never overwritten. The package name is read from pubspec.yaml.

Example:
  python3 scaffold_feature.py --root ./my_app --feature history --entity Transaction
  python3 scaffold_feature.py --root . --feature settings --entity Setting --layers presentation
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def snake(name: str) -> str:
    s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name.strip())
    return re.sub(r"[\s\-]+", "_", s).lower()


def pascal(name: str) -> str:
    return "".join(p[:1].upper() + p[1:] for p in snake(name).split("_") if p)


def camel(name: str) -> str:
    p = pascal(name)
    return p[:1].lower() + p[1:]


def pluralize(word: str) -> str:
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ies"
    if re.search(r"(s|x|z|ch|sh)$", word):
        return word + "es"
    return word + "s"


def read_package(root: Path) -> str:
    pubspec = root / "pubspec.yaml"
    if not pubspec.exists():
        sys.exit(f"pubspec.yaml not found in {root}")
    m = re.search(r"^name:\s*([A-Za-z0-9_]+)", pubspec.read_text(), re.M)
    if not m:
        sys.exit("Could not read `name:` from pubspec.yaml")
    return m.group(1)


def format_files(root: Path, rels):
    """Run `dart format` (via fvm when the project uses it) — line wrapping depends on name lengths."""
    uses_fvm = (root / ".fvmrc").exists() or (root / ".fvm").exists() or (root.parent / ".fvmrc").exists()
    cmd = (["fvm", "dart"] if uses_fvm and shutil.which("fvm") else ["dart"]) + ["format", *rels]
    if not shutil.which(cmd[0]):
        print("\n(dart not found — run `dart format` on the new files yourself)")
        return
    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    status = "Formatted with" if result.returncode == 0 else "Formatting failed:"
    print(f"\n{status} `{' '.join(cmd[:3])}`" + ("" if result.returncode == 0 else f"\n{result.stderr}"))


def build_files(pkg, feature, entity, plural, layers, l10n=False):
    f = snake(feature)
    F = pascal(feature)
    e = snake(entity)
    E = pascal(entity)
    ps = snake(plural)
    P = pascal(plural)
    pc = camel(plural)
    endpoint = "/" + ps.replace("_", "-")

    has_data = "data" in layers
    has_domain = "domain" in layers
    has_pres = "presentation" in layers
    lib = f"lib/features/{f}"
    test = f"test/features/{f}"
    imp = f"package:{pkg}"
    model_import = f"import '{imp}/features/{f}/data/models/{e}.dart';"
    files = {}

    if has_data:
        files[f"{lib}/data/models/{e}.dart"] = f"""class {E} {{
  const {E}({{required this.id}});

  final String id;

  factory {E}.fromJson(Map<String, dynamic> json) => {E}(
    id: json['id'] as String,
  );
}}
"""

        files[f"{lib}/data/data_sources/{e}_remote_data_source.dart"] = f"""import 'dart:convert';

import 'package:fpdart/fpdart.dart';
import '{imp}/core/network/network_client.dart';
import '{imp}/core/network/network_exception.dart';
{model_import}

class {E}RemoteDataSource {{
  const {E}RemoteDataSource({{required NetworkClient networkClient}})
    : _client = networkClient;

  final NetworkClient _client;

  Future<Either<NetworkException, List<{E}>>> get{P}() async {{
    try {{
      final response = await _client.get('{endpoint}');
      if (response.error != null) return left(response.error!);
      final json = jsonDecode(response.jsonResponse!) as Map<String, dynamic>;
      final list = json['{pc}'] as List<dynamic>;
      return right(
        list.map((e) => {E}.fromJson(e as Map<String, dynamic>)).toList(),
      );
    }} on NetworkException catch (e) {{
      return left(e);
    }} catch (e) {{
      return left(UnknownNetworkException(message: e.toString()));
    }}
  }}
}}
"""

    if has_domain:
        files[f"{lib}/domain/repositories/{e}_repository.dart"] = f"""import 'package:fpdart/fpdart.dart';
import '{imp}/core/domain/failures/failure.dart';
{model_import}

abstract interface class {E}Repository {{
  Future<Either<Failure, List<{E}>>> get{P}();
}}
"""

        files[f"{lib}/domain/use_cases/get_{ps}_use_case.dart"] = f"""import 'package:fpdart/fpdart.dart';
import '{imp}/core/domain/failures/failure.dart';
{model_import}
import '{imp}/features/{f}/domain/repositories/{e}_repository.dart';

class Get{P}UseCase {{
  const Get{P}UseCase({{required {E}Repository repository}})
    : _repository = repository;

  final {E}Repository _repository;

  Future<Either<Failure, List<{E}>>> call() => _repository.get{P}();
}}
"""

    if has_data and has_domain:
        files[f"{lib}/data/repositories/{e}_repository_impl.dart"] = f"""import 'package:fpdart/fpdart.dart';
import '{imp}/core/domain/failures/failure.dart';
import '{imp}/core/network/network_exception_ext.dart';
import '{imp}/features/{f}/data/data_sources/{e}_remote_data_source.dart';
{model_import}
import '{imp}/features/{f}/domain/repositories/{e}_repository.dart';

class {E}RepositoryImpl implements {E}Repository {{
  const {E}RepositoryImpl({{required {E}RemoteDataSource dataSource}})
    : _dataSource = dataSource;

  final {E}RemoteDataSource _dataSource;

  @override
  Future<Either<Failure, List<{E}>>> get{P}() async {{
    final result = await _dataSource.get{P}();
    return result.mapLeft((e) => e.toFailure());
  }}
}}
"""

        files[f"lib/di/modules/{f}_module.dart"] = f"""import 'package:get_it/get_it.dart';
import '{imp}/features/{f}/data/data_sources/{e}_remote_data_source.dart';
import '{imp}/features/{f}/data/repositories/{e}_repository_impl.dart';
import '{imp}/features/{f}/domain/repositories/{e}_repository.dart';
import '{imp}/features/{f}/domain/use_cases/get_{ps}_use_case.dart';

void register{F}Dependencies() {{
  final sl = GetIt.instance;
  sl.registerLazySingleton<{E}Repository>(
    () => {E}RepositoryImpl(
      dataSource: {E}RemoteDataSource(networkClient: sl()),
    ),
  );
  sl.registerLazySingleton<Get{P}UseCase>(
    () => Get{P}UseCase(repository: sl()),
  );
}}
"""

        files[f"{test}/data/repositories/{e}_repository_impl_test.dart"] = f"""import 'package:flutter_test/flutter_test.dart';
import 'package:fpdart/fpdart.dart';
import 'package:mocktail/mocktail.dart';
import '{imp}/core/domain/failures/failure.dart';
import '{imp}/core/network/network_exception.dart';
import '{imp}/features/{f}/data/data_sources/{e}_remote_data_source.dart';
{model_import}
import '{imp}/features/{f}/data/repositories/{e}_repository_impl.dart';

class _Mock{E}RemoteDataSource extends Mock implements {E}RemoteDataSource {{}}

const _{camel(entity)} = {E}(id: '{e}-1');

void main() {{
  late _Mock{E}RemoteDataSource dataSource;
  late {E}RepositoryImpl repository;

  setUp(() {{
    dataSource = _Mock{E}RemoteDataSource();
    repository = {E}RepositoryImpl(dataSource: dataSource);
  }});

  group('{E}RepositoryImpl.get{P}', () {{
    test('returns Right with {ps.replace('_', ' ')} on success', () async {{
      when(
        () => dataSource.get{P}(),
      ).thenAnswer((_) async => right([_{camel(entity)}]));

      final result = await repository.get{P}();

      expect(result.getRight().toNullable(), [_{camel(entity)}]);
    }});

    test('maps UnauthorizedNetworkException to UnauthorizedFailure', () async {{
      when(
        () => dataSource.get{P}(),
      ).thenAnswer((_) async => left(const UnauthorizedNetworkException()));

      final result = await repository.get{P}();

      expect(result.getLeft().toNullable(), isA<UnauthorizedFailure>());
    }});
  }});
}}
"""

    if has_pres:
        uses_uc = has_domain and has_data
        if uses_uc:
            cubit_imports = f"""import 'package:flutter_bloc/flutter_bloc.dart';
import '{imp}/core/domain/failures/failure.dart';
{model_import}
import '{imp}/features/{f}/domain/use_cases/get_{ps}_use_case.dart';
"""
            cubit_body = f"""class {F}Cubit extends Cubit<{F}State> {{
  {F}Cubit({{required Get{P}UseCase get{P}}})
    : _get{P} = get{P},
      super(const {F}Initial());

  final Get{P}UseCase _get{P};

  Future<void> load() async {{
    emit(const {F}Loading());
    final result = await _get{P}();
    result.fold(
      (failure) => emit({F}Error(_messageFor(failure))),
      ({pc}) => emit({F}Loaded({pc})),
    );
  }}

  static String _messageFor(Failure failure) => switch (failure) {{
    ServerFailure(:final message) =>
      message.isNotEmpty ? message : 'Server error',
    NetworkFailure() => 'No internet connection',
    UnauthorizedFailure() => 'Session expired. Please sign in again.',
    UnknownFailure(:final message) => message,
  }};
}}
"""
            loaded = f"""class {F}Loaded extends {F}State {{
  const {F}Loaded(this.{pc});

  final List<{E}> {pc};
}}
"""
        else:
            cubit_imports = "import 'package:flutter_bloc/flutter_bloc.dart';\n"
            cubit_body = f"""class {F}Cubit extends Cubit<{F}State> {{
  {F}Cubit() : super(const {F}Initial());

  Future<void> load() async {{
    emit(const {F}Loading());
    // TODO: call a use case and emit {F}Loaded / {F}Error.
    emit(const {F}Loaded());
  }}
}}
"""
            loaded = f"""class {F}Loaded extends {F}State {{
  const {F}Loaded();
}}
"""

        if l10n:
            # States carry the Failure; the screen localizes it.
            cubit_body = cubit_body.replace(
                f"emit({F}Error(_messageFor(failure)))", f"emit({F}Error(failure))"
            )
            cubit_body = re.sub(r"\n\n  static String _messageFor.*?\n  };\n", "\n", cubit_body, flags=re.S)
            if "failures/failure.dart" not in cubit_imports:
                cubit_imports += f"import '{imp}/core/domain/failures/failure.dart';\n"

        files[f"{lib}/presentation/cubits/{f}_cubit.dart"] = (
            f"{cubit_imports}\npart '{f}_state.dart';\n\n{cubit_body}"
        )

        err_field, err_type = ("failure", "Failure") if l10n else ("message", "String")
        files[f"{lib}/presentation/cubits/{f}_state.dart"] = f"""part of '{f}_cubit.dart';

sealed class {F}State {{
  const {F}State();
}}

class {F}Initial extends {F}State {{
  const {F}Initial();
}}

class {F}Loading extends {F}State {{
  const {F}Loading();
}}

{loaded}
class {F}Error extends {F}State {{
  const {F}Error(this.{err_field});

  final {err_type} {err_field};
}}
"""

        if uses_uc:
            screen_imports = f"""import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '{imp}/di/service_locator.dart';
import '{imp}/features/{f}/domain/use_cases/get_{ps}_use_case.dart';
import '{imp}/features/{f}/presentation/cubits/{f}_cubit.dart';
import '{imp}/shared/theme/tokens/app_dimensions.dart';
"""
            create = f"{F}Cubit(get{P}: sl<Get{P}UseCase>())..load()"
            loaded_case = f"""{F}Loaded(:final {pc}) => ListView.separated(
            padding: const EdgeInsets.all(AppDimensions.spacingXl),
            itemCount: {pc}.length,
            separatorBuilder: (_, _) =>
                const SizedBox(height: AppDimensions.spacingLg),
            itemBuilder: (_, i) => Text({pc}[i].id),
          ),"""
        else:
            screen_imports = f"""import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '{imp}/features/{f}/presentation/cubits/{f}_cubit.dart';
"""
            create = f"{F}Cubit()..load()"
            loaded_case = f"{F}Loaded() => const SizedBox.shrink(),"

        if l10n:
            screen_imports += (
                f"import '{imp}/l10n/failure_l10n.dart';\n"
                f"import '{imp}/l10n/l10n.dart';\n"
            )
            error_case = f"""{F}Error(:final failure) => Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(failure.localizedMessage(context.l10n)),
                TextButton(
                  onPressed: () => context.read<{F}Cubit>().load(),
                  child: Text(context.l10n.commonRetry),
                ),
              ],
            ),
          ),"""
        else:
            error_case = f"""{F}Error(:final message) => Center(
            child: TextButton(
              onPressed: () => context.read<{F}Cubit>().load(),
              child: Text(message),
            ),
          ),"""

        files[f"{lib}/presentation/screens/{f}_screen.dart"] = f"""{screen_imports}
class {F}Screen extends StatelessWidget {{
  const {F}Screen({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return BlocProvider(
      create: (_) => {create},
      child: BlocBuilder<{F}Cubit, {F}State>(
        builder: (context, state) => switch (state) {{
          {F}Initial() || {F}Loading() => const Center(
            child: CircularProgressIndicator(),
          ),
          {loaded_case}
          {error_case}
        }},
      ),
    );
  }}
}}
"""

        if uses_uc:
            files[f"{test}/presentation/cubits/{f}_cubit_test.dart"] = f"""import 'package:flutter_test/flutter_test.dart';
import 'package:fpdart/fpdart.dart';
import 'package:mocktail/mocktail.dart';
import '{imp}/core/domain/failures/failure.dart';
{model_import}
import '{imp}/features/{f}/domain/use_cases/get_{ps}_use_case.dart';
import '{imp}/features/{f}/presentation/cubits/{f}_cubit.dart';

class _MockGet{P}UseCase extends Mock implements Get{P}UseCase {{}}

void main() {{
  late _MockGet{P}UseCase get{P};

  setUp(() => get{P} = _MockGet{P}UseCase());

  {F}Cubit buildCubit() => {F}Cubit(get{P}: get{P});

  group('{F}Cubit', () {{
    test('initial state is {F}Initial', () {{
      final cubit = buildCubit();
      expect(cubit.state, isA<{F}Initial>());
      cubit.close();
    }});

    group('load()', () {{
      test('emits [{F}Loading, {F}Loaded] on success', () async {{
        when(
          () => get{P}(),
        ).thenAnswer((_) async => right(const [{E}(id: '{e}-1')]));

        final cubit = buildCubit();
        final future = expectLater(
          cubit.stream,
          emitsInOrder([isA<{F}Loading>(), isA<{F}Loaded>()]),
        );
        await cubit.load();
        await future;
        await cubit.close();
      }});

      test('emits [{F}Loading, {F}Error] on failure', () async {{
        when(
          () => get{P}(),
        ).thenAnswer((_) async => left(const NetworkFailure()));

        final cubit = buildCubit();
        final future = expectLater(
          cubit.stream,
          emitsInOrder([isA<{F}Loading>(), isA<{F}Error>()]),
        );
        await cubit.load();
        await future;
        await cubit.close();
      }});
    }});
  }});
}}
"""

    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="Flutter project root (contains pubspec.yaml)")
    ap.add_argument("--feature", required=True, help="Feature folder name, e.g. history")
    ap.add_argument("--entity", required=True, help="Main entity/model name, e.g. Transaction")
    ap.add_argument("--plural", help="Plural of entity (default: naive English plural)")
    ap.add_argument("--layers", default="data,domain,presentation", help="Comma-separated subset of data,domain,presentation")
    ap.add_argument("--dry-run", action="store_true", help="Print what would be created without writing")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    pkg = read_package(root)
    layers = {l.strip() for l in args.layers.split(",") if l.strip()}
    unknown = layers - {"data", "domain", "presentation"}
    if unknown:
        sys.exit(f"Unknown layers: {', '.join(sorted(unknown))}")
    plural = args.plural or pluralize(pascal(args.entity))

    # Projects bootstrapped from the shell localize failures in the widget layer.
    l10n = (root / "lib/l10n/failure_l10n.dart").exists()
    files = build_files(pkg, args.feature, args.entity, plural, layers, l10n)
    created, skipped = [], []
    for rel, content in files.items():
        path = root / rel
        if path.exists():
            skipped.append(rel)
            continue
        created.append(rel)
        if not args.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    verb = "Would create" if args.dry_run else "Created"
    for rel in created:
        print(f"{verb}: {rel}")
    for rel in skipped:
        print(f"Skipped (exists): {rel}")

    if created and not args.dry_run:
        format_files(root, created)

    f = snake(args.feature)
    F = pascal(args.feature)
    print("\nNext steps:")
    if "data" in layers and "domain" in layers:
        print(f"  - Call register{F}Dependencies() in setupDependencies (lib/di/service_locator.dart)")
    if "presentation" in layers:
        print(f"  - Add an AppRoute entry and GoRoute for {F}Screen in lib/shared/navigation/")
    print(f"  - Fill in model fields, endpoint and business rules under lib/features/{f}/")
    print("  - Run: dart format lib test && flutter analyze && flutter test  (prefix with fvm if used)")


if __name__ == "__main__":
    main()
