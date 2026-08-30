# Safe path joining

`safe_join(root, user_path)` returns a resolved `Path` beneath `root`.

- Accept ordinary nested relative paths.
- Reject traversal outside the root.
- Reject absolute POSIX paths, Windows drive paths, and UNC paths on every host OS.
- Treat both `/` and `\` as separators regardless of the host OS.
- Raise `ValueError` for rejected paths.
