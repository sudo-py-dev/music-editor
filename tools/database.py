import os
from datetime import datetime, timedelta
from .logger import logger
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from typing import Any
from dotenv import load_dotenv
import time
from tools.enums import AccessPermission


load_dotenv()


Base = sqlalchemy.orm.declarative_base()
engine = create_engine(os.getenv("DATABASE_URL") or "sqlite:///db.sqlite",
                       pool_size=10,
                       max_overflow=20,
                       echo=False,
                       connect_args={
                           "timeout": 30
                       })

Session = sessionmaker(bind=engine)


class Chats(Base):
    __tablename__ = 'chats'
    chat_id = Column(Integer, primary_key=True, index=True, unique=True)
    chat_type = Column(String, nullable=True)
    chat_title = Column(String, nullable=True)
    language = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    # Control update of admins permissions
    last_admins_update = Column(DateTime, nullable=True)

    # Relationship with AdminsPermissions
    admins_permissions = relationship("AdminsPermissions", back_populates="chat", cascade="all, delete-orphan")

    @staticmethod
    def create(chat_id: int, chat_type: str, chat_title: str, is_active: bool = True) -> dict:
        with Session() as session:
            chat = session.query(Chats).filter_by(chat_id=chat_id).first()
            if chat is None:
                chat = Chats(chat_id=chat_id, chat_type=chat_type, chat_title=chat_title, is_active=is_active)
                session.add(chat)
                session.commit()
                return chat.__dict__
            return chat.__dict__

    @staticmethod
    def update(chat_id: int, **kwargs) -> bool:
        with Session() as session:
            chat = session.query(Chats).filter_by(chat_id=chat_id).first()
            if chat is None:
                return False
            for key, value in kwargs.items():
                setattr(chat, key, value)
            session.commit()
            return True

    @staticmethod
    def delete(chat_id: int) -> bool:
        with Session() as session:
            chat = session.query(Chats).filter_by(chat_id=chat_id).first()
            if chat is None:
                return False
            session.delete(chat)
            session.commit()
            return True

    @staticmethod
    def get(chat_id: int) -> dict | bool:
        with Session() as session:
            chat = session.query(Chats).filter_by(chat_id=chat_id).first()
            if chat is None:
                return False
            return chat.__dict__

    @staticmethod
    def count() -> int:
        with Session() as session:
            return session.query(Chats).count()

    @staticmethod
    def count_by(**kwargs) -> int:
        with Session() as session:
            return session.query(Chats).filter_by(**kwargs).count()

    @staticmethod
    def chat_status_change(chat_id: int, chat_type: str, chat_title: str, is_active: bool) -> bool:
        with Session() as session:
            chat = session.query(Chats).filter_by(chat_id=chat_id).first()
            if chat is None:
                chat = Chats(chat_id=chat_id, chat_type=chat_type, chat_title=chat_title, is_active=is_active)
                session.add(chat)
            else:
                chat.chat_type = chat_type
                chat.chat_title = chat_title
                chat.is_active = is_active
            session.commit()
            return True


class AdminsPermissions(Base):
    __tablename__ = 'admins_permissions'
    admin_id = Column(Integer, primary_key=True, index=True, unique=True)
    chat_id = Column(Integer, ForeignKey('chats.chat_id', ondelete="CASCADE"), nullable=False)
    is_anonymous = Column(Boolean, nullable=True)
    can_manage_chat = Column(Boolean, nullable=True)
    can_delete_messages = Column(Boolean, nullable=True)
    can_manage_video_chats = Column(Boolean, nullable=True)  # Groups and supergroups only
    can_restrict_members = Column(Boolean, nullable=True)
    can_promote_members = Column(Boolean, nullable=True)
    can_change_info = Column(Boolean, nullable=True)
    can_invite_users = Column(Boolean, nullable=True)
    can_post_messages = Column(Boolean, nullable=True)  # Channels only
    can_edit_messages = Column(Boolean, nullable=True)  # Channels only
    can_pin_messages = Column(Boolean, nullable=True)  # Groups and supergroups only
    can_post_stories = Column(Boolean, nullable=True)
    can_edit_stories = Column(Boolean, nullable=True)
    can_delete_stories = Column(Boolean, nullable=True)
    can_manage_topics = Column(Boolean, nullable=True)  # supergroups only
    can_manage_direct_messages = Column(Boolean, nullable=True)

    # Relationship with Chats
    chat = relationship("Chats", back_populates="admins_permissions")

    @staticmethod
    def _get_valid_privileges(privileges: Any) -> dict[str, Any]:
        """Extract valid privilege attributes from a ChatPrivileges object."""
        return {
            k: v for k, v in vars(privileges).items()
            if (not k.startswith('_')
                and hasattr(AdminsPermissions, k)
                and k not in ('admin_id', 'chat_id'))
        }

    @classmethod
    def create(cls, chat_id: int, admin_list: list[tuple[int, Any]]) -> AccessPermission:
        """
        Create or update admin permissions for a chat.

        Args:
            chat_id: The chat ID to update permissions for
            admin_list: List of (admin_id, ChatPrivileges) tuples

        Returns:
            AccessPermission: Status of the operation
        """
        with Session() as session:
            try:
                chat = session.query(Chats).filter_by(chat_id=chat_id).first()
                if chat is None:
                    chat = Chats(chat_id=chat_id, chat_type="", chat_title="")
                    session.add(chat)

                # Delete old admin permissions
                session.query(cls).filter_by(chat_id=chat_id).delete()

                # Add new admin permissions
                for admin_id, privileges in admin_list:
                    priv_dict = cls._get_valid_privileges(privileges)
                    admin = cls(
                        admin_id=admin_id,
                        chat_id=chat_id,
                        **priv_dict
                    )
                    session.add(admin)
                # Update last_admins_update
                chat.last_admins_update = datetime.now()
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Error updating admin permissions: {e}")
                raise

    @classmethod
    def is_admin(cls, chat_id: int, admin_id: int, permission: str) -> AccessPermission:
        """
        Check if a user has a specific admin permission.

        Args:
            chat_id: The chat ID
            admin_id: The user ID to check
            permission: The permission to verify

        Returns:
            AccessPermission: Permission status
        """
        with Session() as session:
            try:
                chat = session.query(Chats).filter_by(chat_id=chat_id).first()
                if chat is None:
                    Chats.create(chat_id, "", "")
                    return AccessPermission.NEED_UPDATE

                if not chat.last_admins_update or chat.last_admins_update < datetime.now() - timedelta(hours=2):
                    return AccessPermission.NEED_UPDATE

                admin = session.query(cls).filter_by(
                    chat_id=chat_id,
                    admin_id=admin_id
                ).first()

                if admin is None:
                    return AccessPermission.NOT_ADMIN
                if not hasattr(admin, permission):
                    return AccessPermission.DENY
                return AccessPermission.ALLOW if getattr(admin, permission) else AccessPermission.DENY
            except Exception as e:
                logger.error(f"Error in is_admin for chat {chat_id}, admin {admin_id}: {e}")
                return AccessPermission.DENY

    @classmethod
    def clear(cls, chat_id: int) -> bool:
        """Clear all admin permissions for a chat."""
        with Session() as session:
            try:
                session.begin()
                chat = session.query(Chats).filter_by(chat_id=chat_id).first()
                if chat is None:
                    return False
                session.query(cls).filter_by(chat_id=chat_id).delete()
                chat.last_admins_update = None
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Error clearing admin permissions: {e}")
                return False

    @classmethod
    def clear_all(cls) -> bool:
        """Clear all admin permissions from the database."""
        with Session() as session:
            try:
                session.begin()
                session.query(cls).delete()
                # Reset all chat timestamps
                session.query(Chats).update({Chats.last_admins_update: None})
                session.commit()
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
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationship with AudioFiles
    waiting_for = Column(String, nullable=True)
    waiting_for_message_id = Column(Integer, nullable=True)
    audio_id = Column(Integer, ForeignKey('audio_files.audio_id', ondelete="CASCADE"), nullable=True)


    @staticmethod
    def create(user_id: int,
               username: str | None = None,
               full_name: str | None = None,
               language: str | None = None,
               is_active: bool = True) -> bool:
        with Session() as session:
            user = session.query(Users).filter_by(user_id=user_id).first()
            if user is None:
                user = Users(user_id=user_id,
                             username=username,
                             full_name=full_name,
                             language=language,
                             is_active=is_active)
                session.add(user)
                session.commit()
                return True
            return False

    @staticmethod
    def get(user_id: int) -> dict | None:
        with Session() as session:
            user = session.query(Users).filter_by(user_id=user_id).first()
            if user is None:
                return False
            return user.__dict__

    @staticmethod
    def update(user_id: int, **kwargs) -> bool:
        with Session() as session:
            user = session.query(Users).filter_by(user_id=user_id).first()
            if user is None:
                return False
            for key, value in kwargs.items():
                setattr(user, key, value)
            session.commit()
            return True

    @staticmethod
    def delete(user_id: int) -> bool:
        with Session() as session:
            user = session.query(Users).filter_by(user_id=user_id).first()
            if user is None:
                return False
            session.delete(user)
            session.commit()
            return True

    @staticmethod
    def delete_all() -> bool:
        with Session() as session:
            session.query(Users).delete()
            session.commit()
            return True

    @staticmethod
    def get_all() -> list:
        with Session() as session:
            users = session.query(Users).all()
            return users

    @staticmethod
    def get_all_by(**kwargs) -> list:
        with Session() as session:
            users = session.query(Users).filter_by(**kwargs).all()
            return users

    @staticmethod
    def count() -> int:
        with Session() as session:
            return session.query(Users).count() or 0

    @staticmethod
    def count_by(**kwargs) -> int:
        with Session() as session:
            return session.query(Users).filter_by(**kwargs).count() or 0
    
    @staticmethod
    def get_waiting_for(user_id: int) -> dict | None:
        with Session() as session:
            user = session.query(Users).filter_by(user_id=user_id).first()
            if user is None or user.waiting_for is None:
                return None
            return user.__dict__

    @staticmethod
    def set_waiting_for(user_id: int, waiting_for: str, audio_id: int, waiting_for_message_id: int) -> bool:
        with Session() as session:
            user = session.query(Users).filter_by(user_id=user_id).first()
            if user is None:
                return False
            user.waiting_for = waiting_for
            user.audio_id = audio_id
            user.waiting_for_message_id = waiting_for_message_id
            session.commit()
            return True
    
    @staticmethod
    def clear_waiting_for(user_id: int) -> bool:
        with Session() as session:
            user = session.query(Users).filter_by(user_id=user_id).first()
            if user is None:
                return False
            user.waiting_for = None
            user.audio_id = None
            user.waiting_for_message_id = None
            session.commit()
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
    def get_settings(cls, force_refresh: bool = False) -> 'BotSettings':
        """Get the single settings record, using cache if available"""
        # Try to get from cache first
        if not force_refresh:
            cached = cls._get_cached_settings()
            if cached:
                return cached

        # If not in cache or force refresh, get from DB
        with Session() as session:
            settings = session.query(cls).first()
            if not settings:
                settings = cls()
                session.add(settings)
                session.commit()
                session.refresh(settings)

            # Update cache
            cls._update_cache(settings)
            return settings

    @classmethod
    def update_settings(cls, **kwargs) -> 'BotSettings':
        """Update settings with the provided values"""
        with Session() as session:
            settings = session.query(cls).first()
            if not settings:
                settings = cls()
                session.add(settings)

            for key, value in kwargs.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)

            session.commit()
            session.refresh(settings)
            # Update cache
            cls._update_cache(settings)
            return settings

    @classmethod
    def switch_settings(cls, key: str) -> 'BotSettings':
        """Switch the value of a setting"""
        with Session() as session:
            settings = session.query(cls).first()
            if not settings:
                settings = cls()
                session.add(settings)

            if hasattr(settings, key):
                setattr(settings, key, not getattr(settings, key))

            session.commit()
            session.refresh(settings)
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

    @staticmethod
    def create(user_id: int,
               file_id: str,
               file_name: str,
               file_size: int,
               title: str | None = None,
               mime_type: str | None = None,
               file_date: int | None = None) -> dict:
        with Session() as session:
            audio_file = AudioFiles(user_id=user_id,
                                    file_id=file_id,
                                    file_name=file_name,
                                    file_size=file_size,
                                    title=title,
                                    mime_type=mime_type,
                                    file_date=file_date)
            session.add(audio_file)
            session.commit()
            session.refresh(audio_file)
            return audio_file.__dict__
    
    @staticmethod
    def get(user_id: int, audio_id: int) -> dict | None:
        with Session() as session:
            audio_file = session.query(AudioFiles).filter_by(user_id=user_id, audio_id=audio_id).first()
            if audio_file is None:
                return False
            return audio_file.__dict__
    
    @staticmethod
    def update(user_id: int, audio_id: int, **kwargs) -> dict | None:
        with Session() as session:
            audio_file = session.query(AudioFiles).filter_by(user_id=user_id, audio_id=audio_id).first()
            if audio_file is None:
                return None
            for key, value in kwargs.items():
                setattr(audio_file, key, value)
            session.commit()
            session.refresh(audio_file)
            return audio_file.__dict__
    
    @staticmethod
    def delete(user_id: int, audio_id: int) -> bool:
        with Session() as session:
            audio_file = session.query(AudioFiles).filter_by(user_id=user_id, audio_id=audio_id).first()
            if audio_file is None:
                return False
            session.delete(audio_file)
            session.commit()
            return True
    
    @staticmethod
    def delete_all() -> bool:
        with Session() as session:
            session.query(AudioFiles).delete()
            session.commit()
            return True
    
    @staticmethod
    def get_all() -> list:
        with Session() as session:
            audio_files = session.query(AudioFiles).all()
            return audio_files


Base.metadata.create_all(engine)
