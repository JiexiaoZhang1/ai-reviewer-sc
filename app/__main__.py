"""Entrypoint for running the API with `python -m app`."""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()

