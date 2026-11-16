from __future__ import annotations

import uvicorn

from noc import config


def main() -> None:
    uvicorn.run("noc.app:app", host=config.HOST, port=config.PORT, reload=False, access_log=False)


if __name__ == "__main__":
    main()
