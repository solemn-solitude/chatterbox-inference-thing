1. When writing print statements, if you need to create multiple lines, prefer multiline strings with dedent from textwrap instead of multiple print statements.

2. Do not write arbitrary comments.

3. Prefer union types instead of types from typing. After 3.10, many use cases of the typing package has been replaced. So prefer union types over optionals, e.g. str | None over Optional[str], etc. Other redundant types would be Union, List, Dict which also have native support now.

4. Do NOT use imports inside functions or classes unless there's a very good reason to do so. A good reason would be if the dependency is optional and there needs to be a check. A bad reason is laziness.