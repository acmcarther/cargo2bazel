load("@subpar//:subpar.bzl", "par_binary")

package(default_visibility = ["//visibility:public"])

par_binary(
    name = "cargo2bazel",
    deps = [
        "@toml//:toml",
        "@wget//:wget",
    ],
    srcs = ["cargo2bazel.py"]
)
