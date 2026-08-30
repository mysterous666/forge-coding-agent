# Duration parser

`parse_duration(text)` returns a total number of seconds.

- Supported units are `d`, `h`, `m`, and `s`, in any order.
- Spaces are optional between components.
- Each unit may appear at most once.
- Values are non-negative integers.
- The complete non-whitespace input must consist of valid components.
- Empty input, repeated units, unsupported units, negative values, and trailing junk raise `ValueError`.
