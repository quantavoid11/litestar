import logging
from typing import Dict

from litestar import Litestar, Response, get
from litestar.background_tasks import BackgroundTask

logger = logging.getLogger(__name__)


async def logging_task(identifier: str, message: str) -> None:
    logger.info("%s: %s", identifier, message)


@get("/")
def greeter(name: str) -> Response[Dict[str, str]]:
    return Response(
        {"hello": name},
        background=BackgroundTask(logging_task, "greeter", message=f"was called with name {name}"),
    )


app = Litestar(route_handlers=[greeter])
