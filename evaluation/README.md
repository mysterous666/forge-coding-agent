# Live coding benchmark

This benchmark evaluates Forge with small but nontrivial coding tasks. Each case has a `starter` directory sent to the agent and a separate `hidden` directory that must not be copied into the agent workspace.

Run each task in a fresh copy of its `starter` directory. After Forge finishes, run the visible `unittest` suite, then run the corresponding hidden test with the fresh workspace on `PYTHONPATH`. Compare the visible test file hashes before and after the run.

## 2026-08-27 result

Model: `gpt-5.6-sol` through an OpenAI-compatible API. Credentials were process-only and were not stored.

| Case | Capability | Visible | Hidden | Tests changed |
|---|---|---:|---:|---:|
| pricing | Decimal money, ordering, threshold boundaries | 2/2 | 4/4 | No |
| slugify | Unicode normalization and length boundaries | 2/2 | 4/4 | No |
| duration | Complete parsing and invalid-input rejection | 2/2 | 4/4 | No |
| deep_merge | Recursion, immutability, deep copies | 2/2 | 3/3 | No |
| safe_path | Windows/POSIX syntax and containment | 2/2 | 4/4 | No |

Total: 29/29 independent assertions passed across five tasks. The project regression suite also remained green at 12/12 tests.

The benchmark demonstrates reliable performance on well-specified, small-to-medium local changes. It does not establish performance on large repositories, long-horizon architectural changes, interactive processes, or underspecified product decisions.
