from datetime import datetime
from typing import Optional

from app.repositories.conversation import (
    change_conversation_title,
    delete_conversation_by_id,
    delete_conversation_by_user_id,
    find_conversation_by_id,
    find_conversation_by_user_id,
)
from app.repositories.custom_bot import (
    delete_bot_by_id,
    find_bot_by_id,
    find_bot_by_user_id,
    store_bot,
)
from app.repositories.model import BotModel
from app.route_schema import (
    BotInput,
    BotMetaOutput,
    BotOutput,
    ChatInput,
    ChatOutput,
    Content,
    Conversation,
    ConversationMetaOutput,
    MessageOutput,
    NewTitleInput,
    ProposedTitle,
    User,
)
from app.usecase import chat, propose_conversation_title
from app.utils import get_current_time
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
def health():
    """For health check"""
    return {"status": "ok"}


@router.post("/conversation", response_model=ChatOutput)
def post_message(request: Request, chat_input: ChatInput):
    """Send chat message"""
    current_user: User = request.state.current_user

    output = chat(user_id=current_user.id, chat_input=chat_input)
    return output


@router.get("/conversation/{conversation_id}", response_model=Conversation)
def get_conversation(request: Request, conversation_id: str):
    """Get a conversation history"""
    current_user: User = request.state.current_user

    conversation = find_conversation_by_id(current_user.id, conversation_id)
    output = Conversation(
        id=conversation_id,
        title=conversation.title,
        create_time=conversation.create_time,
        last_message_id=conversation.last_message_id,
        message_map={
            message_id: MessageOutput(
                role=message.role,
                content=Content(
                    content_type=message.content.content_type,
                    body=message.content.body,
                ),
                model=message.model,
                children=message.children,
                parent=message.parent,
            )
            for message_id, message in conversation.message_map.items()
        },
    )
    return output


@router.delete("/conversation/{conversation_id}")
def delete_conversation(request: Request, conversation_id: str):
    """Delete conversation"""
    current_user: User = request.state.current_user

    delete_conversation_by_id(current_user.id, conversation_id)


@router.get("/conversations", response_model=list[ConversationMetaOutput])
def get_all_conversations(
    request: Request,
):
    """Get all conversation metadata"""
    current_user: User = request.state.current_user

    conversations = find_conversation_by_user_id(current_user.id)
    output = [
        ConversationMetaOutput(
            id=conversation.id,
            title=conversation.title,
            create_time=conversation.create_time,
            model=conversation.model,
        )
        for conversation in conversations
    ]
    return output


@router.delete("/conversations")
def delete_all_conversations(
    request: Request,
):
    """Delete all conversations"""
    delete_conversation_by_user_id(request.state.current_user.id)


@router.patch("/conversation/{conversation_id}/title")
def update_conversation_title(
    request: Request, conversation_id: str, new_title_input: NewTitleInput
):
    """Update conversation title"""
    current_user: User = request.state.current_user

    change_conversation_title(
        current_user.id, conversation_id, new_title_input.new_title
    )


@router.get(
    "/conversation/{conversation_id}/proposed-title", response_model=ProposedTitle
)
def get_proposed_title(request: Request, conversation_id: str):
    """Suggest conversation title"""
    current_user: User = request.state.current_user

    title = propose_conversation_title(current_user.id, conversation_id)
    return ProposedTitle(title=title)


@router.post("/bot", response_model=BotOutput)
def post_bot(request: Request, bot_input: BotInput):
    """Create new bot."""
    current_user: User = request.state.current_user

    store_bot(
        current_user.id,
        BotModel(
            id=bot_input.id,
            title=bot_input.title,
            description=bot_input.description,
            instruction=bot_input.instruction,
            create_time=get_current_time(),
            last_used_time=get_current_time(),
        ),
    )
    return BotOutput(
        id=bot_input.id,
        title=bot_input.title,
        instruction=bot_input.instruction,
        description=bot_input.description,
        create_time=get_current_time(),
        last_used_time=None,
    )


@router.get("/bot", response_model=list[BotMetaOutput])
def get_all_bots(request: Request, limit: Optional[int] = None):
    """Get all bots. The order is descending by `last_used_time`.
    If limit is specified, only the first n bots will be returned.
    """
    current_user: User = request.state.current_user

    bots = find_bot_by_user_id(current_user.id, limit=limit)

    output = [
        BotMeta(
            id=bot.id,
            title=bot.title,
            create_time=bot.create_time,
            last_used_time=bot.last_used_time,
        )
        for bot in bots
    ]
    return output


@router.get("/bot/{bot_id}", response_model=BotOutput)
def get_bot(request: Request, bot_id: str):
    """Get bot by id"""
    current_user: User = request.state.current_user

    bot = find_bot_by_id(current_user.id, bot_id)
    output = BotOutput(
        id=bot.id,
        title=bot.title,
        instruction=bot.instruction,
        description=bot.description,
        create_time=float(bot.create_time),
        last_used_time=float(bot.last_used_time),
    )
    return output


@router.delete("/bot/{bot_id}")
def delete_bot(request: Request, bot_id: str):
    """Delete bot by id"""
    current_user: User = request.state.current_user

    delete_bot_by_id(current_user.id, bot_id)


@router.put("/bot/{bot_id}")
def make_bot_public(request: Request, bot_id: str):
    """Make bot public"""
    current_user: User = request.state.current_user

    raise NotImplementedError()

    # TODO: implement update method to repository

    bot = find_bot_by_id(current_user.id, bot_id)
    # store_bot(
    #     current_user.id,
    #     BotModel(
    #         id=bot.id,
    #         title=bot.title,
    #         description=bot.description,
    #         instruction=bot.instruction,
    #         create_time=bot.create_time,
    #         last_used_time=bot.last_used_time,
    #         public_bot_id=bot.id
    #     ),
    # )


# TODO: remove alias
