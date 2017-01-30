import sys
from toml import toml
from warnings import warn

# An ugly hack to work around the inability to parse or handle [target.*.dependencies] config
BANNED_TARGET_DEPENDENCIES = ["redox_syscall"]

class CargoLock:
    def __init__(self, loaded_toml):
        self.root = CargoLock_Package(loaded_toml['root'])
        self.packages = []
        if 'package' in loaded_toml:
            self.packages = map(CargoLock_Package, loaded_toml['package'])

class CargoLock_Package:
    def __init__(self, loaded_toml):
        self.name = loaded_toml['name']
        self.version = loaded_toml['version']
        self.source = loaded_toml.get('source')
        self.dependencies = []
        if 'dependencies' in loaded_toml:
            self.dependencies = map(CargoLock_Dependency, loaded_toml['dependencies'])

class CargoLock_Dependency:
    def __init__(self, dependency_string):
        components = dependency_string.split()
        self.name = components[0]
        self.version = components[1]
        self.source = None

        if len(dependency_string) == 3:
            self.source = components[2]

class CargoToml:
    def __init__(self, loaded_toml):
        self.package = CargoToml_Package(loaded_toml['package'])
        self.features = CargoToml_Features({})
        self.dependencies = []
        self.target = []

        if 'features' in loaded_toml:
            self.features = CargoToml_Features(loaded_toml['features'])

        if 'dependencies' in loaded_toml:
            self.dependencies = map(CargoToml_Dependency, loaded_toml['dependencies'].iteritems())

        if 'target' in loaded_toml:
            all_deps_for_all_targets = []
            for deps in loaded_toml['target'].values():
                all_deps_for_all_targets.extend(deps['dependencies'].iteritems())

            deduped_all_deps_for_all_targets = set(all_deps_for_all_targets)
            deduped_all_deps_for_all_targets = filter(lambda dep: dep[0] not in BANNED_TARGET_DEPENDENCIES, deduped_all_deps_for_all_targets)
            self.dependencies.extend(map(CargoToml_Dependency, list(deduped_all_deps_for_all_targets)))



class CargoToml_Package:
    def __init__(self, loaded_toml):
        self.name = loaded_toml['name']
        self.version = loaded_toml['version']
        self.authors = loaded_toml.get('authors')
        self.license = loaded_toml.get('license')

        if 'workspace' in loaded_toml:
            warn("{0}-{1} may not compile correctly because it uses the Cargo \
                    workspaces feature".format(self.name, self.version))

        if 'replace' in loaded_toml:
            warn("{0}-{1} may not compile correctly because it uses the Cargo \
                    replace feature".format(self.name, self.version))

        if 'lib' in loaded_toml:
            warn("lib property is being ignored in {0}-{1}".format(self.name, self.version))

class CargoToml_Features:
    def __init__(self, loaded_toml):
        self.default_flags = []
        if 'default' in loaded_toml:
            self.default_flags = loaded_toml['default']
        self.flags_to_dependencies = dict(filter(lambda x: (x[0] != 'default'), loaded_toml.iteritems()))

class CargoToml_Dependency:
    def __init__(self, kv_pair):
        self.name = kv_pair[0]
        self.optional = False
        self.default_features = True
        self.features = []

        if isinstance(kv_pair[1], basestring):
            self.version_spec = kv_pair[1]
        else:
            props = kv_pair[1]
            assert isinstance(props, dict), "could not parse properties for \
                    dependency {0}".format(self.name)
            self.version_spec = props.get('version')

            if 'optional' in props:
                self.optional = props['optional']

            if 'default-features' in props:
                self.default_features = props['default-features']

            if 'features' in props:
                self.features = props['features']

def main():
    assert len(sys.argv) is 2, "expected to receive an argument"
    file_path = sys.argv[1]
    loader = None
    if file_path.endswith("toml"):
       loader = CargoToml
    elif file_path.endswith("lock"):
       loader = CargoLock

    with open(file_path) as open_file:
        print(repr(loader(toml.loads(open_file.read()))))


if __name__ == "__main__":
  main()
