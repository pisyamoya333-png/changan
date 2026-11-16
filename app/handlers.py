import app.keyboards as kb
import app.database.requests as rq
import app.payment.payment_api as pm

from app.middlewares.subscription_middleware import SubscriptionMiddleware
from app.middlewares.user_check_middleware import UserCheckMiddleware
from app.middlewares.captcha_middleware import CaptchaMiddleware
from app.middlewares.verification_check_middleware import VerificationCheckMiddleware
from app.middlewares.admin_check_middleware import AdminCheckMiddleware
from app.middlewares.throttle_middleware import ThrottleMiddleware

from aiogram import F, Router
from aiogram.filters import CommandStart, StateFilter, Command, ChatMemberUpdatedFilter
from aiogram.filters.chat_member_updated import KICKED, LEFT
from aiogram.types import (
    Message, CallbackQuery, FSInputFile, ChatMemberUpdated,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
    MessageEntity, InlineKeyboardMarkup, InlineKeyboardButton,
    SwitchInlineQueryChosenChat
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from datetime import timedelta
from time import time
from asyncio import gather, Semaphore
from decimal import Decimal, InvalidOperation
from html import escape
from re import sub, escape as re_escape
from json import loads
from os import path, remove
from ast import literal_eval
from functions import check_subscription, generate_captcha
from config import bot, bot_name, required_channel_id, owner_required_channel_id, payfrom_channel_id, helper_username


router_verification = Router()
router = Router()
router_admin = Router()

router_verification.message.middleware(ThrottleMiddleware(limit=1))
router_verification.callback_query.middleware(ThrottleMiddleware(limit=1))
router_verification.message.middleware(UserCheckMiddleware())
router_verification.callback_query.middleware(UserCheckMiddleware())
router_verification.message.middleware(VerificationCheckMiddleware())
router_verification.callback_query.middleware(VerificationCheckMiddleware())

router.message.middleware(ThrottleMiddleware(limit=1))
router.callback_query.middleware(ThrottleMiddleware(limit=1))
router.message.middleware(UserCheckMiddleware())
router.callback_query.middleware(UserCheckMiddleware())
router.message.middleware(CaptchaMiddleware())
router.callback_query.middleware(CaptchaMiddleware())
router.message.middleware(SubscriptionMiddleware())
router.callback_query.middleware(SubscriptionMiddleware())

router_admin.message.middleware(ThrottleMiddleware(limit=1))
router_admin.callback_query.middleware(ThrottleMiddleware(limit=1))
router_admin.message.middleware(AdminCheckMiddleware())
router_admin.callback_query.middleware(AdminCheckMiddleware())


class AddChannelState(StatesGroup):
    waiting_for_channel_data = State()


class DeleteChannelState(StatesGroup):
    waiting_for_channel_id = State()


class ChangeMinCashoutState(StatesGroup):
    waiting_for_min_cashout_id = State()


class ChangeInvitationBonusState(StatesGroup):
    waiting_for_invitation_bonus_id = State()


class ChangeDailyBonusState(StatesGroup):
    waiting_for_daily_bonus_id = State()


class MailingState(StatesGroup):
    waiting_for_mailing_id = State()
    waiting_for_confirmation = State()


class CashoutState(StatesGroup):
    waiting_for_cashout_id = State()


class TopUpBotBalanceState(StatesGroup):
    waiting_for_topup_bot_balance_id = State()


class VerificationState(StatesGroup):
    waiting_for_captcha = State()


@router_verification.callback_query(F.data == 'verification')
async def verification(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    captcha_text, captcha_path = await generate_captcha(user_id)
    await state.update_data(captcha_text=captcha_text)

    try:
        await callback.message.answer_photo(
            photo=FSInputFile(captcha_path),
            caption="<tg-emoji emoji-id=\"5881806211195605908\">🚀</tg-emoji> Пожалуйста, пройдите <b>CAPTCHA</b> для продолжения использования бота!"
        )
    finally:
        if path.exists(captcha_path):
            remove(captcha_path)

    await state.set_state(VerificationState.waiting_for_captcha)
    await callback.answer()


@router_verification.message(VerificationState.waiting_for_captcha)
async def check_captcha(message: Message, state: FSMContext):
    user_id = message.from_user.id

    data = await state.get_data()
    correct_captcha = data.get("captcha_text")

    if not message.text:
        await message.answer("<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Пожалуйста, отправьте текст с капчи")
        return

    if message.text.strip().upper() == correct_captcha.upper():
        await state.clear()
        await rq.update_user_is_verified(user_id, True)

        is_subscribed = await check_subscription(user_id)
        if not (is_subscribed in ['member', 'administrator', 'creator']):
            await message.answer(
                "<b><tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Верификация пройдена\n\n<tg-emoji emoji-id=\"5274099962655816924\">❗️</tg-emoji> Чтобы продолжить, необходимо подписаться на каналы</b>",
                reply_markup=await kb.channels_for_authorization_btn()
            )
        else:
            await message.answer(
                "<b><tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Верификация пройдена. Добро пожаловать в бота!</b>",
                reply_markup=await kb.main_keyboard(user_id)
            )

    else:
        await message.answer("<b><tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Капча не пройдена. Генерирую другую...</b>")

        captcha_text, captcha_path = await generate_captcha(user_id)
        await state.update_data(captcha_text=captcha_text)

        try:
            await message.answer_photo(
                photo=FSInputFile(captcha_path),
                caption="<tg-emoji emoji-id=\"5881806211195605908\">🚀</tg-emoji> Пройдите <b>CAPTCHA</b> для продолжения использования бота"
            )
        finally:
            if path.exists(captcha_path):
                remove(captcha_path)


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id

    await message.answer(
        f'''<tg-emoji emoji-id=\"5879814368572478751\">⌨️</tg-emoji> Меню''', 
        reply_markup=await kb.main_keyboard(user_id)
        )
    

@router.callback_query(F.data == 'cashout')
async def cashout(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)

    withdrawal_status = await rq.get_setting_bool_value('withdrawal_status')

    if not(withdrawal_status):
        await callback.message.answer(f'''<tg-emoji emoji-id=\"5774077015388852135\">🚫</tg-emoji> <b>На данный момент вывод средств недоступен.</b>''')
        return

    user_id = callback.from_user.id
    min_cashout = await rq.get_setting_value('min_cashout')
    user = await rq.get_user_info(user_id)
    
    if user.balance >= min_cashout:
        await callback.message.answer(f'''<b><tg-emoji emoji-id=\"5879814368572478751\">⌨️</tg-emoji> Укажите сумму для вывода</b>''',
                                      reply_markup=kb.process_channel_data_cancel_btn)
        await state.set_state(CashoutState.waiting_for_cashout_id)
    else:
        await callback.answer(f'<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Минимальная сумма для вывода: {min_cashout} USDT', show_alert=True)
    await callback.answer() 


@router.message(CashoutState.waiting_for_cashout_id)
async def process_cashout(message: Message, state: FSMContext):
    cashout_value = message.text
    user_id = message.from_user.id
    min_cashout_value = await rq.get_setting_value('min_cashout')
    user = await rq.get_user_info(user_id)

    if not ((await bot.get_chat(user_id)).username):
        await message.answer(
            '''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Пожалуйста, укажите username в настройках Telegram.\n
Согласно правилам бота, для вывода средств наличие username обязательно.</b>''', 
        )
        await state.clear()
        return 

    try:
        cashout_value = Decimal(cashout_value)
    except InvalidOperation:
        await message.answer(
'<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Неправильное значение!\n\nУбедитесь, что вы ввели число, и повторите попытку.</b>',
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return
    
    if cashout_value.as_tuple().exponent < -4:
        await message.answer(
            f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Число не должно содержать более 4 знаков после точки.</b>''', 
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return
    
    if cashout_value < min_cashout_value:
        await message.answer(
            f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Минимальная сумма для вывода: {min_cashout_value} USDT</b>''', 
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return
    
    if cashout_value > user.balance:
        await message.answer(
            f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>На вашем балансе недостаточно средств.</b>''', 
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return

    await rq.update_user_on_cashout(user_id, cashout_value)
    await rq.update_user_balance(user_id, -cashout_value)

    await state.clear()

    withdrawal_request_id = await rq.set_withdrawal_request(user_id, cashout_value)

    admin_ids = await rq.get_all_admins()

    for admin_id in admin_ids:
        await bot.send_message(admin_id, 
                               f'''<b><tg-emoji emoji-id=\"5409048419211682843\">💸</tg-emoji> Новая заявка на вывод!</b>\n
<tg-emoji emoji-id=\"6030687898141987254\">👨‍💻</tg-emoji> От @{(await bot.get_chat(user_id)).username} | <code>{user_id}</code>
🪙 На сумму: <b>{cashout_value} USDT</b>''',
                               reply_markup=await kb.acceptance_btn(withdrawal_request_id))

    await message.answer(
            f'''<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Вы успешно подали заявку на вывод средств.\n
<b>Обработка занимает до 48 часов. Вы получите уведомление о статусе вашей заявки. Хорошего дня, от {bot_name} <tg-emoji emoji-id=\"5994417835630137549\">💘</tg-emoji></b>\n'''
        )


@router_admin.callback_query(F.data.startswith("approve:") | F.data.startswith("reject:"))
async def accept_request(callback: CallbackQuery):
    data = callback.data.split(":")

    withdrawal_request_id = int(data[1])
    withdrawal_request = await rq.get_withdrawal_request_info(withdrawal_request_id)
    status_withdrawal_request = withdrawal_request.status

    if status_withdrawal_request != 'waiting':
        await callback.answer("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Заявка уже была обработана!", show_alert=True)
        await callback.message.edit_reply_markup()
        return
    
    user_id = withdrawal_request.tg_id
    cashout_value = withdrawal_request.amount

    if data[0] == "approve":
        try:
            check = await pm.create_check(float(cashout_value))

            try:
                await bot.send_message(user_id, f'''<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Ваша заявка на вывод <b>{cashout_value} USDT подтверждена</b>!''', reply_markup=await kb.check_btn(check[0]))
                chat = await bot.get_chat(user_id)
                await bot.send_message(payfrom_channel_id, f'''<tg-emoji emoji-id=\"5409048419211682843\">💸</tg-emoji> Выплата на сумму <b>{cashout_value} USDT</b> пользователю <b>{f"@{chat.username}" if chat.username else escape(chat.full_name)}</b>''')
                
                await rq.update_user_on_cashout(user_id, -cashout_value)
                await rq.update_user_received(user_id, cashout_value)
                await rq.update_withdrawal_request_status(withdrawal_request_id, 'approved')
                        
                await callback.message.edit_reply_markup(reply_markup=kb.approved_btn)
                await callback.answer("Заявка подтверждена!")

            except Exception as e:
                await callback.message.answer(f'Не удалось отправить сообщение с чеком пользователю. Чек не удален.\n\nОшибка: {e}', parse_mode=None)

        except Exception as e:
            try:
                error_name = loads(literal_eval(str(e))[1])["error"]["name"]
            except:
                await callback.message.answer(f"Ошибка: {e}", parse_mode=None)
                return
            
            if error_name == 'NOT_ENOUGH_COINS' or error_name == 'INSUFFICIENT_FUNDS':
                await callback.answer("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Недостаточно средств!")
            else:
                await callback.message.answer(f"Ошибка: {e}", parse_mode=None)
        
    elif data[0] == "reject": 
        await rq.update_user_on_cashout(user_id, -cashout_value)
        # await rq.update_user_balance(user_id, cashout_value) # возврат средств
        await rq.update_withdrawal_request_status(withdrawal_request_id, 'rejected')

        await callback.message.edit_reply_markup(reply_markup=kb.rejected_btn)
        await callback.answer("Заявка отклонена!")

        try:
            await bot.send_message(user_id, f'''<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Ваша заявка на вывод <b>{cashout_value} USDT отклонена</b>!''')
        except:
            pass

    await callback.answer()


@router_admin.callback_query(F.data == 'approved')
async def approved(callback: CallbackQuery):
    await callback.answer()


@router_admin.callback_query(F.data == 'rejected')
async def rejected(callback: CallbackQuery):
    await callback.answer()


@router.message(F.text == 'Профиль')
async def profile_information(message: Message):
    user_id = message.from_user.id
    user = await rq.get_user_info(user_id)

    await message.answer(
        f'''<tg-emoji emoji-id=\"5904630315946611415\">👤</tg-emoji> Ваш профиль:\n
∟ <tg-emoji emoji-id=\"5886437972647088483\">🆔</tg-emoji> Ваш ID: {user_id}
∟ <tg-emoji emoji-id=\"5769126056262898415\">💰</tg-emoji> Ваш баланс: {user.balance} USDT
    <blockquote>∟ Выведено: {user.received} USDT</blockquote>\n
<tg-emoji emoji-id=\"6032609071373226027\">👥</tg-emoji> Число приглашённых рефералов: {user.invitations}''', 
        reply_markup=kb.cashout_btn
        )
    


@router.message(F.text == 'Заработать')
async def earning(message: Message):
    user_id = message.from_user.id
    user = await rq.get_user_info(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Пригласить друга',
                switch_inline_query_chosen_chat=SwitchInlineQueryChosenChat(
                    query='',
                    allow_user_chats=True,
                    allow_group_chats=True
                )
            )
        ]
    ])

    await message.answer(
        f'''<tg-emoji emoji-id="5409048419211682843">💸</tg-emoji> За каждого приглашенного друга ты получишь {await rq.get_setting_value("invitation_bonus")} USDT

<tg-emoji emoji-id="5936143551854285132">📊</tg-emoji> После приглашения, средства будут автоматически зачислены на твой баланс.

<tg-emoji emoji-id="5271604874419647061">🔗</tg-emoji> Ссылка для приглашения: {user.referral_link}

<blockquote><tg-emoji emoji-id="6032609071373226027">👥</tg-emoji> Всего пригласил: {user.invitations} человек</blockquote>''',
        reply_markup=keyboard,
        disable_web_page_preview=True
    )



@router.message(F.text == 'Информация о проекте')
async def info(message: Message):

    await message.answer(
        f'''<b><tg-emoji emoji-id=\"6030687898141987254\">👨‍💻</tg-emoji> Информация о проекте:</b>\n
— <tg-emoji emoji-id=\"5409048419211682843\">💸</tg-emoji> Выплачено всего: {await rq.get_total_received()}
— <tg-emoji emoji-id=\"5447410659077661506\">🫂</tg-emoji> Пользователей: {await rq.get_user_count()} шт.''',
        reply_markup=await kb.info_btn()
        )
    

@router.callback_query(F.data == 'developer')
async def developer(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(f'''<b><tg-emoji emoji-id=\"5440660757194744323\">‼️</tg-emoji> Если хочешь такого же бота, обращайся ко мне <tg-emoji emoji-id=\"5348390385636883361\">⬇️</tg-emoji></b>''', reply_markup=kb.order_btn)


@router.message(F.text == 'Тех. поддержка')
async def help(message: Message):

    await message.answer(
        f'''<tg-emoji emoji-id=\"5436113877181941026\">❓</tg-emoji> При обнаружении багов/ошибок/недоработок обращайтесь к администрации.\n
<b>Администрация — @{helper_username}</b>
Ответ поступит в самое ближайшее время <tg-emoji emoji-id=\"5935824500208702046\">😉</tg-emoji>'''
        )
    

@router.message(F.text == 'ПОЛУЧИТЬ 10$ ЗА РЕГИСТРАЦИЮ!')
async def gift(message: Message):
    gift_message = await rq.get_setting_link('gift_message')

    if gift_message:
        await message.answer(gift_message)
    else:
        await message.answer(
            'Пока сообщение не настроено. Администратор может установить его командой '
            '<code>/gifttext ваш текст</code>.'
        )


@router.message(F.text == 'Ежедневный бонус')
async def daily_bonus(message: Message):
    user_id = message.from_user.id
    daily_bonus = await rq.get_setting_value('daily_bonus')
    cooldown = await rq.check_cooldown(user_id)

    if cooldown[0]:
        await rq.update_user_balance(user_id, daily_bonus)
        await rq.update_user_last_bonus(user_id)
        await message.answer(f'''<tg-emoji emoji-id=\"5904462880941545555\">🎁</tg-emoji> <b>Вам был начислен ежедневный бонус в размере {daily_bonus} USDT!</b>''')
    else:
        await message.answer(f'''<tg-emoji emoji-id=\"5891211339170326418\">⏳</tg-emoji> <b>Приходите через {cooldown[1]} для получения ежедневного бонуса!</b>''')


@router.callback_query(F.data == 'top')
async def top(callback: CallbackQuery):
    await callback.answer()

    top_users = await rq.get_top_users_by_invitations()
    response_parts = ["<tg-emoji emoji-id=\"6032594876506312598\">🏆</tg-emoji> <b>Топ 5 по приглашениям:</b>\n\n"]

    semaphore = Semaphore(30)

    async def fetch_user_info(index, user_id, invitations):
        try:
            async with semaphore:
                chat = await bot.get_chat(user_id)
                if chat.username:
                    return f'{index}. <a href="https://t.me/{chat.username}">{escape(chat.full_name)}</a> — <b>{invitations}</b> шт.\n'
                else:
                    return f'{index}. {escape(chat.full_name)} — <b>{invitations}</b> шт.\n'
        except Exception:
            return None

    tasks = [
        fetch_user_info(index, user_id, invitations)
        for index, (user_id, invitations) in enumerate(top_users.items(), start=1)
    ]
    results = await gather(*tasks)
    response_parts.extend(filter(None, results))

    await callback.message.answer("".join(response_parts), disable_web_page_preview=True)


@router_admin.message(F.text == 'Админка')
async def admin_panel(message: Message):
    await message.answer(
        f'''<b><tg-emoji emoji-id=\"6030687898141987254\">👨‍💻</tg-emoji> Админ-панель:\n
<tg-emoji emoji-id=\"6032609071373226027\">👥</tg-emoji> Пользователей в боте: {await rq.get_user_count()} шт.
<tg-emoji emoji-id=\"5890925363067886150\">🔥</tg-emoji> Каналов добавлено: {await rq.get_channel_count()} шт.\n
<tg-emoji emoji-id=\"6032742198179532882\">⚙️</tg-emoji> Параметры бота:\n
<tg-emoji emoji-id=\"5904462880941545555\">🎁</tg-emoji> Реферальная награда: {await rq.get_setting_value("invitation_bonus")}
<tg-emoji emoji-id=\"5409048419211682843\">💸</tg-emoji> Ежедневный бонус: {await rq.get_setting_value("daily_bonus")}
<tg-emoji emoji-id=\"6039573425268201570\">📤</tg-emoji> Минимальный вывод: {await rq.get_setting_value("min_cashout")}</b>''',
        reply_markup=kb.admin_panel_btns)
    

@router_admin.callback_query(F.data == 'channel_management')
async def channel_management(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(f'<tg-emoji emoji-id=\"6032742198179532882\">⚙️</tg-emoji> <b>Выберите действие:</b>', 
                                     reply_markup=kb.channel_management_btns,
                                     )
    

@router_admin.callback_query(F.data == 'show_channels')
async def show_channels(callback: CallbackQuery):
    channels = await rq.get_channels_dict()
    response = f'<b>Список каналов:</b>'

    if len(channels) == 0:
        await callback.answer(f'<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Каналы не найдены')
        return

    for index, (tg_id, link) in enumerate(channels.items(), start=1):
        response += f'\n\n{index}. <code>{str(tg_id)}</code>\n{link}' 

    await callback.message.reply(response)
    await callback.answer()


@router_admin.callback_query(F.data == 'mailing')
async def mailing(callback: CallbackQuery, state: FSMContext):
    await callback.message.reply(
        '''<b><tg-emoji emoji-id=\"5879814368572478751\">⌨️</tg-emoji> Введите текст для рассылки</b>''', 
        reply_markup=kb.process_channel_data_cancel_btn
    )
    await state.set_state(MailingState.waiting_for_mailing_id)
    await callback.answer()


@router_admin.message(MailingState.waiting_for_mailing_id)
async def process_mailing(message: Message, state: FSMContext):
    text =  message.md_text
    photo = message.photo[-1].file_id if message.photo else None

    content = {"text": text, "photo": photo}
    await state.update_data(content=content)

    if photo:
        await message.answer_photo(photo=photo, caption=f'*Ваш текст для рассылки*:\n\n{text}', reply_markup=kb.mailing_btn, parse_mode='MarkdownV2')
    else:
        await message.answer(f'*Ваш текст для рассылки*:\n\n{text}', reply_markup=kb.mailing_btn, parse_mode='MarkdownV2')

    await state.set_state(MailingState.waiting_for_confirmation)


@router_admin.callback_query(F.data == "confirm_mailing", MailingState.waiting_for_confirmation)
async def confirm_mailing(callback: CallbackQuery, state: FSMContext):
    start_time = time()
    user_ids = await rq.get_all_users()
    
    data = await state.get_data()
    content = data.get("content")

    text = content.get("text")
    photo = content.get("photo")

    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer(f'Рассылка начата <tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji>\nПо завершении придет уведомление', show_alert=True)

    successful_attempts = 0
    failed_attempts = 0
    semaphore = Semaphore(30)

    async def send_message(user_id):
        nonlocal successful_attempts, failed_attempts
        try:
            async with semaphore:
                full_name = (await bot.get_chat(user_id)).full_name
                personalized_full_name = sub(r'([' + re_escape(r'[_*[\]()~`>#+-=|{}.!]') + r'])', r'\\\1', full_name)
                personalized_text = text.replace("\{user\}", personalized_full_name)

                if photo:
                    await bot.send_photo(chat_id=user_id, photo=photo, caption=personalized_text, parse_mode='MarkdownV2')
                else:
                    await bot.send_message(chat_id=user_id, text=personalized_text, parse_mode='MarkdownV2')
                successful_attempts += 1
        except:
            failed_attempts += 1

    await gather(*(send_message(user_id) for user_id in user_ids))

    end_time = time()
    total_time = timedelta(seconds=int(end_time - start_time))

    formatted_time = []
    if total_time.days:
        formatted_time.append(f"{total_time.days} д.")
    if total_time.seconds // 3600:
        formatted_time.append(f"{total_time.seconds // 3600} ч.")
    if (total_time.seconds % 3600) // 60:
        formatted_time.append(f"{(total_time.seconds % 3600) // 60} м.")
    if total_time.seconds % 60:
        formatted_time.append(f"{total_time.seconds % 60} с.")

    await callback.message.answer(f'''
<tg-emoji emoji-id=\"5881806211195605908\">🚀</tg-emoji> <b>Сообщение было успешно разослано.</b>\n
<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Успешно: {successful_attempts}
<tg-emoji emoji-id=\"5774077015388852135\">🚫</tg-emoji> Не успешно: {failed_attempts}
<tg-emoji emoji-id=\"5891211339170326418\">⌛️</tg-emoji> Потраченное время: {" ".join(formatted_time)}
''')


@router_admin.callback_query(F.data == 'command_list')
async def command_list(callback: CallbackQuery):
    await callback.message.edit_text(
        '''<b><tg-emoji emoji-id=\"5904248647972820334\">💬</tg-emoji> Доступные команды:</b>\n
<code>/info ID</code> — информация о пользователе
<code>/reset ID</code> — обнулить пользователя
<code>/gifttext ТЕКСТ</code> — изменить сообщение кнопки «ПОЛУЧИТЬ 10$ ЗА РЕГИСТРАЦИЮ!»''', reply_markup=kb.back_to_admin_panel_btn)
    await callback.answer()


@router_admin.callback_query(F.data == 'add_channel')
async def add_channel(callback: CallbackQuery, state: FSMContext): 

    await callback.message.reply(f'''<b><tg-emoji emoji-id=\"5879814368572478751\">⌨️</tg-emoji> Введите ID и ссылку канала в следующем формате:\n<code>id ссылка</code></b>\n
<i>Например, <code>-1001234567890 https://t.me/examplechannel</code></i>\n
<tg-emoji emoji-id=\"5274099962655816924\">❗️</tg-emoji> <b>Проверьте, что ID канала начинается с "-100"</b>''', reply_markup=kb.process_channel_data_cancel_btn)
    
    await state.set_state(AddChannelState.waiting_for_channel_data)
    await callback.answer()


@router_admin.message(AddChannelState.waiting_for_channel_data)
async def process_channel_data(message: Message, state: FSMContext):
    user_input = message.text
    parts = user_input.split()

    if len(parts) != 2:
        await message.answer(
            f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Пожалуйста, введите ID и ссылку канала в следующем формате:\n<code>id ссылка</code></b>\n
<i>Например, <code>-1001234567890 https://t.me/examplechannel</code></i>''', 
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return

    channel_id, channel_link = parts

    if not channel_id.startswith("-100") or not channel_id[1:].isdigit():
        await message.answer('<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b> Некорректный ID канала! Он должен начинаться с "-100"\n\nПопробуйте снова</b>',
                             reply_markup=kb.process_channel_data_cancel_btn)
        return

    if not channel_link.startswith("http"):
        await message.answer('<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Некорректная ссылка. Она должна начинаться с "http"\n\nПопробуйте снова</b>',
                             reply_markup=kb.process_channel_data_cancel_btn)
        return

    channel = await rq.get_channel_info(channel_id)

    if channel:
        await message.answer('<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Данный канал был добавлен ранее!\n\nПопробуйте снова</b>',
                             reply_markup=kb.process_channel_data_cancel_btn)
        return
    else:
        await rq.set_channel(tg_id=channel_id, link=channel_link)
        await message.answer(f'<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> <b>Канал успешно добавлен!\n\nID: <code>{channel_id}</code>\nСсылка:</b> {channel_link}')

    await state.clear()


@router_admin.callback_query(F.data == 'delete_channel')
async def delete_channel(callback: CallbackQuery, state: FSMContext): 
    channels = await rq.get_channels_dict()

    if len(channels) == 0:
        await callback.answer(f'<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Каналы не найдены')
        return

    await callback.message.reply(
        '''<b><tg-emoji emoji-id=\"5879814368572478751\">⌨️</tg-emoji> Введите ID канала, который вы хотите удалить:</b>\n
<tg-emoji emoji-id=\"5274099962655816924\">❗️</tg-emoji> <b>Проверьте, что ID канала начинается с "-100"</b>''', 
        reply_markup=kb.process_channel_data_cancel_btn
    )
    await state.set_state(DeleteChannelState.waiting_for_channel_id)
    await callback.answer()


@router_admin.message(DeleteChannelState.waiting_for_channel_id)
async def process_delete_channel(message: Message, state: FSMContext):
    channel_id = message.text.strip()

    if not channel_id.startswith("-100") or not channel_id[1:].isdigit():
        await message.answer(
            '<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Некорректный ID канала! Он должен начинаться с "-100"\n\nПопробуйте снова</b>', 
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return

    channel = await rq.get_channel_info(channel_id)
    if not channel:
        await message.answer(
            '<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Канал с таким ID не найден!\n\nПопробуйте снова</b>', 
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return
    
    # ---------- PR ----------
    user_id = message.from_user.id
    if channel_id == str(required_channel_id) and user_id != int(owner_required_channel_id):
        await message.answer(
            f'''<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> <b>У вас недостаточно прав для удаления данного канала.\n
Обратитесь к создателю и приобретите удаление канала из обязательной подписки.</b>''', 
        )
        await state.clear()
        return
    # -------------------------

    await rq.delete_channel(channel_id)
    await message.answer(
        f'<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> <b>Канал успешно удалён!\n\nID: <code>{channel_id}</code></b>', 
    )

    await state.clear()


@router.callback_query(F.data == 'process_channel_data_cancel', StateFilter(AddChannelState.waiting_for_channel_data, 
                                                                            DeleteChannelState.waiting_for_channel_id, 
                                                                            ChangeMinCashoutState.waiting_for_min_cashout_id,
                                                                            ChangeInvitationBonusState.waiting_for_invitation_bonus_id,
                                                                            ChangeDailyBonusState.waiting_for_daily_bonus_id,
                                                                            MailingState.waiting_for_mailing_id,
                                                                            MailingState.waiting_for_confirmation,
                                                                            CashoutState.waiting_for_cashout_id,
                                                                            TopUpBotBalanceState.waiting_for_topup_bot_balance_id))
async def process_channel_data_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer('<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji>')


@router_admin.callback_query(F.data == 'setting_up_accruals')
async def setting_up_accruals(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(f'<tg-emoji emoji-id=\"6032742198179532882\">⚙️</tg-emoji> <b>Выберите действие:</b>', 
                                     reply_markup=kb.setting_up_accruals_btns,
                                     )


@router_admin.callback_query(F.data == 'change_invitation_bonus')
async def change_invitation_bonus(callback: CallbackQuery, state: FSMContext):
    await callback.message.reply(
        '''<b><tg-emoji emoji-id=\"5879814368572478751\">⌨️</tg-emoji> Введите значение для реферальной награды</b>''', 
        reply_markup=kb.process_channel_data_cancel_btn
    )
    await state.set_state(ChangeInvitationBonusState.waiting_for_invitation_bonus_id)
    await callback.answer()


@router_admin.message(ChangeInvitationBonusState.waiting_for_invitation_bonus_id)
async def process_change_invitation_bonus(message: Message, state: FSMContext):
    invitation_bonus_value = message.text

    try:
        invitation_bonus_value = Decimal(invitation_bonus_value)
    except InvalidOperation:
        await message.answer(
            '<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Некорректное значение!\n\nПроверьте, что ваше значение является числом и попробуйте снова</b>',
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return
    
    if invitation_bonus_value.as_tuple().exponent < -4:
        await message.answer(
            f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Число не должно содержать более 4 знаков после точки.</b>''', 
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return

    await rq.update_setting_value('invitation_bonus', invitation_bonus_value) 
    await message.answer(
        f'<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> <b>Значение успешно применено!\n\nРеферальная награда:</b> {invitation_bonus_value}', 
    )

    await state.clear()


@router_admin.callback_query(F.data == 'change_daily_bonus')
async def change_daily_bonus(callback: CallbackQuery, state: FSMContext):
    await callback.message.reply(
        '''<b><tg-emoji emoji-id=\"5879814368572478751\">⌨️</tg-emoji> Введите значение для ежедневного бонуса</b>''', 
        reply_markup=kb.process_channel_data_cancel_btn
    )
    await state.set_state(ChangeDailyBonusState.waiting_for_daily_bonus_id)
    await callback.answer()


@router_admin.message(ChangeDailyBonusState.waiting_for_daily_bonus_id)
async def process_change_daily_bonus(message: Message, state: FSMContext):
    daily_bonus_value = message.text

    try:
        daily_bonus_value = Decimal(daily_bonus_value)
    except InvalidOperation:
        await message.answer(
            '<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Некорректное значение!\n\nПроверьте, что ваше значение является числом и попробуйте снова</b>',
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return
    
    if daily_bonus_value.as_tuple().exponent < -4:
        await message.answer(
            f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Число не должно содержать более 4 знаков после точки.</b>''', 
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return

    await rq.update_setting_value('daily_bonus', daily_bonus_value) 
    await message.answer(
        f'<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> <b>Значение успешно применено!\n\nБонус:</b> {daily_bonus_value}', 
    )

    await state.clear()


@router_admin.callback_query(F.data == 'setting_up_withdrawal')
async def setting_up_withdrawal(callback: CallbackQuery):
    await callback.message.edit_text(f'<tg-emoji emoji-id=\"6032742198179532882\">⚙️</tg-emoji> <b>Выберите действие:</b>', 
                                     reply_markup=kb.setting_up_withdrawal_btns,
                                     )
    await callback.answer()


@router_admin.callback_query(F.data == 'change_min_cashout')
async def change_min_cashout(callback: CallbackQuery, state: FSMContext):
    await callback.message.reply(
        '''<b><tg-emoji emoji-id=\"5879814368572478751\">⌨️</tg-emoji> Введите минимальное значение для вывода</b>''', 
        reply_markup=kb.process_channel_data_cancel_btn
    )
    await state.set_state(ChangeMinCashoutState.waiting_for_min_cashout_id)
    await callback.answer()


@router_admin.message(ChangeMinCashoutState.waiting_for_min_cashout_id)
async def process_change_min_cashout(message: Message, state: FSMContext):
    min_cashout_value = message.text

    try:
        min_cashout_value = Decimal(min_cashout_value)
    except InvalidOperation:
        await message.answer(
            '<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Некорректное значение!\n\nПроверьте, что ваше значение является числом и попробуйте снова</b>',
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return
    
    if min_cashout_value.as_tuple().exponent < -4:
        await message.answer(
            f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Число не должно содержать более 4 знаков после точки.</b>''', 
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return

    await rq.update_setting_value('min_cashout', min_cashout_value) 
    await message.answer(
        f'<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> <b>Значение успешно применено!\n\nМинимальный вывод:</b> {min_cashout_value}', 
    )

    await state.clear()


@router_admin.callback_query(F.data == 'topup_bot_balance')
async def topup_bot_balance(callback: CallbackQuery, state: FSMContext):
    await callback.message.reply(
        '''<b><tg-emoji emoji-id=\"5879814368572478751\">⌨️</tg-emoji> Введите сумму пополнения в USDT</b>''', 
        reply_markup=kb.process_channel_data_cancel_btn
    )
    await state.set_state(TopUpBotBalanceState.waiting_for_topup_bot_balance_id)
    await callback.answer()


@router_admin.message(TopUpBotBalanceState.waiting_for_topup_bot_balance_id)
async def process_topup_bot_balance(message: Message, state: FSMContext):
    topup_bot_balance_value = message.text

    try:
        topup_bot_balance_value = Decimal(topup_bot_balance_value)
    except InvalidOperation:
        await message.answer(
            '<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Некорректное значение!\n\nПроверьте, что ваше значение является числом и попробуйте снова</b>',
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return
    
    if topup_bot_balance_value.as_tuple().exponent < -2:
        await message.answer(
            f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Число не должно содержать более 2 знаков после точки.</b>''', 
            reply_markup=kb.process_channel_data_cancel_btn
        )
        return
    
    try:
        pay_url = await pm.create_invoice(amount=float(topup_bot_balance_value))
        await message.answer(f"<b>Нажмите на кнопку и оплатите счёт</b>", reply_markup=await kb.to_pay_btn(pay_url))
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
    
    await state.clear()


@router_admin.callback_query(F.data == 'bot_balance')
async def bot_balance(callback: CallbackQuery):
    try:
        balance = await pm.get_balance()
        await callback.message.answer(f"<tg-emoji emoji-id=\"5769126056262898415\">💰</tg-emoji> <b>Баланс бота: {balance} USDT</b>")
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}")

    await callback.answer()


@router_admin.callback_query(F.data == 'prohibit_withdrawal')
async def prohibit_withdrawal(callback: CallbackQuery):
    withdrawal_status = await rq.get_setting_bool_value('withdrawal_status')

    if not(withdrawal_status):
        await rq.update_setting_bool_value('withdrawal_status', True)
        await callback.answer(f'<tg-emoji emoji-id=\"5843918217323484232\">🔓</tg-emoji> Вывод средств был открыт')

    elif withdrawal_status:
        await rq.update_setting_bool_value('withdrawal_status', False)
        await callback.answer(f'<tg-emoji emoji-id=\"5936035091045159318\">🔐</tg-emoji> Вывод средств был закрыт')

    await callback.answer()


@router_admin.message(Command('reset'))
async def delete_user_info(message: Message):
    text = message.text
    user_id = message.from_user.id

    if len(text.split()) > 1 and (text.split()[1]).isdigit():
        reset_user_id = text.split()[1]
        reset_user = await rq.get_user_info(reset_user_id)

        if user_id == int(reset_user_id):
            await message.answer(f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Вы не можете обнулить сами себя!</b>''')
            return

        if reset_user:
            await rq.reset_user_info(reset_user_id)
            await message.answer(f'''<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> <b>Пользователь @{(await bot.get_chat(reset_user_id)).username} был обнулён\n
ID: <code>{reset_user_id}</code></b>''')
        else:
            await message.answer(f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Команда введена неверно!\n
Убедитесь, что пользователь с таким ID существует
<code>/reset ID</code></b>''')
            
    else:
        await message.answer(f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Команда введена неверно!\n
Проверьте, что ваше значение является числом и попробуйте снова</b>
<code>/reset ID</code>''')



@router_admin.message(Command('gifttext'))
async def set_gift_text(message: Message):
    # Берём весь текст после команды, включая пробелы и переносы строк.
    parts = (message.text or '').split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            'Укажите текст, который будет отправляться по нажатию кнопки.\\n'
            '<code>/gifttext Ваш текст здесь</code>'
        )
        return

    gift_text = parts[1].strip()
    await rq.update_setting_link('gift_message', gift_text)
    await message.answer('✅ Текст для кнопки успешно обновлён!')


@router_admin.message(Command('info'))
async def user_info(message: Message):
    text = message.text

    if len(text.split()) > 1 and (text.split()[1]).isdigit():
        user_info_id = text.split()[1]
        user_info = await rq.get_user_info(user_info_id)

        if user_info:
            try:
                chat = await bot.get_chat(user_info_id)
            except Exception:
                await message.answer(f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Невозможно получить чат. Возможно, пользователь заблокировал бота или был деактивирован.''')
                return
            
            await message.answer(f'''<b><tg-emoji emoji-id=\"5334544901428229844\">ℹ️</tg-emoji> Информация о пользователе</b>:\n
ID: <b><code>{user_info_id}</code></b>
Username: <b>{f"@{chat.username}" if chat.username else 'отсутствует'}</b>
Админ: <b>{f'да' if user_info.is_admin else 'нет'}</b> 
Приглашений: <b>{user_info.invitations}</b> 
Баланс: <b>{user_info.balance}</b> 
На удержании: <b>{user_info.on_cashout}</b> 
Выведено: <b>{user_info.received}</b>''', reply_markup=await kb.show_referrals_btn(user_info_id))
            
        else:
            await message.answer(f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Команда введена неверно!\n
Убедитесь, что пользователь с таким ID существует
<code>/info ID</code></b>''')
            
    else:
        await message.answer(f'''<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Команда введена неверно!\n
Проверьте, что ваше значение является числом и попробуйте снова</b>
<code>/info ID</code>''')
        

@router_admin.callback_query(F.data.startswith("show_referrals:"))
async def show_referrals(callback: CallbackQuery):
    data = callback.data.split(":")
    referrer_id = int(data[1])

    referral_ids = await rq.get_referral_ids(referrer_id)
    total_referrals = len(referral_ids)

    if total_referrals == 0:
        await callback.answer('<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Рефералы не найдены')
        return
    
    await callback.answer()

    page = int(data[2]) if len(data) > 2 else 1
    page_size = 20
    total_pages = (total_referrals + page_size - 1) // page_size

    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    current_page_referrals = referral_ids[start_index:end_index]

    response_parts = [f"<tg-emoji emoji-id=\"6032609071373226027\">👥</tg-emoji> <b>Рефералы {referrer_id} ({page}/{total_pages}):</b>\n\n"]
    semaphore = Semaphore(30)

    async def fetch_referral_info(index, referral_id):
        try:
            async with semaphore:
                chat = await bot.get_chat(referral_id)
                if chat.username:
                    return f"{index}. @{chat.username} | <code>{referral_id}</code>\n"
                else:
                    return f"{index}. {escape(chat.full_name)} | <code>{referral_id}</code>\n"
        except Exception:
            return f"{index}. Пользователь <code>{referral_id}</code> недоступен.\n"

    tasks = [fetch_referral_info(index, referral_id) for index, referral_id in enumerate(current_page_referrals, start=start_index + 1)]
    results = await gather(*tasks)
    response_parts.extend(results)

    await callback.message.edit_text("".join(response_parts), reply_markup=await kb.get_keyboard_show_referrals(referrer_id, page, total_pages), disable_web_page_preview=True)


@router_admin.callback_query(F.data == 'back_to_admin_panel')
async def admin_panel(callback: CallbackQuery):
    await callback.message.edit_text(
        f'''<b><tg-emoji emoji-id=\"6030687898141987254\">👨‍💻</tg-emoji> Админ-панель:\n
<tg-emoji emoji-id=\"6032609071373226027\">👥</tg-emoji> Пользователей в боте: {await rq.get_user_count()} шт.
<tg-emoji emoji-id=\"5890925363067886150\">🔥</tg-emoji> Каналов добавлено: {await rq.get_channel_count()} шт.\n
<tg-emoji emoji-id=\"6032742198179532882\">⚙️</tg-emoji> Параметры бота:\n
<tg-emoji emoji-id=\"5904462880941545555\">🎁</tg-emoji> Реферальная награда: {await rq.get_setting_value("invitation_bonus")}
<tg-emoji emoji-id=\"5409048419211682843\">💸</tg-emoji> Ежедневный бонус: {await rq.get_setting_value("daily_bonus")}
<tg-emoji emoji-id=\"6039573425268201570\">📤</tg-emoji> Минимальный вывод: {await rq.get_setting_value("min_cashout")}</b>''',
        reply_markup=kb.admin_panel_btns)
    await callback.answer()


@router.callback_query(F.data == 'check_subscription_cb')
async def check_subscription_cb(callback: CallbackQuery):
    user_id = callback.from_user.id

    await callback.message.answer(
        f'''<b><tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Вы подписаны на все каналы</b>''', 
        reply_markup=await kb.main_keyboard(user_id), 
        )
    await callback.answer()


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=LEFT))
@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def user_left(event: ChatMemberUpdated):
    user_id = event.from_user.id
    user = await rq.get_user_info(user_id)

    if user is None:
        return

    start_message = user.start_message
    if len(start_message.split()) > 1 and user.is_invited and user.is_verified and not user.is_unsubscribed:
        invitation_bonus = await rq.get_setting_value('invitation_bonus')
        referrer_id = start_message.split()[1]
                
        await rq.update_user_balance(referrer_id, -invitation_bonus)
        await rq.update_user_is_unsubscribed(user_id, True)

        reason = "отписался от канала из ОП" if event.new_chat_member.status == "left" else "заблокировал бота"

        try:
            get_chat = await bot.get_chat(user_id)
            await bot.send_message(referrer_id, f'''<tg-emoji emoji-id=\"5774077015388852135\">🚫</tg-emoji> С вашего баланса было <b>списано {invitation_bonus} USDT</b>!\n
<blockquote><b>Причина</b>: ваш реферал <b>{escape(get_chat.full_name)}</b> {reason}</blockquote>''')
        except:
            pass


@router.inline_query()
async def invite_friend(inline_query: InlineQuery):
    user_id = inline_query.from_user.id
    user = await rq.get_user_info(user_id)

    if not user:
        await inline_query.answer([], cache_time=0)
        return

    result = InlineQueryResultArticle(
        id='invite_friend',
        title='💸 Чек на 10$',
        description='Отправить приглашение другу',
        input_message_content=InputTextMessageContent(
            message_text='💸 Чек на 10$',
            parse_mode=None,
            entities=[
                MessageEntity(
                    type='custom_emoji',
                    offset=0,
                    length=2,
                    custom_emoji_id='5409048419211682843'
                )
            ]
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text='Получить',
                        url=user.referral_link
                    )
                ]
            ]
        )
    )

    await inline_query.answer(
        results=[result],
        cache_time=0,
        is_personal=True
    )