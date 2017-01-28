import sys
from toml import toml
import urllib
import itertools
import os
from wget import wget
import tarfile
import copy
from cargo_toml import CargoLock, CargoToml

alias_file_template = """\
# This is a direct dependency
# You've come to the right place!

package(default_visibility = ["//visibility:public"])

# TODO: we don't actually know this
licenses(["notice"])
alias(
    name = "{0}",
    actual = "{1}",
)
"""

build_file_template = """\
# This is (probably) a transitive dependency
# You likely want "//third_party/cargo2bazel/{0}"
#
# If your package is not available there, you must require it explicitly in Cargo.toml and rerun
# cargo2bazel
package(default_visibility = [
  "//third_party/cargo2bazel:__subpackages__",
])

load(
    "@io_bazel_rules_rust//rust:rust.bzl",
    "rust_library",
)

# TODO: we don't actually know this
licenses(["notice"])

rust_library(
    name = "{0}",
    deps = {1},
    srcs = glob(["../lib.rs", "../src/**/*.rs"]),
    rustc_flags = [
      "--cap-lints warn",
    ],
    crate_features = {2},
)
"""


def main():
    assert len(sys.argv) >= 4, "expected to receive the cargo.lock, the cargo.toml, and the codegen directory as arguments"
    toml_path = sys.argv[1]
    lock_path = sys.argv[2]
    codegen_dir = sys.argv[3]

    cargo_toml = CargoToml(load_toml(toml_path))
    cargo_lock = CargoLock(load_toml(lock_path))
    gen_root = codegen_dir + '/third_party/cargo2bazel/'
    gen_root_internal = gen_root + "internal/"

    if not os.path.exists(gen_root_internal):
      os.makedirs(gen_root_internal)

    download_dependencies(cargo_lock, gen_root_internal)
    dependency_toml_map = read_tomls(cargo_lock, gen_root_internal)
    variants = identify_package_variants(cargo_toml, cargo_lock.root)

    dependency_lock_map = {}
    for package in cargo_lock.packages:
        package_key = "{0}-{1}".format(package.name, package.version)
        dependency_lock_map[package_key] = package
        variants.extend(identify_package_variants(
            dependency_toml_map[package_key],
            package))

    distinct_variants = set(variants)
    add_build_rules(
            gen_root_internal,
            distinct_variants,
            dependency_toml_map,
            dependency_lock_map);

    add_aliases(
            gen_root,
            cargo_toml.dependencies,
            cargo_lock.root.dependencies)

def load_toml(file_path):
    with open(file_path) as open_file:
        return toml.loads(open_file.read())

def download_dependencies(cargo_lock, gen_root_internal):
    for package in cargo_lock.packages:
        if package.source != "registry+https://github.com/rust-lang/crates.io-index":
            print("Only packages from crates.io are supported, dependencies on [{0}-{1}] may not work".format(package.name, package.version))
            continue

        url = "https://crates.io/api/v1/crates/{0}/{1}/download".format(
            package.name,
            package.version)

        tar_path = (gen_root_internal + "{0}-{1}.tar").format(package.name, package.version)
        if not os.path.exists(tar_path):
            print("Downloading {}".format(url))
            wget.download(url, out=tar_path)

        expected_path = gen_root_internal + "{0}-{1}/".format(
            package.name,
            package.version)

        if not os.path.exists(expected_path):
            print("Unpacking {}".format(tar_path))
            tar_file = tarfile.open(tar_path)
            tar_file.extractall(path=gen_root_internal)
            tar_file.close()


def read_tomls(cargo_lock, gen_root_internal):
    toml_map = {}
    for package in cargo_lock.packages:
        if package.source is "registry+https://github.com/rust-lang/crates.io-index":
            continue

        toml_path = "{0}{1}-{2}/Cargo.toml".format(
                gen_root_internal,
                package.name,
                package.version)

        print("Loading {0}".format(toml_path))
        package_key = '{0}-{1}'.format(package.name, package.version)
        toml_map[package_key] = CargoToml(load_toml(toml_path))
    return toml_map

def identify_package_variants(cargo_toml, cargo_lock_package):
    dep_map = {}
    variants = []
    for toml_dependency in cargo_toml.dependencies:
        dep_map[toml_dependency.name] = toml_dependency

    for lock_dependency in cargo_lock_package.dependencies:
        if lock_dependency.name not in dep_map:
            # Dev-dependency, dont need it.
            continue
        toml_dependency = dep_map[lock_dependency.name]
        variants.append(PackageVariant(
                lock_dependency.name,
                lock_dependency.version,
                toml_dependency.features,
                toml_dependency.default_features))

    return variants

def identify_dependencies(cargo_toml, cargo_lock, variant):
    lock_dependencies_by_name = {}
    for dependency in cargo_lock.dependencies:
        lock_dependencies_by_name[dependency.name] = dependency

    optional_dependencies = []
    used_features = list(variant.features)
    if variant.use_defaults:
        used_features.extend(cargo_toml.features.default_flags)
    for feature in used_features:
        new_dependencies = cargo_toml.features.flags_to_dependencies.get(feature)

        if new_dependencies is not None:
            optional_dependencies.extend(new_dependencies)

    selected_optional_dependencies = set(optional_dependencies)

    dependencies = []
    for toml_dependency in cargo_toml.dependencies:
        if not toml_dependency.optional or toml_dependency.name in selected_optional_dependencies:
            lock_dependency = lock_dependencies_by_name[toml_dependency.name]
            package_key = "{0}-{1}".format(toml_dependency.name, lock_dependency.version)
            dependencies.append("//third_party/cargo2bazel/internal/{0}/{1}:{2}".format(
                package_key,
                variant.get_key(),
                toml_dependency.name))
    return dependencies

class PackageVariant:
    def __init__(self, name, version, features, use_defaults=True):
        self.name = name
        self.version= version
        self.features = features
        self.use_defaults = use_defaults

    def get_key(self):
        key = "{0}".format(hash(str(self.features)))
        if self.use_defaults:
            key = "default+" + key
        return key

def add_build_rules(gen_root_internal, distinct_variants, dependency_toml_map, dependency_lock_map):
    grouped_variants = itertools.groupby(
            distinct_variants,
            lambda v: "{0}-{1}".format(v.name, v.version))
    for package_key, variants in grouped_variants:
        root_package_path = "{0}{1}/".format(
                gen_root_internal,
                package_key)
        variant_toml = dependency_toml_map[package_key]
        variant_lock = dependency_lock_map[package_key]
        default_features = variant_toml.features.default_flags

        for variant in variants:
            all_features = list(variant.features)
            all_dependencies = identify_dependencies(variant_toml, variant_lock, variant)

            variant_path = root_package_path + variant.get_key() + "/"
            if not os.path.exists(variant_path):
              os.makedirs(variant_path)

            build_file = open(variant_path + "/BUILD", 'w')
            build_file.write(build_file_template.format(
                variant.name,
                '[' + ', \n      '.join(map(lambda f: "\"{}\"".format(f), all_dependencies)) + ']',
                '[' + ', '.join(map(lambda f: "\"{}\"".format(f), all_features)) + ']'))
            build_file.close()

def add_aliases(gen_root, root_cargo_toml_dependencies, root_cargo_lock_dependencies):
    root_cargo_lock_dependency_map = {}
    for lock_dep in root_cargo_lock_dependencies:
        root_cargo_lock_dependency_map[lock_dep.name] = lock_dep

    for toml_dependency in root_cargo_toml_dependencies:
        lock_dependency = root_cargo_lock_dependency_map[toml_dependency.name]
        package_key = "{0}-{1}".format(toml_dependency.name, lock_dependency.version)
        variant_key = PackageVariant(
                toml_dependency.name,
                lock_dependency.version,
                toml_dependency.features,
                toml_dependency.default_features).get_key()
        target_path = "{0}{1}/{2}:{3}".format(
                gen_root,
                package_key,
                variant_key,
                toml_dependency.name)
        alias_file_path = '{0}{1}'.format(
                gen_root,
                package_key)
        if not os.path.exists(alias_file_path):
          os.makedirs(alias_file_path)
        build_file = open(alias_file_path + '/BUILD', 'w')
        build_file.write(alias_file_template.format(toml_dependency.name, target_path))
        build_file.close()


if __name__ == "__main__":
    main()
