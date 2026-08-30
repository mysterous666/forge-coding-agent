# Demo Project — string_utils

A 2-file, 2-bug example for recording the Forge Agent demo.

## Layout

- `string_utils.py` — utility module with **two bugs**
- `test_string_utils.py` — unittest suite (do NOT edit during the demo)

## The bugs

1. **`reverse_string`** — uses `text[::1]` (returns the string unchanged) instead of `text[::-1]`.
   - Failing test: `test_reverse_string` expects `reverse_string("hello") == "olleh"`.

2. **`count_vowels`** — only counts lowercase vowels, so uppercase ones are missed.
   - Failing test: `test_count_vowels_uppercase` expects `count_vowels("Apple") == 2`.

`capitalize_words` is correct on purpose — the agent must not touch it.

## Run the tests

```bash
python -m unittest -q
```

Expected before the fix: `FAILED (failures=2)` — 2 failed, 3 passed.
Expected after the fix: `OK` — 5 passed.

## Suggested demo task

> 修复当前项目中的失败测试：先运行测试定位失败，阅读源码，修复实现但不要修改试文件，然后重新运行全部测试确认 100% 通过，最后总结改了什么。

## Expected timeline

```
list_files → run_command (2 failed, red)
→ read_file(string_utils.py)
→ replace_text (Diff: reverse_string)
→ run_command (1 failed)
→ replace_text (Diff: count_vowels)
→ run_command (all passed, green)
→ Task Completed
```