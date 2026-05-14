def strip_trailing_whitespace(text: str) -> str:
    """Strip trailing whitespace from every line, preserving indentation
    and the original line endings."""
    out_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        # Preserve the line ending; strip whitespace only on the content side.
        if line.endswith("\n"):
            content, eol = line[:-1], "\n"
        else:
            content, eol = line, ""
        # BUG: .strip() removes BOTH leading and trailing whitespace.
        out_lines.append(content.strip() + eol)
    return "".join(out_lines)
