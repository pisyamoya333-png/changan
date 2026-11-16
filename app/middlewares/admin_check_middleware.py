from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from typing import Callable, Dict, Any, Awaitable
import app.database.requests as rq

class AdminCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        user = await rq.get_user_info(user_id)

        if not(user.is_admin):
            if isinstance(event, Message):
                await event.answer("<tg-emoji emoji-id=\"5774077015388852135\">🚫</tg-emoji> <b>У вас нет прав для выполнения этой команды!</b>", parse_mode='HTML')
            elif isinstance(event, CallbackQuery):
                await event.answer("<tg-emoji emoji-id=\"5774077015388852135\">🚫</tg-emoji> У вас нет прав для выполнения этого действия!", show_alert=True)
            return 
        
        return await handler(event, data)
