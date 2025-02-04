from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel

from litestar import Litestar, get


class Order(BaseModel):
    id: int
    customer_id: int


ORDERS_BY_DATETIME = {
    datetime.fromtimestamp(1667924386, tz=timezone.utc): [
        Order(id=1, customer_id=2),
        Order(id=2, customer_id=2),
    ]
}


@get(path="/orders/{from_date:int}")
def get_orders(from_date: datetime) -> List[Order]:
    return ORDERS_BY_DATETIME[from_date]


app = Litestar(route_handlers=[get_orders])
