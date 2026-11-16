from sqlalchemy import BigInteger, String, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.types import TypeDecorator, String

from datetime import datetime, timedelta
from decimal import Decimal
from config import sqlalchemy_url


engine = create_async_engine(url=sqlalchemy_url)
async_session = async_sessionmaker(engine)


class DecimalType(TypeDecorator):
    impl = String 
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            format(value.normalize(), 'f')
            return str(value) 
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return Decimal(format(Decimal(value).normalize(), 'f'))
        return None


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    invitations: Mapped[int] = mapped_column()
    balance: Mapped[Decimal] = mapped_column(DecimalType, default=Decimal("0.0"))
    on_cashout: Mapped[Decimal] = mapped_column(DecimalType, default=Decimal("0.0"))
    received: Mapped[Decimal] = mapped_column(DecimalType, default=Decimal("0.0"))
    last_bonus: Mapped[datetime] = mapped_column(DateTime, default=datetime.now() - timedelta(hours=24))
    referral_link: Mapped[str] = mapped_column(String(128))
    is_invited: Mapped[bool] = mapped_column(Boolean, default=False)
    start_message: Mapped[str] = mapped_column(String(128))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_unsubscribed: Mapped[bool] = mapped_column(Boolean, default=False)


class WithdrawalRequest(Base):
    __tablename__ = 'withdrawal_requests'
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger)
    amount: Mapped[Decimal] = mapped_column(DecimalType, default=Decimal("0.0"))
    status: Mapped[str] = mapped_column(String(128), default='waiting')


class Channel(Base):
    __tablename__ = 'channels'
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger)
    link: Mapped[str] = mapped_column(String(128))


class Setting(Base):
    __tablename__ = 'settings'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    value: Mapped[Decimal] = mapped_column(DecimalType, default=Decimal("0.0"))
    bool_value: Mapped[bool] = mapped_column(Boolean, default=True)
    link: Mapped[str] = mapped_column(String(128))


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
