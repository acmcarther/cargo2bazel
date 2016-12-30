import sys
from toml import toml
import urllib
import os
from wget import wget
import tarfile

alias_file_template = """\
# This is a direct dependency
# You've come to the right place!
package(default_visibility = ["//visibility:public"])

# TODO: we don't actually know this
licenses(["notice"])

alias(
  name = "{0}",
  actual = "//third_party/cargo2bazel/internal/{0}-{1}:{0}",
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
    "rust_binary",
    "rust_test",
    "rust_doc",
    "rust_doc_test",
)

# TODO: we don't actually know this
licenses(["notice"])

rust_library(
    name = "{0}",
    deps = {1},
    srcs = glob(["lib.rs", "src/**/*.rs"])
)
"""

def sanitize(s):
  return s.replace('-', '_')

def quoted(s):
  return '"{0}"'.format(s)

class Package:
  '''An extracted package from a Cargo.lock'''

  def __init__(self, name, source, version, dependencies):
    self.name = name
    self.source = source
    self.version = version
    self.dependencies = dependencies

  @staticmethod
  def from_config(config_package):
    name = config_package['name']
    source = config_package.get('source', None)
    version = config_package['version']
    raw_dependencies = config_package.get('dependencies', [])

    dependencies = list(map(Dependency.from_config, raw_dependencies))
    return Package(name, source, version, dependencies)

  def as_build_file(self):
    stringified_dependencies = ",\n    ".join(list(map(lambda dep: quoted(dep.as_package_name()), self.dependencies)))
    return build_file_template.format(
        sanitize(self.name),
        "[\n      {0}\n    ]".format(stringified_dependencies))

  def as_dependency(self):
    return Dependency(self.name, self.version, self.source);

class Dependency:
  '''A destructured dependency from a Cargo.lock'''

  def __init__(self, name, version, source=None):
    self.name = name
    self.version = version
    self.source = source

  @staticmethod
  def from_config(config_dependency):
    components = config_dependency.split()
    name = components[0]
    version = components[1]

    if len(config_dependency) == 3:
      source = components[2]
      return Dependency(name, version, source)
    else:
      return Dependency(name, version)

  def as_package_name(self):
    return "//third_party/cargo2bazel/internal/{0}-{1}:{2}".format(self.name, self.version, sanitize(self.name))

  def __key(self):
    # NOTE: Ignores the "source" key
    return (self.name, self.version)

  def __eq__(x, y):
    return x.__key() == y.__key()

  def __hash__(self):
    return hash(self.__key())

def main():
  if len(sys.argv) != 3:
    raise ValueError("Expected to recieve a cmdline arg of path to target Cargo.lock, and a path to place the dependencies")

  lock_file = sys.argv[1]
  output_path = sys.argv[2]
  with open(lock_file) as open_file:
    config = toml.loads(open_file.read())
    root = config['root']
    root_dependencies = list(map(Dependency.from_config, root.get('dependencies', [])))
    root_deps_hashset = set(map(lambda dep: dep.__hash__(), root_dependencies))
    packages = config['package']
    bazel_packages = list(map(Package.from_config, packages))
    remote_packages = list(filter(lambda pkg: pkg.source != None, bazel_packages))
    tar_dump_path = output_path + "/third_party/cargo2bazel/internal/"


    if not os.path.exists(tar_dump_path):
      os.makedirs(tar_dump_path)

    for package in remote_packages:
      url = "https://crates.io/api/v1/crates/{0}/{1}/download".format(
          package.name,
          package.version)
      tar_path = (tar_dump_path + "{0}-{1}.tar").format(package.name, package.version)
      if not os.path.exists(tar_path):
        wget.download(url, out=tar_path)

      expected_path = output_path + "/third_party/cargo2bazel/internal/{0}-{1}/".format(
        package.name,
        package.version)

      if not os.path.exists(expected_path):
        tar_file = tarfile.open(tar_path)
        tar_file.extractall(path=tar_dump_path)
        tar_file.close()
      build_file = open(expected_path + "BUILD", 'w')
      build_file.write(package.as_build_file())
      build_file.close()

      if package.as_dependency().__hash__() in root_deps_hashset:
        # We need to expose this pkg
        root_path = output_path + "/third_party/cargo2bazel/{0}/".format(package.name)
        if not os.path.exists(root_path):
          os.makedirs(root_path)
        build_file = open(root_path + "BUILD", 'w')
        build_file.write(alias_file_template.format(package.name, package.version))
        build_file.close()


if __name__ == "__main__":
  main()
