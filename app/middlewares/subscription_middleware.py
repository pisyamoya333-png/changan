import app.keyboards as kb
import app.database.requests as rq

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from typing import Callable, Dict, Any, Awaitable
from functions import check_subscription


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id

        user = await rq.get_user_info(user_id)

        if user.is_admin:
            return await handler(event, data)

        is_subscribed = await check_subscription(user_id)
        if not (is_subscribed in ['member', 'administrator', 'creator']):
            if isinstance(event, Message):
                await event.answer(
                    '<tg-emoji emoji-id=\"5274099962655816924\">❗️</tg-emoji> <b>Чтобы продолжить, необходимо подписаться на каналы</b>',
                    parse_mode='HTML',
                    reply_markup=await kb.channels_for_authorization_btn()
                )
            elif isinstance(event, CallbackQuery):
                await event.answer('<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji>')

            return

        return await handler(event, data)