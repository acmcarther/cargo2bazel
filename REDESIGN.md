# Thoughts on some redesign

## Read each crate's Cargo.toml

Currently we don't identify the default flags from the Cargo.toml files, since we only use the root Cargo.lock to identify crates. We'll start reading that file for several reasons

### Identifying default flags for the crate
If we start reading each crate's Cargo.toml, we can support automatically generating default rules that contain the default flags. This will reduce the number of edge cases that next_space_coop has to deal with.

### Supporting alternate flag settings for dependencies
We can also start generating build rules for dependencies that have alternate flags settings. This capability will let us have more "correct" builds

### Omitting optional and dev dependencies
Currently the Cargo.lock file includes all possible dependencies. If we naively link to all of them, we may link to os-specific dependencies, or dev dependencies that are Cargo specific.


### Implementation strategy
I'm thinking a reimplementation of the current system would work something like the following:

- Use the Cargo.lock to identify all crates, and all interdependencies (Crate_X@1.0 -> Crate_Y@0.5)
- Use the Cargo.toml to generate the BUILD files for each crate. Use this opportunity to identify additional rules if a dependency needs, for example, a feature flag.

So each crate would get a build rule with the default flag values. Something of the form ${crate_name}_default. Next, we'd insert additional BUILD rules for feature combinations that other crates depend on -- hashing the alphabetized flag and appending it to name the build rule -- such as ${crate_name}_1852643589.


## Support overriding generated code in a deterministic way

I'm not sure exactly how I'd like this to look, but i've needed a good way to override codegen BUILD files since the beginning. Currently, I have to edit and remove build-dependencies and add default flags to make up for the above deficiencies, but I'm sure there are other usecases that won't be resolved even when the prior issues are addressed.
