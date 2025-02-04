from typing import Any, Dict

from typing_extensions import Annotated

from litestar import Litestar, get
from litestar.params import Dependency


@get("/")
def hello_world(optional_dependency: Annotated[int, Dependency(default=3)]) -> Dict[str, Any]:
    """Notice we haven't provided the dependency to the route.

    This is OK, because of the default value, and now the parameter is excluded from the docs.
    """
    return {"hello": optional_dependency}


app = Litestar(route_handlers=[hello_world])
