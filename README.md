# Cargo2Bazel Rules for Bazel

Note: This ruleset is currently a work in progress and may be incomplete.

The current README is speculative.

## Overview

These build rules are used for converting a set of dependencies generated by Rust's package manager, Cargo, into a set of third party dependencies using Bazel's [Repository Rules](https://www.bazel.io/versions/master/docs/skylark/repository_rules.html) feature.

## Example

Suppose you have a `Cargo.toml` matching the following:

```toml
[package]
#...

[dependencies]
regex = "0.4.16"
```

which cargo converts into the following (approximate)`Cargo.lock`:
```toml
[root]
#...

# Many omitted

[[package]]
name = "regex"
version = "0.1.73"
source = "registry+https://github.com/rust-lang/crates.io-index"
dependencies = [
 "aho-corasick 0.5.2 (registry+https://github.com/rust-lang/crates.io-index)",
 "memchr 0.1.11 (registry+https://github.com/rust-lang/crates.io-index)",
 "regex-syntax 0.3.4 (registry+https://github.com/rust-lang/crates.io-index)",
 "thread_local 0.2.6 (registry+https://github.com/rust-lang/crates.io-index)",
 "utf8-ranges 0.1.3 (registry+https://github.com/rust-lang/crates.io-index)",
]

[[package]]
name = "regex-syntax"
version = "0.3.4"
source = "registry+https://github.com/rust-lang/crates.io-index"

[[package]]
name = "rustc-serialize"
version = "0.3.19"
source = "registry+https://github.com/rust-lang/crates.io-index"
```

Cargo2Bazel provides a repository rule that can be used to read a Cargo.lock and produce a series of third-party libraries automatically. In a WORKSPACE:

```python
cargo2bazel(
    name = "my_toml",
    lock_file = "./Cargo.lock",
)
```

After adding a cargo2bazel rule into your WORKSPACE folder, you can access declared dependencies in your workspace.

```python
rust_library(
    name = "foo",
    deps = [
      "@cargo2bazel//my_toml:regex",
    ],
)
```

# Caveats

You *only* have access to explicit dependencies -- not any transitive dependencies.