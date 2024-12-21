import datetime
import decimal
import json
from typing import Any, Literal, Optional

from boto3.dynamodb.table import TableResource as Table
from pydantic import BaseModel, PrivateAttr

from app.config.dynamodb import get_dynamodb


def parse_value(db_record: dict, key: str, cls: Any = str, default: Any = None) -> Any:
    """
    Parse a value from a database record, converting it to the specified type.

    Args:
        db_record (dict): The database record to parse.
        key (str): The key to look for in the record.
        cls (type): The type to convert the value to (default: str).
        default (Any): The default value to return if the key is not in the record.

    Returns:
        Any: The parsed value, converted to the specified type, or the default value.
    """
    if key not in db_record or db_record[key] is None:
        return default

    value = db_record[key]
    match cls:
        case datetime.datetime:
            return datetime.datetime.fromisoformat(value)
        case decimal.Decimal:
            return decimal.Decimal(value)
        case _:
            return cls(value)


class IndexField(BaseModel):
    field_name: str
    key_type: Literal["HASH", "RANGE"]


class Index(BaseModel):
    partition_key: IndexField
    sort_key: IndexField
    projection: Literal["ALL", "KEYS_ONLY", "INCLUDE"] = "ALL"


class Record(BaseModel):
    class NotFoundError(Exception):
        pass

    class ParsingError(Exception):
        pass

    _KEY_FIELD: str = PrivateAttr(default="id")
    _TABLE_NAME: str = PrivateAttr(default="table")

    _table: Optional[Table] = PrivateAttr(default=None)
    _indexes: list[Index] = PrivateAttr(default=[])

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._table = None

    @classmethod
    def key_field(cls):
        return cls._KEY_FIELD.get_default()

    @classmethod
    def table_name(cls):
        return cls._TABLE_NAME.get_default()

    @classmethod
    def get_full_table_name(cls, bot: str):
        return f"{bot}_{cls.table_name()}"

    @classmethod
    def indexes(cls):
        return cls._indexes.get_default()

    def get_id(self) -> str:
        return getattr(self, self._KEY_FIELD)

    @classmethod
    def get_fields(cls) -> dict:
        fields = {}
        for field_name, field_info in cls.model_fields.items():
            fields[field_name] = field_info.type_
        return fields

    @classmethod
    def get_attribute(cls, field_name: str) -> str:
        return "S"

    @classmethod
    def get_attribute_definitions(cls):
        attributes = set()
        attributes.add(cls.key_field())
        for index in cls.indexes():
            attributes.add(index.partition_key.field_name)
            attributes.add(index.sort_key.field_name)

        attribute_definitions = []
        for field_name in cls.model_fields.keys():
            if field_name in attributes:
                attribute_definitions.append(
                    {"AttributeName": field_name, "AttributeType": cls.get_attribute(field_name)}
                )
        return attribute_definitions

    @classmethod
    def get_index_definitions(cls):
        indexes = []
        for index in cls.indexes():
            index_definitions = {}
            index_definitions["IndexName"] = f"{index.partition_key.field_name}_{index.sort_key.field_name}_index"
            index_definitions["KeySchema"] = [
                {
                    "AttributeName": index.partition_key.field_name,
                    "KeyType": index.partition_key.key_type,
                },
                {
                    "AttributeName": index.sort_key.field_name,
                    "KeyType": index.sort_key.key_type,
                },
            ]
            index_definitions["Projection"] = {"ProjectionType": index.projection}
            indexes.append(index_definitions)
        return indexes

    @classmethod
    def create_table(cls, bot: str) -> None:
        table_name = cls.get_full_table_name(bot)
        if table_name not in get_dynamodb().meta.client.list_tables().get("TableNames"):
            create_table_arguments = {
                "TableName": table_name,
                "KeySchema": [
                    {
                        "AttributeName": cls.key_field(),
                        "KeyType": "HASH",
                    },
                ],
                "AttributeDefinitions": cls.get_attribute_definitions(),
                "BillingMode": "PAY_PER_REQUEST",
            }
            index_definitions = cls.get_index_definitions()
            if index_definitions:
                create_table_arguments["GlobalSecondaryIndexes"] = index_definitions
            table = get_dynamodb().create_table(**create_table_arguments)
            table.meta.client.get_waiter("table_exists").wait(TableName=table_name)

    @classmethod
    def delete_table(cls, bot: str) -> None:
        table_name = cls.get_full_table_name(bot)
        if table_name in get_dynamodb().meta.client.list_tables().get("TableNames"):
            table = get_dynamodb().Table(table_name)
            table.delete()
            table.meta.client.get_waiter("table_not_exists").wait(TableName=table_name)

    @classmethod
    def _get_table(cls, bot: str) -> Table:
        table_name = cls.get_full_table_name(bot)
        if cls._table is None:
            cls._table = get_dynamodb().Table(table_name)
        return cls._table

    @classmethod
    def get(cls, bot: str, id: str, raise_not_found: bool = False) -> Optional["Record"]:
        table = cls._get_table(bot)
        response = table.get_item(Key={cls.key_field(): id})
        if "Item" not in response:
            if raise_not_found:
                raise cls.NotFoundError(
                    f"{cls.__name__} with {cls.key_field()} {id} not found in the database."  # noqa: E713
                )
            else:
                return None
        return cls.create_from_db(response["Item"])

    @classmethod
    def save(cls, bot: str, record: "Record") -> None:
        table = cls._get_table(bot)
        item = json.loads(record.model_dump_json())

        # Remove None fields to avoid saving them to DynamoDB
        item = {k: v for k, v in item.items() if v is not None}
        try:
            # Put the item into the DynamoDB table
            table.put_item(Item=item)
            print(f"{cls.__name__} {record.get_id()} saved successfully to DynamoDB.")
        except Exception as e:
            raise RuntimeError(f"Failed to save {cls.__name__} {record.get_id()} to DynamoDB: {e}")

    @classmethod
    def delete(cls, bot: str, id: str) -> None:
        table = cls._get_table(bot)
        try:
            # Delete the item from the DynamoDB table
            table.delete_item(Key={cls.key_field(): id})
            print(f"{cls.__name__} {id} deleted successfully from DynamoDB.")
        except Exception as e:
            raise RuntimeError(f"Failed to delete {cls.__name__} {id} from DynamoDB: {e}")

    @classmethod
    def update(cls, bot: str, record: "Record") -> None:
        table = cls._get_table(bot)
        item = record.model_dump()

        update_expression_parts = []
        remove_expression_parts = []
        expression_values = {}

        for key, value in item.items():
            if value is None:
                remove_expression_parts.append(key)
            else:
                update_expression_parts.append(f"{key} = :{key}")
                expression_values[f":{key}"] = value

        update_expression = "SET " + ", ".join(update_expression_parts) if update_expression_parts else ""
        remove_expression = "REMOVE " + ", ".join(remove_expression_parts) if remove_expression_parts else ""

        final_update_expression = " ".join(filter(None, [update_expression, remove_expression]))

        if not final_update_expression:
            raise ValueError("No fields to update or remove")

        try:
            # Update the item in DynamoDB
            table.update_item(
                Key={cls.key_field(): record.get_id()},
                UpdateExpression=final_update_expression,
                ExpressionAttributeValues=expression_values or None,
            )

            print(
                f"{cls.__name__} {record.get_id()} updated successfully in DynamoDB. update_expression: {final_update_expression}"
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to update {cls.__name__} {record.get_id()} update_expression: {final_update_expression} error={e}"
            )
