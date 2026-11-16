import app.database.requests as rq

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from typing import Callable, Dict, Any, Awaitable
from app.keyboards import verification_btn


class CaptchaMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        user = await rq.get_user_info(user_id)

        if not user.is_verified:
            if isinstance(event, Message):
                await event.answer(
                    '<b><tg-emoji emoji-id=\"5774077015388852135\">🚫</tg-emoji> Доступ к боту запрещен. Подтвердите, что вы не бот!</b>',
                    reply_markup=verification_btn
                )
            elif isinstance(event, CallbackQuery):
                await event.message.answer(
                    '<b><tg-emoji emoji-id=\"5774077015388852135\">🚫</tg-emoji> Доступ к боту запрещен. Подтвердите, что вы не бот!</b>',
                    reply_markup=verification_btn
                )
            return

        return await handler(event, data)