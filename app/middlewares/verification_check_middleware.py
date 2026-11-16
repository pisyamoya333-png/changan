import app.database.requests as rq

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from typing import Callable, Dict, Any, Awaitable


class VerificationCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id

        user = await rq.get_user_info(user_id)

        if user.is_verified:
            await event.answer('<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Вы уже проходили верификацию')
            return

        return await handler(event, data)