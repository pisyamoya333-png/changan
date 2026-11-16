import app.database.requests as rq

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from typing import Callable, Dict, Any, Awaitable
from functions import referral_system, check_subscription


class UserCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        user = await rq.get_user_info(user_id)
        
        if not user:
            await rq.set_user(user_id)

            user = await rq.get_user_info(user_id)

        if user.start_message == '':
            if isinstance(event, Message):
                if event.text.split()[0] == '/start' and len(event.text.split()) > 1:
                    start_message = event.text
                    await rq.update_user_start_message(user_id, start_message)
                    user = await rq.get_user_info(user_id)
                else:
                    await rq.update_user_start_message(user_id, '/start')
                    await rq.update_user_is_invited(user_id, True)
                    
            user = await rq.get_user_info(user_id)

        if not user.is_invited and user.is_verified:
            start_message = user.start_message
            is_subscribed = await check_subscription(user_id)
            if is_subscribed in ['member', 'administrator', 'creator']:
                await referral_system(user, start_message, user_id)
        
        return await handler(event, data)