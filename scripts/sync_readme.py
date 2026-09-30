"""Copy docs/findings.md into README.md between the FINDINGS markers (F10: "copied automatically")."""

import re
from pathlib import Path

START, END = "<!-- FINDINGS:START -->", "<!-- FINDINGS:END -->"


def main() -> None:
    findings = Path("docs/findings.md").read_text(encoding="utf-8")
    body = findings.split("\n## ", 1)[1]  # drop title + preamble, keep numbered sections
    body = "## " + body
    body = re.sub(r"^## ", "#### ", body, flags=re.MULTILINE)
    readme = Path("README.md").read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(readme):
        raise SystemExit("FINDINGS markers not found in README.md")
    block = f"{START}\n\n{body.strip()}\n\n{END}"
    Path("README.md").write_text(pattern.sub(lambda _: block, readme), encoding="utf-8")
    print("README.md findings synced from docs/findings.md")


if __name__ == "__main__":
    main()
