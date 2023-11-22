import json
import logging
import os
from datetime import datetime
from decimal import Decimal as decimal
from functools import wraps

import boto3
from app.repositories.common import (
    TABLE_NAME,
    TRANSACTION_BATCH_SIZE,
    RecordNotFoundError,
    _compose_bot_id,
    _compose_conv_id,
    _decompose_conv_id,
    _get_dynamodb_client,
    _get_table_client,
)
from app.repositories.model import (
    ContentModel,
    ConversationMeta,
    ConversationModel,
    MessageModel,
)
from app.utils import get_current_time
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
sts_client = boto3.client("sts")


def store_conversation(user_id: str, conversation: ConversationModel):
    logger.debug(f"Storing conversation: {conversation.model_dump_json()}")
    client = _get_dynamodb_client(user_id)

    transact_items = [
        {
            "Put": {
                "TableName": TABLE_NAME,
                "Item": {
                    "PK": user_id,
                    "SK": _compose_conv_id(user_id, conversation.id),
                    "Title": conversation.title,
                    "CreateTime": decimal(conversation.create_time),
                    "MessageMap": json.dumps(
                        {k: v.model_dump() for k, v in conversation.message_map.items()}
                    ),
                    "LastMessageId": conversation.last_message_id,
                    "BotId": conversation.bot_id,
                },
            }
        },
    ]
    # TODO
    if conversation.bot_id:
        transact_items.append(
            # Update `LastBotUsed`
            {
                "Update": {
                    "TableName": TABLE_NAME,
                    "Key": {
                        "PK": user_id,
                        "SK": _compose_bot_id(user_id, conversation.bot_id),
                    },
                    "UpdateExpression": "set LastBotUsed = :current_time",
                    "ExpressionAttributeValues": {
                        ":current_time": decimal(get_current_time())
                    },
                }
            },
        )

    response = client.transact_write_items(TransactItems=transact_items)
    return response


def find_conversation_by_user_id(user_id: str) -> list[ConversationMeta]:
    logger.debug(f"Finding conversations for user: {user_id}")
    table = _get_table_client(user_id)

    query_params = {
        "KeyConditionExpression": Key("PK").eq(user_id)
        # NOTE: Need SK to fetch only conversations
        & Key("SK").begins_with(f"{user_id}#CONV#"),
        "ScanIndexForward": False,
    }

    response = table.query(**query_params)
    conversations = [
        ConversationMeta(
            id=_decompose_conv_id(item["SK"]),
            create_time=float(item["CreateTime"]),
            title=item["Title"],
            # NOTE: all message has the same model
            model=json.loads(item["MessageMap"]).popitem()[1]["model"],
            bot_id=item["BotId"],
        )
        for item in response["Items"]
    ]

    query_count = 1
    MAX_QUERY_COUNT = 5
    while "LastEvaluatedKey" in response:
        model = json.loads(response["Items"][0]["MessageMap"]).popitem()[1]["model"]
        query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        # NOTE: max page size is 1MB
        # See: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.Pagination.html
        response = table.query(
            **query_params,
        )
        conversations.extend(
            [
                ConversationMeta(
                    id=_decompose_conv_id(item["SK"]),
                    create_time=float(item["CreateTime"]),
                    title=item["Title"],
                    model=model,
                    bot_id=item["BotId"],
                )
                for item in response["Items"]
            ]
        )
        query_count += 1
        if query_count > MAX_QUERY_COUNT:
            logger.warning(f"Query count exceeded {MAX_QUERY_COUNT}")
            break

    logger.debug(f"Found conversations: {conversations}")
    return conversations


def find_conversation_by_id(user_id: str, conversation_id: str) -> ConversationModel:
    logger.debug(f"Finding conversation: {conversation_id}")
    table = _get_table_client(user_id)
    response = table.query(
        IndexName="SKIndex",
        KeyConditionExpression=Key("SK").eq(_compose_conv_id(user_id, conversation_id)),
    )
    if len(response["Items"]) == 0:
        raise RecordNotFoundError(f"No conversation found with id: {conversation_id}")

    # NOTE: conversation is unique
    item = response["Items"][0]
    conv = ConversationModel(
        id=_decompose_conv_id(item["SK"]),
        create_time=float(item["CreateTime"]),
        title=item["Title"],
        message_map={
            k: MessageModel(
                role=v["role"],
                content=ContentModel(
                    content_type=v["content"]["content_type"],
                    body=v["content"]["body"],
                ),
                model=v["model"],
                children=v["children"],
                parent=v["parent"],
                create_time=float(v["create_time"]),
            )
            for k, v in json.loads(item["MessageMap"]).items()
        },
        last_message_id=item["LastMessageId"],
        bot_id=item["BotId"],
    )
    logger.debug(f"Found conversation: {conv}")
    return conv


def delete_conversation_by_id(user_id: str, conversation_id: str):
    logger.debug(f"Deleting conversation: {conversation_id}")
    table = _get_table_client(user_id)

    try:
        response = table.delete_item(
            Key={"PK": user_id, "SK": _compose_conv_id(user_id, conversation_id)},
            ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise RecordNotFoundError(
                f"Conversation with id {conversation_id} not found"
            )
        else:
            raise e

    return response


def delete_conversation_by_user_id(user_id: str):
    logger.debug(f"Deleting ALL conversations for user: {user_id}")
    table = _get_table_client(user_id)

    query_params = {
        "KeyConditionExpression": Key("PK").eq(user_id)
        # NOTE: Need SK to fetch only conversations
        & Key("SK").begins_with(f"{user_id}#CONV#"),
        "ProjectionExpression": "SK",  # Only SK is needed to delete
    }

    def delete_batch(batch):
        with table.batch_writer() as writer:
            for item in batch:
                writer.delete_item(Key={"PK": user_id, "SK": item["SK"]})

    try:
        response = table.query(
            **query_params,
        )

        while True:
            items = response.get("Items", [])
            for i in range(0, len(items), TRANSACTION_BATCH_SIZE):
                batch = items[i : i + TRANSACTION_BATCH_SIZE]
                delete_batch(batch)

            # Check if next page exists
            if "LastEvaluatedKey" not in response:
                break

            # Load next page
            query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = table.query(
                **query_params,
            )

    except ClientError as e:
        logger.error(f"An error occurred: {e.response['Error']['Message']}")


def change_conversation_title(user_id: str, conversation_id: str, new_title: str):
    logger.debug(f"Updating conversation title: {conversation_id} to {new_title}")
    table = _get_table_client(user_id)

    try:
        response = table.update_item(
            Key={
                "PK": user_id,
                "SK": _compose_conv_id(user_id, conversation_id),
            },
            UpdateExpression="set Title=:t",
            ExpressionAttributeValues={":t": new_title},
            ReturnValues="UPDATED_NEW",
            ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise RecordNotFoundError(
                f"Conversation with id {conversation_id} not found"
            )
        else:
            raise e

    logger.debug(f"Updated conversation title response: {response}")

    return response
