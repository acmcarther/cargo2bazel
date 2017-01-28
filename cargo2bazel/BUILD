load("@subpar//:subpar.bzl", "par_binary")

package(default_visibility = ["//visibility:public"])

par_binary(
    name = "cargo2bazel",
    deps = [
        "@toml//:toml",
        "@wget//:wget",
        ":cargo_toml",
    ],
    srcs = ["cargo2bazel.py"],
)

par_binary(
    name = "cargo_toml",
    deps = [
        "@toml//:toml",
    ],
    srcs = ["cargo_toml.py"]
)
