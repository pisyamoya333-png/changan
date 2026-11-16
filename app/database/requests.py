from app.database.models import async_session
from app.database.models import User, WithdrawalRequest, Channel, Setting
from sqlalchemy import select, desc, func

from datetime import datetime, timedelta
from decimal import Decimal
from config import bot_username


async def set_user(
    tg_id, is_admin=False, invitations=0, balance=Decimal("0.0"), 
    on_cashout=Decimal("0.0"), received=Decimal("0.0"), last_bonus=None, referral_link='', 
    is_invited=False, start_message='', is_verified=False, is_unsubscribed=False
):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        referral_link = f'https://t.me/{bot_username}?start={tg_id}'

        if not user:
            new_user = User(
                tg_id=tg_id,
                is_admin=is_admin,
                invitations=invitations,
                balance=balance,
                on_cashout=on_cashout,
                received=received,
                last_bonus=last_bonus,
                referral_link=referral_link,
                is_invited=is_invited,
                start_message=start_message,
                is_verified=is_verified,
                is_unsubscribed=is_unsubscribed
            )
            session.add(new_user)
            await session.commit()


async def set_withdrawal_request(tg_id, amount, status='waiting'):
    async with async_session() as session:
        new_withdrawal_request = WithdrawalRequest(
            tg_id=tg_id,
            amount=amount,
            status=status
        )
        session.add(new_withdrawal_request)
        await session.flush()
        withdrawal_request = new_withdrawal_request.id
        await session.commit()
    return withdrawal_request


async def set_channel(tg_id, link=''):
    async with async_session() as session:
        channel = await session.scalar(select(Channel).where(Channel.tg_id == tg_id))

        if not channel:
            new_channel = Channel(
                tg_id=tg_id,
                link=link
            )
            session.add(new_channel)
            await session.commit()


async def set_setting(name, value, bool_value=True, link=''):
    async with async_session() as session:
        setting = await session.scalar(select(Setting).where(Setting.name == name))

        if not setting:
            new_setting = Setting(
                name=name,
                value=Decimal(value),
                bool_value=bool_value,
                link=link
            )
            session.add(new_setting)
            await session.commit()


async def get_user_info(tg_id):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalars().first()
        return user
    

async def get_channel_info(tg_id):
    async with async_session() as session:
        result = await session.execute(select(Channel).where(Channel.tg_id == tg_id))
        channel = result.scalars().first()
        return channel
    

async def get_setting_info(name):
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.name == name))
        setting = result.scalars().first()

        if not setting:
            new_setting = Setting(
                name=name,
                value=Decimal("0.0"),
                bool_value=True,
                link=''
            )
            session.add(new_setting)
            await session.commit()
            await session.refresh(new_setting)

        return setting
    

async def get_withdrawal_request_info(id):
    async with async_session() as session:
        result = await session.execute(select(WithdrawalRequest).where(WithdrawalRequest.id == id))
        withdrawal_request = result.scalars().first()
        return withdrawal_request
    

async def delete_channel(tg_id):
    async with async_session() as session:
        channel = await session.scalar(select(Channel).where(Channel.tg_id == tg_id))
        if channel:
            await session.delete(channel)
            await session.commit()


async def get_setting_value(name):
    async with async_session() as session:
        setting = await session.scalar(select(Setting).where(Setting.name == name))

        if not setting:
            new_setting = Setting(
                name=name,
                value=Decimal("0.0"),
                bool_value=True,
                link=''
            )
            session.add(new_setting)
            await session.commit()
            await session.refresh(new_setting)
            return new_setting.value

        return setting.value


async def get_setting_link(name):
    async with async_session() as session:
        setting = await session.scalar(select(Setting).where(Setting.name == name))

        if not setting:
            new_setting = Setting(
                name=name,
                value=Decimal("0.0"),
                bool_value=True,
                link=''
            )
            session.add(new_setting)
            await session.commit()
            await session.refresh(new_setting)
            return new_setting.link

        return setting.link
    

async def get_setting_bool_value(name):
    async with async_session() as session:
        setting = await session.scalar(select(Setting).where(Setting.name == name))

        if not setting:
            new_setting = Setting(
                name=name,
                value=Decimal("0.0"),
                bool_value=True,
                link=''
            )
            session.add(new_setting)
            await session.commit()
            await session.refresh(new_setting)
            return new_setting.bool_value

        return setting.bool_value


async def update_setting_value(name, value):
    async with async_session() as session:
        setting = await session.scalar(select(Setting).where(Setting.name == name))

        if not setting:
            new_setting = Setting(
                name=name,
                value=Decimal(value),
                bool_value=True,
                link=''
            )
            session.add(new_setting)
        else:
            setting.value = Decimal(value)

        await session.commit()


async def update_setting_link(name, link):
    async with async_session() as session:
        setting = await session.scalar(select(Setting).where(Setting.name == name))

        if not setting:
            new_setting = Setting(
                name=name,
                value=Decimal("0.0"),
                bool_value=True,
                link=link
            )
            session.add(new_setting)
        else:
            setting.link = link

        await session.commit()


async def update_setting_bool_value(name, bool_value):
    async with async_session() as session:
        setting = await session.scalar(select(Setting).where(Setting.name == name))

        if not setting:
            new_setting = Setting(
                name=name,
                value=Decimal("0.0"),
                bool_value=bool_value,
                link=''
            )
            session.add(new_setting)
        else:
            setting.bool_value = bool_value

        await session.commit()


async def update_withdrawal_request_status(id, status):
    async with async_session() as session:
        withdrawal_request = await session.scalar(select(WithdrawalRequest).where(WithdrawalRequest.id == id))
        withdrawal_request.status = status 
        await session.commit()


async def update_user_invitations(referrer_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == referrer_id))
        user.invitations += 1
        await session.commit()


async def update_user_is_admin(tg_id, bool):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        user.is_admin = bool
        await session.commit()
    

async def update_user_balance(tg_id, amount):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        user.balance = user.balance + Decimal(amount)
        await session.commit()


async def update_user_on_cashout(tg_id, amount):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        user.on_cashout = user.on_cashout + Decimal(amount)
        await session.commit()
        

async def update_user_is_invited(tg_id, bool):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        user.is_invited = bool
        await session.commit()


async def update_user_start_message(tg_id, start_message):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        user.start_message = start_message
        await session.commit()


async def update_user_received(tg_id, amount):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        user.received = user.received + Decimal(amount)
        await session.commit()


async def update_user_last_bonus(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        user.last_bonus = datetime.now()
        await session.commit()


async def update_user_is_verified(tg_id, bool):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        user.is_verified = bool
        await session.commit()


async def update_user_is_unsubscribed(tg_id, bool):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        user.is_unsubscribed = bool
        await session.commit()


async def check_cooldown(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        last_bonus = user.last_bonus

        current_time = datetime.now()
        cooldown_time = last_bonus + timedelta(hours=24)

        if current_time >= cooldown_time:
            return [True, "Кулдаун завершён!"]
        else:
            remaining_time = cooldown_time - current_time

            total_seconds = int(remaining_time.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            time_parts = []
            if hours > 0:
                time_parts.append(f"{hours} ч.")
            if minutes > 0:
                time_parts.append(f"{minutes} мин.")
            if seconds > 0:
                time_parts.append(f"{seconds} сек.")

            remaining_str = " ".join(time_parts)
            return [False, remaining_str]


async def get_all_users():
    async with async_session() as session:
        result = await session.scalars(select(User.tg_id))
        return result.all()
    

async def get_all_admins():
    async with async_session() as session:
        result = await session.scalars(select(User.tg_id).filter(User.is_admin == True))
        return result.all()
    

async def get_top_users_by_invitations(limit: int = 5):
    async with async_session() as session:
        result = await session.execute(select(User.tg_id, User.invitations).order_by(desc(User.invitations)).limit(limit))
        top_users = {row.tg_id: row.invitations for row in result.fetchall()}
        return top_users
    

async def get_channels_dict():
    async with async_session() as session:
        result = await session.execute(select(Channel.tg_id, Channel.link))
        channels = result.all()
        channels_dict = {tg_id: link for tg_id, link in channels}
        return channels_dict


async def get_user_count():
    async with async_session() as session:
        result = await session.execute(select(func.count(User.tg_id)))
        user_count = result.scalar()
        return user_count
    

async def get_channel_count():
    async with async_session() as session:
        result = await session.execute(select(func.count(Channel.tg_id)))
        channel_count = result.scalar()
        return channel_count
    

async def get_total_received():
    async with async_session() as session:
        result = await session.execute(select(func.sum(User.received))) 
        total_received = result.scalar()
        return (format(Decimal(total_received or 0).quantize(Decimal('0.0001')).normalize(), 'f'))
    

async def reset_user_info(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        user.is_admin = False
        user.invitations = 0
        user.balance = Decimal("0.0")
        user.on_cashout = Decimal("0.0")
        user.received = Decimal("0.0")
        user.last_bonus = datetime.now()
        await session.commit()
    

async def get_referral_ids(referrer_id):
    async with async_session() as session:
        result = await session.scalars(select(User.tg_id).filter(User.start_message == f"/start {referrer_id}").filter(User.is_invited == True))
        return result.all()
    

async def get_gift_links():
    async with async_session() as session:
        result = await session.execute(select(Setting.link).where(Setting.name.like("gift_link_%")))
        return result.scalars().all()