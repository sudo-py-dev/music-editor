import os
from datetime import datetime, timedelta
from tools.logger import logger
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, ForeignKey, select, update, delete, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from typing import Any, List, Dict, Optional
import time
from tools.enums import AccessPermission
from pyrogram.errors import ChatAdminRequired, ChannelPrivate, PeerIdInvalid, RPCError, ChatInvalid
from pyrogram import Client
from pyrogram.types import ChatPrivileges
from pyrogram.enums import ChatMembersFilter


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///my_bot.sqlite")


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith('sqlite') else {}
)


async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


Base = declarative_base()

class Chats(Base):
    __tablename__ = 'chats'
    chat_id = Column(Integer, primary_key=True, index=True, unique=True)
    chat_type = Column(String, nullable=True)
    chat_title = Column(String, nullable=True)
    language = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    # is the bot admin of the chat
    is_admin = Column(Boolean, default=False)

    # Control update of admins permissions
    last_admins_update = Column(DateTime, nullable=True)
    chat_permissions = Column(JSON, nullable=True)

    # Relationship with AdminsPermissions
    admins_permissions = relationship("AdminsPermissions", back_populates="chat", cascade="all, delete-orphan")

    @classmethod
    async def create(cls, chat_id: int, chat_type: str, chat_title: str, is_active: bool = True) -> Dict[str, Any]:
        async with async_session() as session:
            result = await session.execute(select(cls).filter_by(chat_id=chat_id))
            chat = result.scalars().first()
            if chat is None:
                chat = cls(chat_id=chat_id, chat_type=chat_type, chat_title=chat_title, is_active=is_active)
                session.add(chat)
                await session.commit()
                await session.refresh(chat)
                return {k: v for k, v in chat.__dict__.items() if not k.startswith('_')}
            return {k: v for k, v in chat.__dict__.items() if not k.startswith('_')}

    @classmethod
    async def update(cls, chat_id: int, **kwargs) -> bool:
        async with async_session() as session:
            result = await session.execute(select(cls).filter_by(chat_id=chat_id))
            chat = result.scalars().first()
            if chat is None:
                return False
            for key, value in kwargs.items():
                setattr(chat, key, value)
            session.add(chat)
            await session.commit()
            await session.refresh(chat)
            return True

    @classmethod
    async def delete(cls, chat_id: int) -> bool:
        async with async_session() as session:
            result = await session.execute(select(cls).filter_by(chat_id=chat_id))
            chat = result.scalars().first()
            if chat is None:
                return False
            await session.delete(chat)
            await session.commit()
            return True

    @classmethod
    async def get(cls, chat_id: int) -> Optional[Dict[str, Any]]:
        async with async_session() as session:
            result = await session.execute(select(cls).filter_by(chat_id=chat_id))
            chat = result.scalars().first()
            if chat is None:
                return None
            return {k: v for k, v in chat.__dict__.items() if not k.startswith('_')}

    @classmethod
    async def count(cls) -> int:
        async with async_session() as session:
            result = await session.execute(select(func.count()).select_from(select(cls).subquery()))
            return result.scalar_one()

    @classmethod
    async def count_by(cls, **kwargs) -> int:
        async with async_session() as session:
            result = await session.execute(select(func.count()).select_from(select(cls).filter_by(**kwargs).subquery()))
            return result.scalar_one()

    @classmethod
    async def chat_status_change(cls, chat_id: int, chat_type: str, chat_title: str, is_active: bool, is_admin: bool) -> bool:
        async with async_session() as session:
            result = await session.execute(select(cls).filter_by(chat_id=chat_id))
            chat = result.scalars().first()
            if chat is None:
                chat = cls(chat_id=chat_id, chat_type=chat_type, chat_title=chat_title, is_active=is_active, is_admin=is_admin)
                session.add(chat)
            else:
                chat.chat_type = chat_type
                chat.chat_title = chat_title
                chat.is_active = is_active
                chat.is_admin = is_admin
            await session.commit()
            return True
    
    @classmethod
    async def get_all(cls) -> List[Dict[str, Any]]:
        async with async_session() as session:
            result = await session.execute(select(cls))
            chats = result.scalars().all()
            return [{k: v for k, v in chat.__dict__.items() if not k.startswith('_')} for chat in chats]


class AdminsPermissions(Base):
    __tablename__ = 'admins_permissions'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    admin_id = Column(Integer, index=True)
    chat_id = Column(Integer, ForeignKey('chats.chat_id', ondelete="CASCADE"), nullable=False)
    privileges = Column(JSON, nullable=False)

    # Relationship with Chats
    chat = relationship("Chats", back_populates="admins_permissions")

    @classmethod
    async def create(cls, client: Client, chat_id: int, admin_list: list[tuple[int, Any]]) -> AccessPermission:
        """
        Create or update admin permissions for a chat.

        Args:
            client: The client to use for the request
            chat_id: The chat ID to update permissions for
            admin_list: List of (admin_id, ChatPrivileges) tuples

        Returns:
            AccessPermission: Status of the operation
        """
        async with async_session() as session:
            try:
                chat = await session.execute(select(Chats).filter_by(chat_id=chat_id))
                chat = chat.scalars().first()
                if chat is None:
                    try:
                        chat_info = await client.get_chat(chat_id)
                        chat = Chats(chat_id=chat_id, chat_type=chat_info.type.value, chat_title=chat_info.title)
                        session.add(chat)
                        await session.commit()
                    except (RPCError, ChannelPrivate, PeerIdInvalid, ValueError):
                        return AccessPermission.CHAT_NOT_FOUND
                await session.execute(delete(cls).filter_by(chat_id=chat_id))
                for admin_id, privileges in admin_list:
                    admin = cls(
                        admin_id=admin_id,
                        chat_id=chat_id,
                        privileges=privileges
                    )
                    session.add(admin)
                chat.last_admins_update = datetime.now()
                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Error updating admin permissions: {e}")
                raise   
    
    @classmethod
    async def update_admin(cls, chat_id: int, admin_id: int, privileges: Any) -> AccessPermission:
        """
        Update admin permissions for a chat.

        Args:
            chat_id: The chat ID to update permissions for
            admin_id: The admin ID to update permissions for
            privileges: The new admin privileges

        Returns:
            AccessPermission: Status of the operation
        """
        async with async_session() as session:
            try:
                admin = await session.execute(select(cls).filter_by(chat_id=chat_id, admin_id=admin_id))
                admin = admin.scalars().first()
                if isinstance(privileges, ChatPrivileges):
                    privileges = privileges.__dict__
                elif isinstance(privileges, dict):
                    pass
                else:
                    raise ValueError("Invalid privileges type")
                if admin is None:
                    admin = cls(chat_id=chat_id, admin_id=admin_id, privileges=privileges)
                    session.add(admin)
                else:
                    admin.privileges = privileges
                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Error updating admin permissions: {e}")
                raise   
    
    @classmethod
    async def delete_admin(cls, chat_id: int, admin_id: int) -> AccessPermission:
        """
        Delete admin permissions for a chat.

        Args:
            chat_id: The chat ID to delete permissions for
            admin_id: The admin ID to delete permissions for

        Returns:
            AccessPermission: Status of the operation
        """
        async with async_session() as session:
            try:
                admin = await session.execute(select(cls).filter_by(chat_id=chat_id, admin_id=admin_id))
                admin = admin.scalars().first()
                if admin is None:
                    return False
                await session.delete(admin)
                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Error deleting admin permissions: {e}")
                raise   
    
    @classmethod
    async def is_admin(cls, client: Client, chat_id: int, admin_id: int, permission_required: str) -> AccessPermission:
        """
        Check if a user has a specific admin permission.

        Args:
            client: The Telegram client
            chat_id: The chat ID
            admin_id: The user ID to check
            permission: The permission to verify

        Returns:
            AccessPermission: Permission status
        """
        async with async_session() as session:
            try:
                chat = await session.execute(select(Chats).filter_by(chat_id=chat_id))
                chat = chat.scalars().first()
                if chat is None:
                    try:
                        chat_info = await client.get_chat(chat_id=chat_id)
                        chat = Chats(chat_id=chat_id, chat_type=chat_info.type.value, chat_title=chat_info.title)
                        session.add(chat)
                        await session.commit()
                        await session.refresh(chat)
                    except Exception:
                        return AccessPermission.CHAT_NOT_FOUND
                if not chat.is_admin:
                    return AccessPermission.BOT_NOT_ADMIN
                elif not chat.last_admins_update or (chat.last_admins_update < datetime.now() - timedelta(hours=24)):
                    admin_list = [
                        (member.user.id, member.privileges.__dict__)
                        async for member in client.get_chat_members(
                            chat_id=chat_id,
                            filter=ChatMembersFilter.ADMINISTRATORS
                        )
                    ]
                    await cls.create(client=client, chat_id=chat_id, admin_list=admin_list)
                    await session.refresh(chat)
                admin = await session.execute(select(cls).filter_by(
                    chat_id=chat_id,
                    admin_id=admin_id
                ))
                admin = admin.scalars().first()

                if admin is None:
                    return AccessPermission.NOT_ADMIN
                elif chat_id == admin_id:
                    return AccessPermission.ALLOW
                elif admin.privileges.get(permission_required) is None:
                    return AccessPermission.DENY
                elif admin.privileges.get(permission_required):
                    return AccessPermission.ALLOW
                return AccessPermission.DENY
            except (ChatInvalid, ChatAdminRequired, ChannelPrivate, PeerIdInvalid, ValueError) as e:
                return AccessPermission.CHAT_NOT_FOUND
            except Exception as e:
                logger.error(f"Error in is_admin for chat {chat_id}, admin {admin_id}: {e}")
                return AccessPermission.DENY

    @classmethod
    async def clear(cls, chat_id: int) -> bool:
        """Clear all admin permissions for a chat."""
        async with async_session() as session:
            try:
                session.begin()
                chat = await session.execute(select(Chats).filter_by(chat_id=chat_id))
                chat = chat.scalars().first()
                if chat is None:
                    return False
                await session.execute(delete(cls).filter_by(chat_id=chat_id))
                chat.last_admins_update = None
                await session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Error clearing admin permissions: {e}")
                return False

    @classmethod
    async def clear_all(cls) -> bool:
        """Clear all admin permissions from the database."""
        async with async_session() as session:
            try:
                session.begin()
                await session.execute(delete(cls))
                # Reset all chat timestamps
                await session.execute(update(Chats).values(last_admins_update=None))
                await session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Error clearing all admin permissions: {e}")
                return False


class Users(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, index=True, unique=True)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    language = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # wait_input is used to wait for user input
    wait_input = Column(String, nullable=True)
    waiting_for_message_id = Column(Integer, nullable=True)
    audio_id = Column(Integer, ForeignKey('audio_files.audio_id', ondelete="CASCADE"), nullable=True)

    @classmethod
    async def create(cls, user_id: int,
               username: str | None = None,
               full_name: str | None = None,
               language: str | None = None,
               is_active: bool = True) -> bool:
        async with async_session() as session:
            user = await session.execute(select(cls).filter_by(user_id=user_id))
            user = user.scalars().first()
            if user is None:
                user = cls(user_id=user_id,
                             username=username,
                             full_name=full_name,
                             language=language,
                             is_active=is_active)
                session.add(user)
                await session.commit()
                return True
            return False

    @classmethod
    async def get(cls, user_id: int) -> Optional[Dict[str, Any]]:
        async with async_session() as session:
            user = await session.execute(select(cls).filter_by(user_id=user_id))
            user = user.scalars().first()
            if user is None:
                return False
            return user.__dict__

    @classmethod
    async def update(cls, user_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        async with async_session() as session:
            user = await session.execute(select(cls).filter_by(user_id=user_id))
            user = user.scalars().first()
            if user is None:
                return False
            for key, value in kwargs.items():
                setattr(user, key, value)
            await session.commit()
            await session.refresh(user)
            return user.__dict__

    @classmethod
    async def delete(cls, user_id: int) -> bool:
        async with async_session() as session:
            user = await session.execute(select(cls).filter_by(user_id=user_id))
            user = user.scalars().first()
            if user is None:
                return False
            await session.delete(user)
            await session.commit()
            return True

    @classmethod
    async def delete_all(cls) -> bool:
        async with async_session() as session:
            await session.execute(delete(cls))
            await session.commit()
            return True

    @classmethod
    async def get_all(cls) -> list:
        async with async_session() as session:
            users = await session.execute(select(cls))
            users = users.scalars().all()
            # Convert SQLAlchemy objects to dictionaries and remove the _sa_instance_state key
            return [{k: v for k, v in user.__dict__.items() if not k.startswith('_')} for user in users]

    @classmethod
    async def get_all_by(cls, **kwargs) -> list:
        async with async_session() as session:
            users = await session.execute(select(cls).filter_by(**kwargs))
            users = users.scalars().all()
            return users

    @classmethod
    async def count(cls) -> int:
        async with async_session() as session:
            result = await session.execute(select(func.count()).select_from(cls))
            return result.scalar() or 0

    @classmethod
    async def count_by(cls, **kwargs) -> int:
        async with async_session() as session:
            result = await session.execute(select(func.count()).select_from(cls).filter_by(**kwargs))
            return result.scalar() or 0
    
    @classmethod
    async def get_waiting_for(cls, user_id: int) -> dict | None:
        async with async_session() as session:
            user = await session.execute(select(cls).filter_by(user_id=user_id))
            user = user.scalars().first()
            if user is None or user.wait_input is None:
                return None
            return user.__dict__

    @classmethod
    async def set_waiting_for(cls, user_id: int, wait_input: str, audio_id: int, waiting_for_message_id: int) -> bool:
        async with async_session() as session:
            user = await session.execute(select(cls).filter_by(user_id=user_id))
            user = user.scalars().first()
            if user is None:
                return False
            user.wait_input = wait_input
            user.audio_id = audio_id
            user.waiting_for_message_id = waiting_for_message_id
            await session.commit()
            return True
    
    @classmethod
    async def clear_waiting_for(cls, user_id: int) -> bool:
        async with async_session() as session:
            user = await session.execute(select(cls).filter_by(user_id=user_id))
            user = user.scalars().first()
            if user is None:
                return False
            user.wait_input = None
            user.audio_id = None
            user.waiting_for_message_id = None
            await session.commit()
            return True


class BotSettings(Base):
    __tablename__ = 'bot_settings'

    # Primary key (always 1 for the single settings record)
    id = Column(Integer, primary_key=True, default=1, autoincrement=False)

    # Bot settings
    can_join_group = Column(Boolean, default=True, nullable=False)
    can_join_channel = Column(Boolean, default=True, nullable=False)
    owner_id = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Cache for settings
    _instance = None
    _last_fetch = 0
    CACHE_TTL = 60 * 60 * 24  # Cache for 24 hours

    @classmethod
    def _get_cached_settings(cls) -> 'BotSettings':
        """Get settings from cache if valid, otherwise None"""
        current_time = time.time()
        if (cls._instance is not None and
                current_time - cls._last_fetch < cls.CACHE_TTL):
            return cls._instance
        return None

    @classmethod
    def _update_cache(cls, settings: 'BotSettings'):
        """Update the cache with new settings"""
        cls._instance = settings
        cls._last_fetch = time.time()

    @classmethod
    async def get_settings(cls, force_refresh: bool = False) -> 'BotSettings':
        """Get the single settings record, using cache if available"""
        # Try to get from cache first
        if not force_refresh:
            cached = cls._get_cached_settings()
            if cached:
                return cached

        # If not in cache or force refresh, get from DB
        async with async_session() as session:
            result = await session.execute(select(cls).limit(1))
            settings = result.scalars().first()
            
            if not settings:
                settings = cls()
                session.add(settings)
                await session.commit()
                await session.refresh(settings)

            # Update cache
            cls._update_cache(settings)
            return settings

    @classmethod
    async def update_settings(cls, **kwargs) -> 'BotSettings':
        """Update settings with the provided values"""
        async with async_session() as session:
            result = await session.execute(select(cls).limit(1))
            settings = result.scalars().first()
            
            if not settings:
                settings = cls()
                session.add(settings)
                await session.commit()
                await session.refresh(settings)

            for key, value in kwargs.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)

            await session.commit()
            await session.refresh(settings)
            # Update cache
            cls._update_cache(settings)
            return settings

    @classmethod
    async def switch_settings(cls, key: str) -> 'BotSettings':
        """Switch the value of a setting"""
        async with async_session() as session:
            settings = await session.execute(select(cls).limit(1))
            settings = settings.scalars().first()
            
            if not settings:
                settings = cls()
                session.add(settings)

            if hasattr(settings, key):
                setattr(settings, key, not getattr(settings, key))

            await session.commit()
            await session.refresh(settings)
            # Update cache
            cls._update_cache(settings)
            return settings


class AudioFiles(Base):
    __tablename__ = 'audio_files'
    audio_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete="CASCADE"), nullable=False)
    file_id = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    title = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
    file_date = Column(DateTime, default=func.now())
    image_id = Column(String, nullable=True)
    genre = Column(String, nullable=True)
    album = Column(String, nullable=True)
    artist = Column(String, nullable=True)
    cut_start = Column(Integer, nullable=True)
    cut_end = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    @classmethod
    async def create(cls, user_id: int,
               file_id: str,
               file_name: str,
               file_size: int,
               title: str | None = None,
               mime_type: str | None = None,
               file_date: int | None = None) -> dict:
        async with async_session() as session:
            audio_file = AudioFiles(user_id=user_id,
                                    file_id=file_id,
                                    file_name=file_name,
                                    file_size=file_size,
                                    title=title,
                                    mime_type=mime_type,
                                    file_date=file_date)
            session.add(audio_file)
            await session.commit()
            await session.refresh(audio_file)
            return audio_file.__dict__
    
    @classmethod
    async def get(cls, user_id: int, audio_id: int) -> dict | None:
        async with async_session() as session:
            audio_file = await session.execute(select(cls).filter_by(user_id=user_id, audio_id=audio_id))
            audio_file = audio_file.scalars().first()
            if audio_file is None:
                return False
            return audio_file.__dict__
    
    @classmethod
    async def update(cls, user_id: int, audio_id: int, **kwargs) -> dict | None:
        async with async_session() as session:
            audio_file = await session.execute(select(cls).filter_by(user_id=user_id, audio_id=audio_id))
            audio_file = audio_file.scalars().first()
            if audio_file is None:
                return None
            for key, value in kwargs.items():
                setattr(audio_file, key, value)
            await session.commit()
            await session.refresh(audio_file)
            return audio_file.__dict__
    
    @classmethod
    async def delete(cls, user_id: int, audio_id: int) -> bool:
        async with async_session() as session:
            audio_file = await session.execute(select(cls).filter_by(user_id=user_id, audio_id=audio_id))
            audio_file = audio_file.scalars().first()
            if audio_file is None:
                return False
            await session.delete(audio_file)
            await session.commit()
            return True
    
    @classmethod
    async def delete_all(cls) -> bool:
        async with async_session() as session:
            await session.execute(delete(cls))
            await session.commit()
            return True
    
    @classmethod
    async def get_all(cls) -> list:
        async with async_session() as session:
            audio_files = await session.execute(select(cls))
            audio_files = audio_files.scalars().all()
            return audio_files


async def create_tables():
    async with engine.begin() as conn:
        logger.info("Database tables initialized successfully")
        await conn.run_sync(Base.metadata.create_all)
