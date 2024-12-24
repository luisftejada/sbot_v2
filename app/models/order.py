import datetime
from decimal import Decimal
from typing import Any, Optional

from boto3.dynamodb.conditions import Key
from pydantic import BaseModel, PrivateAttr

from app.config.config import Config
from app.models.common import DbBaseModel, Index, IndexField, Record, parse_value
from app.models.enums import (
    BASIC_CURRENCIES,
    MarketOrderType,
    OrderStatus,
    OrderType,
    OrderTypeError,
)
from app.models.filled import Fill, fill_parser


class Order(Record):
    _KEY_FIELD: str = PrivateAttr(default="order_id")
    _TABLE_NAME: str = PrivateAttr(default="orders")
    _indexes: list[Index] = PrivateAttr(
        default=[
            Index(
                partition_key=IndexField(field_name="orderStatus", key_type="HASH"),
                sort_key=IndexField(field_name="executed", key_type="RANGE"),
            )
        ]
    )

    order_id: str
    created: datetime.datetime
    executed: Optional[datetime.datetime] = None
    type: OrderType
    buy_price: Optional[Decimal] = None
    sell_price: Optional[Decimal] = None
    orderStatus: OrderStatus
    amount: Decimal
    fills: list[Fill] = []
    benefit: Optional[Decimal] = None
    market: str  # Note market does not include /

    _currency_from: Optional[str] = PrivateAttr(default=None)
    _currency_to: Optional[str] = PrivateAttr(default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.executed is None:
            self.executed = self.created

    @classmethod
    def get_attribute(cls, field_name: str) -> str:
        match field_name:
            case "buy_price":
                return "N"
            case "sell_price":
                return "N"
            case "amount":
                return "N"
            case "fills":
                return "L"
            case "benefit":
                return "N"
            case _:
                return "S"

    @classmethod
    def create_from_db(cls, db_order: dict) -> "Order":
        try:
            # Return the populated Order instance with direct parsing and conversion
            return cls(
                order_id=parse_value(db_order, "order_id"),
                created=parse_value(db_order, "created", datetime.datetime),
                executed=parse_value(db_order, "executed", datetime.datetime, default=None),
                type=parse_value(db_order, "type", OrderType),
                buy_price=parse_value(db_order, "buy_price", Decimal, default=None),
                sell_price=parse_value(db_order, "sell_price", Decimal, default=None),
                orderStatus=parse_value(db_order, "orderStatus", OrderStatus),
                amount=parse_value(db_order, "amount", Decimal),
                fills=parse_value(db_order, "fills", fill_parser, default=[]),
                benefit=parse_value(db_order, "benefit", Decimal, default=None),
                market=parse_value(db_order, "market"),
            )
        except KeyError as e:
            raise cls.ParsingError(f"Missing required field in database record: {e}")
        except Exception as e:
            raise ValueError(f"Error creating Order from database record: {e}")

    @classmethod
    def create_from_coinex(cls, config: Config, coinex_data: Any, market: str | None = None) -> "Order":
        date = datetime.datetime.fromtimestamp(coinex_data.get("created_at") // 1000)
        order_type = OrderType.from_value(coinex_data.get("side"))
        _market = market if market is not None else config.market
        buy_price: Decimal | None = None
        sell_price: Decimal | None = None
        match order_type:
            case OrderType.BUY:
                buy_price = config.rnd_price(coinex_data.get("price"))
                sell_price = None
            case OrderType.SELL:
                sell_price = config.rnd_price(coinex_data.get("price"))
                buy_price = None
            case _:
                raise OrderTypeError(f"worng order type: {order_type}")

        obj = cls(
            order_id=str(coinex_data.get("order_id")),
            created=date,
            executed=date,
            type=order_type.value,
            buy_price=buy_price,
            sell_price=sell_price,
            orderStatus=OrderStatus.INITIAL,
            amount=config.rnd_amount(coinex_data.get("amount")),
            fills=[],
            benefit=None,
            market=_market,
        )
        return obj

    def _update_currencies(self) -> None:
        for currency in BASIC_CURRENCIES:
            if self.market.startswith(currency):
                self._currency_from = currency
                self._currency_to = self.market.replace(currency, "")
                return
        for currency in BASIC_CURRENCIES:
            if self.market.endswith(currency):
                self._currency_to = currency
                self._currency_from = self.market.replace(currency, "")
                return

    def currency_from(self) -> str | None:
        if self._currency_from is None:
            self._update_currencies()
        return self._currency_from

    def currency_to(self) -> str | None:
        if self._currency_to is None:
            self._update_currencies()
        return self._currency_to

    @classmethod
    def query_by_status(
        cls,
        bot: str,
        orderStatus: OrderStatus,
        from_date: Optional[datetime.datetime] = None,
        to_date: Optional[datetime.datetime] = None,
        limit: int | None = None,
        ascending: bool = True,
    ) -> list["Order"]:
        # Define the table name and index name
        table = cls._get_table(bot)
        index_name = "orderStatus_executed_index"

        filter_expression = Key("orderStatus").eq(orderStatus.value)
        if from_date is not None and to_date is not None:
            filter_expression &= Key("executed").between(from_date.isoformat(), to_date.isoformat())
        elif from_date is not None:
            filter_expression &= Key("executed").gte(from_date.isoformat())
        elif to_date is not None:
            filter_expression &= Key("executed").lt(to_date.isoformat())

        query_params = {
            "IndexName": index_name,
            "KeyConditionExpression": filter_expression,
            "ScanIndexForward": ascending,
        }
        if limit is not None:
            query_params["Limit"] = limit
        response = table.query(**query_params)
        # Convert response items into Order instances
        data = [cls.create_from_db(item) for item in response.get("Items", [])]
        return data

    @classmethod
    def query_first_by_status(
        cls,
        bot: str,
        orderStatus: OrderStatus,
        from_date: Optional[datetime.datetime] = None,
        to_date: Optional[datetime.datetime] = None,
        ascending: bool = True,
    ) -> Optional["Order"]:
        orders = cls.query_by_status(bot, orderStatus, from_date, to_date, limit=1, ascending=ascending)
        return orders[0] if orders else None

    def executed_day(self):
        return datetime.datetime(year=self.executed.year, month=self.executed.month, day=self.executed.day)


class ExecutedOrder(DbBaseModel):
    order_id: str
    executed: datetime.datetime
    type: MarketOrderType
    buy_price: Optional[Decimal] = None
    sell_price: Optional[Decimal] = None
    amount: Decimal
    benefit: Optional[Decimal] = None
    market: str  # Note market does not include /

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.ParsingError = Order.ParsingError

    @classmethod
    def create_from_db(cls, data: dict) -> "ExecutedOrder":
        try:
            return cls(
                order_id=parse_value(data, "order_id"),
                executed=parse_value(data, "executed", datetime.datetime),
                type=parse_value(data, "type", MarketOrderType),
                buy_price=parse_value(data, "buy_price", Decimal, default=None),
                sell_price=parse_value(data, "sell_price", Decimal, default=None),
                amount=parse_value(data, "amount", Decimal),
                benefit=parse_value(data, "benefit", Decimal, default=None),
                market=parse_value(data, "market"),
            )
        except KeyError as e:
            raise cls.ParsingError(f"Missing required field in database record: {e}")
        except Exception as e:
            raise ValueError(f"Error creating Order from database record: {e}")

    @classmethod
    def create_from_order(cls, order: Order, order_type: MarketOrderType | OrderType) -> "ExecutedOrder":
        return cls(
            order_id=order.order_id,
            executed=order.executed,
            type=order_type,
            buy_price=order.buy_price,
            sell_price=order.sell_price,
            amount=order.amount,
            benefit=order.benefit,
            market=order.market,
        )


def market_orders_parser(value) -> list[ExecutedOrder]:
    orders = [ExecutedOrder.create_from_db(order) for order in value]
    return orders


class DbExecuted(Record):
    _KEY_FIELD: str = PrivateAttr(default="date")
    _TABLE_NAME: str = PrivateAttr(default="executed")
    _indexes: list[Index] = PrivateAttr(
        default=[
            Index(
                partition_key=IndexField(field_name="day", key_type="HASH"),
                sort_key=IndexField(field_name="date", key_type="RANGE"),
            )
        ]
    )

    date: datetime.datetime
    day: datetime.datetime
    orders: list[ExecutedOrder]

    _page_size: Optional[int] = PrivateAttr(default=1000)

    def __init__(self, *args, **kwargs):
        private_value = kwargs.pop("_page_size", None)
        super().__init__(*args, **kwargs)
        self._page_size = private_value if private_value else self._page_size

    @classmethod
    def get_attribute(cls, field_name):
        match field_name:
            case "date", "day":
                return "S"
            case "orders":
                return "L"
            case _:
                return "S"

    @classmethod
    def create_from_db(cls, data: dict) -> "DbExecuted":
        executed = cls(
            date=parse_value(data, "date", datetime.datetime),
            day=parse_value(data, "day", datetime.datetime),
            orders=sorted(
                parse_value(data, "orders", market_orders_parser, default=[]), key=lambda order: order.executed
            ),
        )
        return executed

    def is_full(self) -> bool:
        return len(self.orders) >= self._page_size if self._page_size else False

    def add_order(self, order: Order, order_type: MarketOrderType | OrderType) -> ExecutedOrder:
        executed_order = ExecutedOrder.create_from_order(order, order_type)
        self.orders.append(executed_order)
        return executed_order

    @classmethod
    def query_by_day(cls, bot: str, day: datetime.datetime) -> list["DbExecuted"]:
        table = cls._get_table(bot)
        filter_expression = Key("day").eq(day.isoformat())
        query_params = {
            "IndexName": "day_date_index",
            "KeyConditionExpression": filter_expression,
            "ScanIndexForward": True,
        }
        response = table.query(**query_params)
        data = [cls.create_from_db(item) for item in response.get("Items", [])]
        return data


class Executed(BaseModel):
    date: datetime.datetime
    pages: list[DbExecuted] = []
    bot: str

    _page_size: Optional[int] = PrivateAttr(default=1000)

    @property
    def current_page(self) -> DbExecuted:
        return self.pages[-1]

    @property
    def current_date(self) -> datetime.datetime:
        return self.current_page.date

    @property
    def current_day(self) -> datetime.datetime:
        return self.current_page.day

    @classmethod
    def load_day(cls, bot: str, day: datetime.datetime) -> "Executed":
        new_executed = cls(bot=bot, date=day, pages=[])
        new_executed.load()
        return new_executed

    def __init__(self, *args, **kwargs):
        private_value = kwargs.pop("_page_size", None)
        super().__init__(*args, **kwargs)
        self._page_size = private_value if private_value else self._page_size

    def add_executed_order(self, order: Order, order_type: MarketOrderType | OrderType) -> ExecutedOrder:
        if len(self.pages) == 0:
            self.load()
        if self.current_page.is_full():
            DbExecuted.save(self.bot, self.current_page)
            self.add_page()
        return self.current_page.add_order(order=order, order_type=order_type)

    def add_page(self):
        self.pages.append(
            DbExecuted(
                day=self.current_day,
                date=self.current_date + datetime.timedelta(minutes=1),
                orders=[],
                _page_size=self._page_size,
            )
        )

    def load(self) -> None:
        from_date = self.date
        filter_expression = Key("day").eq(from_date.isoformat())
        query_params = {
            "IndexName": "day_date_index",
            "KeyConditionExpression": filter_expression,
            "ScanIndexForward": True,
        }
        table = DbExecuted._get_table(self.bot)
        response = table.query(**query_params)
        self.pages = [DbExecuted.create_from_db(item) for item in response.get("Items", [])]
        if len(self.pages) == 0:
            self.pages = [DbExecuted(date=self.date, day=self.date, orders=[], _page_size=self._page_size)]

    @classmethod
    def query_by_day(cls, bot: str, day: datetime.datetime) -> list[ExecutedOrder]:
        data = DbExecuted.query_by_day(bot, day)
        orders = []
        for page in data:
            orders.extend(page.orders)
        return orders

    def save(self):
        if len(self.pages) > 0:
            DbExecuted.save(self.bot, self.current_page)
