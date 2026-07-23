"""用户、角色、权限模型"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.core.database import Base

user_roles = Table(
    "user_roles", Base.metadata,
    Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions = Table(
    "role_permissions", Base.metadata,
    Column("role_id", BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", BigInteger, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(50), nullable=False)
    phone = Column(String(20), default="")
    email = Column(String(100), default="")
    avatar_url = Column(String(500), default="")
    status = Column(String(10), default="active")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    roles = relationship("Role", secondary=user_roles, back_populates="users")

    @property
    def role_codes(self) -> list[str]:
        return [r.code for r in self.roles]


class Role(Base):
    __tablename__ = "roles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    code = Column(String(30), unique=True, nullable=False)
    description = Column(String(200), default="")

    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

    @property
    def permission_codes(self) -> list[str]:
        return [p.code for p in self.permissions]


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    code = Column(String(100), unique=True, nullable=False)
    resource = Column(String(50), default="")
    action = Column(String(30), default="")

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
