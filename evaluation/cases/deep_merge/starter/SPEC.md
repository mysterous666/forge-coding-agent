# Deep merge

`deep_merge(base, override)` returns a new dictionary.

- When both values at a key are dictionaries, merge them recursively.
- Otherwise the override value replaces the base value, including `None` and lists.
- Keys present in only one input are preserved.
- Neither input nor any nested container reachable from it may be mutated or shared with the result.
