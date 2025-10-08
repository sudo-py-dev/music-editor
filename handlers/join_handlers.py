from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import ChannelPrivate
from tools.database import Chats, BotSettings
from pyrogram.types import ChatMemberUpdated, ChatJoinRequest
from pyrogram.handlers import ChatMemberUpdatedHandler, ChatJoinRequestHandler
from pyrogram import filters, Client


async def group_join_handler(_, member: ChatMemberUpdated):
    if member.old_chat_member and not member.new_chat_member:
        return
    if member.new_chat_member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
        if member.new_chat_member.user.is_self:
            if not BotSettings.get_settings().can_join_group:
                try:
                    await member.chat.leave()
                except ChannelPrivate:
                    pass
            else:
                chat_id = member.chat.id
                chat_title = member.chat.title
                chat_type = member.chat.type.value
                Chats.chat_status_change(chat_id, chat_type, chat_title, True)
        else:
            # add operation you want to do
            pass
    elif member.new_chat_member.status == ChatMemberStatus.MEMBER:
        if member.new_chat_member.user.is_self:
            if not BotSettings.get_settings().can_join_group:
                try:
                    await member.chat.leave()
                except ChannelPrivate:
                    pass
            else:
                chat_id = member.chat.id
                chat_title = member.chat.title
                chat_type = member.chat.type.value
                Chats.chat_status_change(chat_id, chat_type, chat_title, True)
        else:
            # add operation you want to do
            pass
    elif member.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
        if member.new_chat_member.user.is_self:
            Chats.update(member.chat.id, is_active=False)
        else:
            # add operation you want to do
            pass


async def channel_join_handler(client: Client, member: ChatMemberUpdated):
    if member.old_chat_member and not member.new_chat_member:
        return
    if member.new_chat_member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
        if member.new_chat_member.user.is_self:
            if not BotSettings.get_settings().can_join_channel:
                try:
                    await member.chat.leave()
                except ChannelPrivate:
                    pass
            else:
                chat_id = member.chat.id
                chat_title = member.chat.title
                chat_type = member.chat.type.value
                Chats.chat_status_change(chat_id, chat_type, chat_title, True)
        else:
            # add operation you want to do
            pass
    elif member.new_chat_member.status == ChatMemberStatus.MEMBER:
        if member.new_chat_member.user.is_self:
            chat_id = member.chat.id
            chat_title = member.chat.title
            chat_type = member.chat.type.value
            Chats.chat_status_change(chat_id, chat_type, chat_title, True)
        else:
            # add operation you want to do
            pass
    elif member.new_chat_member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.BANNED}:
        if member.new_chat_member.user.is_self:
            Chats.update(member.chat.id, is_active=False)
        else:
            # add operation you want to do
            pass


async def group_join_request_handler(_, request: ChatJoinRequest):
    # add implementation
    pass


async def channel_join_request_handler(_, request: ChatJoinRequest):
    # add implementation
    pass


join_handlers = [
    ChatMemberUpdatedHandler(group_join_handler, filters.group),
    ChatJoinRequestHandler(group_join_request_handler, filters.group),
    ChatMemberUpdatedHandler(channel_join_handler, filters.channel),
    ChatJoinRequestHandler(channel_join_request_handler, filters.channel)
]
