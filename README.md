# Cargo2Bazel Rules for Bazel
### WARNING: Not production ready! Use at your own peril!
### Seriously, there are no tests. At your own peril!

It is currently implemented as a python utility, instead of a ruleset because of limitations importing external python code into a build rule.

## Overview

These build rules are used for converting a set of dependencies generated by Rust's package manager, Cargo, into a set of third party dependencies.

## Usage

Create or bring in a `Cargo.toml` from another project and add your dependencies.

You'll need to specify the following section to trick cargo into resolving the dependencies:

```
[lib]
path = "some_path.rs"
```

For our example, we'll bring in regex, as so:
```toml
[package]
#...

[dependencies]
regex = "0.1.80"
```

When `cargo fetch` is run, cargo converts the toml into the following (approximate)`Cargo.lock`:
```toml
[root]
name = "test"
version = "0.1.0"
dependencies = [
 "regex 0.1.80 (registry+https://github.com/rust-lang/crates.io-index)",
]

[[package]]
name = "aho-corasick"
version = "0.5.3"
source = "registry+https://github.com/rust-lang/crates.io-index"
dependencies = [
 "memchr 0.1.11 (registry+https://github.com/rust-lang/crates.io-index)",
]

# ... many omitted

[[package]]
name = "regex"
version = "0.1.80"
source = "registry+https://github.com/rust-lang/crates.io-index"
dependencies = [
 "aho-corasick 0.5.3 (registry+https://github.com/rust-lang/crates.io-index)",
 "memchr 0.1.11 (registry+https://github.com/rust-lang/crates.io-index)",
 "regex-syntax 0.3.9 (registry+https://github.com/rust-lang/crates.io-index)",
 "thread_local 0.2.7 (registry+https://github.com/rust-lang/crates.io-index)",
 "utf8-ranges 0.1.3 (registry+https://github.com/rust-lang/crates.io-index)",
]
```

Cargo2Bazel provides a binary that can be used to read a Cargo.lock and produce a series of third-party libraries automatically. In a WORKSPACE add the following to bring in cargo2bazel. These are the cargo2bazel project, and its runtime dependencies

```python
git_repository(
    name = "io_bazel_cargo2bazel",
    remote = "https://github.com/acmcarther/cargo2bazel.git",
    commit = "723ce7b"
)

git_repository(
    name = "subpar",
    remote = "https://github.com/google/subpar",
    commit = "74529f1df2178f07d34c72b3d270355dab2a10fc",
)

new_git_repository(
    name = "toml",
    remote = "https://github.com/uiri/toml.git",
    tag = "0.9.2",
    build_file_content = """
package(default_visibility = ["//visibility:public"])

py_library(
  name = "toml",
  srcs = [
    "toml.py",
    "setup.py",
  ],
)""",
)

new_git_repository(
    name = "wget",
    remote = "https://github.com/steveeJ/python-wget.git",
    commit = "fdd3a0f8404ccab90f939f9952af139e6c55142a",
    build_file_content = """
package(default_visibility = ["//visibility:public"])

py_library(
  name = "wget",
  srcs = [
    "wget.py",
    "setup.py",
  ],
)""",
)

```

Now, in your console, execute:
```
bazel run @io_bazel_cargo2bazel//cargo2bazel $(pwd)/Cargo.lock $(pwd)
```

This will pull down your dependencies into "//third_party/cargo2bazel/". Our example, `regex`, would be available as "//third_party/cargo2bazel/regex".

## Still to do...
The ultimate aim of this project is to provide something akin to a `cargo_toml` rule that requires no external action or maintenance to use -- it just automatically pulls things down.
