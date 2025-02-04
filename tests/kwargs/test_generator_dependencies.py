from typing import AsyncGenerator, Callable, Dict, Generator
from unittest.mock import MagicMock

import pytest
from pytest import FixtureRequest

from litestar import WebSocket, get, websocket
from litestar.di import Provide
from litestar.testing import create_test_client


@pytest.fixture
def cleanup_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def exception_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def finally_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def generator_dependency(
    cleanup_mock: MagicMock, exception_mock: MagicMock, finally_mock: MagicMock
) -> Callable[[], Generator[str, None, None]]:
    def dependency() -> Generator[str, None, None]:
        try:
            yield "hello"
            cleanup_mock()
        except ValueError:
            exception_mock()
        finally:
            finally_mock()

    return dependency


@pytest.fixture
def async_generator_dependency(
    cleanup_mock: MagicMock, exception_mock: MagicMock, finally_mock: MagicMock
) -> Callable[[], AsyncGenerator[str, None]]:
    async def dependency() -> AsyncGenerator[str, None]:
        try:
            yield "hello"
            cleanup_mock()
        except ValueError:
            exception_mock()
        finally:
            finally_mock()

    return dependency


@pytest.mark.parametrize("cache", [False, True])
@pytest.mark.parametrize("dependency_fixture", ["generator_dependency", "async_generator_dependency"])
def test_generator_dependency(
    cache: bool,
    request: FixtureRequest,
    dependency_fixture: str,
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = request.getfixturevalue(dependency_fixture)

    @get("/", dependencies={"dep": Provide(dependency)}, cache=cache)
    def handler(dep: str) -> Dict[str, str]:
        return {"value": dep}

    with create_test_client(route_handlers=[handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"value": "hello"}
        cleanup_mock.assert_called_once()
        finally_mock.assert_called_once()
        exception_mock.assert_not_called()


@pytest.mark.parametrize("dependency_fixture", ["generator_dependency", "async_generator_dependency"])
async def test_generator_dependency_websocket(
    request: FixtureRequest,
    dependency_fixture: str,
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = request.getfixturevalue(dependency_fixture)

    @websocket("/ws", dependencies={"dep": Provide(dependency)})
    async def ws_handler(socket: WebSocket, dep: str) -> None:
        await socket.accept()
        await socket.send_json({"value": dep})
        await socket.close()

    with create_test_client(route_handlers=[ws_handler]) as client, client.websocket_connect("/ws") as ws:
        assert ws.receive_json() == {"value": "hello"}
    cleanup_mock.assert_called_once()
    finally_mock.assert_called_once()
    exception_mock.assert_not_called()


@pytest.mark.parametrize("dependency_fixture", ["generator_dependency", "async_generator_dependency"])
def test_generator_dependency_handle_exception(
    request: FixtureRequest,
    dependency_fixture: str,
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = request.getfixturevalue(dependency_fixture)

    @get("/", dependencies={"dep": Provide(dependency)})
    def handler(dep: str) -> Dict[str, str]:
        raise ValueError("foo")

    with create_test_client(route_handlers=[handler]) as client:
        res = client.get("/")
        assert res.status_code == 500
        assert res.json() == {"detail": "ValueError('foo')", "status_code": 500}
        cleanup_mock.assert_not_called()
        exception_mock.assert_called_once()
        finally_mock.assert_called_once()


@pytest.mark.parametrize("dependency_fixture", ["generator_dependency", "async_generator_dependency"])
def test_generator_dependency_exception_during_cleanup(
    request: FixtureRequest,
    dependency_fixture: str,
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = request.getfixturevalue(dependency_fixture)
    cleanup_mock.side_effect = Exception("foo")

    @get("/", dependencies={"dep": Provide(dependency)})
    def handler(dep: str) -> Dict[str, str]:
        return {"value": dep}

    with create_test_client(route_handlers=[handler]) as client:
        res = client.get("/")
        assert res.status_code == 500
        assert res.json() == {"status_code": 500, "detail": "Exception('foo')"}
        cleanup_mock.assert_called_once()
        finally_mock.assert_called_once()


@pytest.mark.parametrize("dependency_fixture", ["generator_dependency", "async_generator_dependency"])
def test_generator_dependency_nested(
    request: FixtureRequest,
    dependency_fixture: str,
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = request.getfixturevalue(dependency_fixture)

    async def nested_dependency_one(generator_dep: str) -> str:
        return generator_dep

    async def nested_dependency_two(generator_dep: str, nested_one: str) -> str:
        return generator_dep + nested_one

    @get(
        "/",
        dependencies={
            "generator_dep": Provide(dependency),
            "nested_one": Provide(nested_dependency_one),
            "nested_two": Provide(nested_dependency_two),
        },
    )
    def handler(nested_two: str) -> Dict[str, str]:
        return {"value": nested_two}

    with create_test_client(route_handlers=[handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"value": "hellohello"}
        cleanup_mock.assert_called_once()
        finally_mock.assert_called_once()
        exception_mock.assert_not_called()


@pytest.mark.parametrize("dependency_fixture", ["generator_dependency", "async_generator_dependency"])
def test_generator_dependency_nested_error_during_cleanup(
    request: FixtureRequest,
    dependency_fixture: str,
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = request.getfixturevalue(dependency_fixture)
    cleanup_mock_no_raise = MagicMock()
    cleanup_mock.side_effect = ValueError()

    async def other_dependency(generator_dep: str) -> AsyncGenerator[str, None]:
        try:
            yield generator_dep + ", world"
        finally:
            cleanup_mock_no_raise()

    @get(
        "/",
        dependencies={
            "generator_dep": Provide(dependency),
            "other": Provide(other_dependency),
        },
    )
    def handler(other: str) -> Dict[str, str]:
        return {"value": other}

    with create_test_client(route_handlers=[handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"value": "hello, world"}
        cleanup_mock.assert_called_once()
        finally_mock.assert_called_once()
        exception_mock.assert_called_once()
        cleanup_mock_no_raise.assert_called_once()
