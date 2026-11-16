import app.database.requests as rq

from config import bot, logger
from html import escape
from captcha.image import ImageCaptcha
from random import choices
from aiogram.exceptions import TelegramNetworkError


async def get_channel_title(channel_id):
    try:
        chat = await bot.get_chat(channel_id)
        return chat.title
    except Exception as e:
        return 'Подпишись'


async def check_subscription(user_id):
    channels_dict = await rq.get_channels_dict()

    if not channels_dict:
        return 'member'

    for channel_id in channels_dict.keys():
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if not (member.status in ['member', 'administrator', 'creator']):
                return 'left'
        except TelegramNetworkError as e:
            continue
        except TimeoutError as e:
            continue
        except Exception as e:
            logger.error(f"Произошла ошибка: {e}", exc_info=True)
            await rq.delete_channel(channel_id)

            admin_ids = await rq.get_all_admins()
            for admin_id in admin_ids:
                await bot.send_message(
                    admin_id,
                    f'''<b><tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Канал с ID <code>{channel_id}</code> был удален из ОП.\n
<blockquote>Пригласите бота в администраторы канала и добавьте канал снова.</blockquote></b>'''
                )
            continue

    return 'member'
    

async def referral_system(user, start_message, user_id):
    if not(user.is_invited):
        if len(start_message.split()) > 1:
            referrer_id = start_message.split()[1]
            referrer = await rq.get_user_info(referrer_id)

            if referrer and str(referrer_id) != str(user_id):
                await rq.update_user_invitations(referrer_id)
                await rq.update_user_balance(referrer_id, (await rq.get_setting_value("invitation_bonus")))

                referrer = await rq.get_user_info(referrer_id)

                try:
                    get_chat = await bot.get_chat(user_id)

                    await bot.send_message(chat_id=referrer_id, text=f'''<tg-emoji emoji-id=\"6041731551845159060\">🎉</tg-emoji> <b>По вашей ссылке был приглашен пользователь {escape(get_chat.full_name)}! Вам было начислено {await rq.get_setting_value("invitation_bonus")} USDT\n
Баланс: {referrer.balance} USDT</b>''')
                except:
                    pass
            
            else:
                await rq.update_user_start_message(user_id, '/start')
                    
        await rq.update_user_is_invited(user_id, True)


async def generate_captcha(user_id):
    characters = "АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ0123456789"
    captcha_text = ''.join(choices(characters, k=7))

    image_captcha = ImageCaptcha(width=300, height=120)
    image = image_captcha.generate_image(captcha_text)

    image.save(f'app/middlewares/captcha_{user_id}.png')
    return captcha_text, f'app/middlewares/captcha_{user_id}.png'