import asyncio
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Message, CallbackQuery

class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 1):
        super().__init__()
        self.limit = limit
        self.rate_limit = {}

    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if user_id is not None:
            current_time = asyncio.get_event_loop().time()
            if user_id in self.rate_limit and current_time - self.rate_limit[user_id] < self.limit:
                if isinstance(event, Message):
                    sent_message = await event.answer("<tg-emoji emoji-id=\"5891211339170326418\">⏳</tg-emoji> Не так быстро! Пожалуйста, подождите.")
                    await asyncio.sleep(3)
                    await event.delete()
                    await sent_message.delete()
                elif isinstance(event, CallbackQuery):
                    await event.answer("<tg-emoji emoji-id=\"5891211339170326418\">⏳</tg-emoji> Пожалуйста, подождите")
                return

            self.rate_limit[user_id] = current_time

        return await handler(event, data)