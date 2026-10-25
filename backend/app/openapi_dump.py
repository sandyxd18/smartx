"""Print the OpenAPI schema as JSON. Used by `npm run gen:api` in frontend/.

Usage: uv run python -m app.openapi_dump > openapi.json
"""

import json
import sys

from app.main import create_app


def main() -> None:
    schema = create_app().openapi()
    # Write bytes: the Windows console encoding cannot represent every character.
    sys.stdout.buffer.write(json.dumps(schema, indent=2, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
