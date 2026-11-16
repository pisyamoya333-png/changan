from aiogram.types import KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from functions import get_channel_title
from app.database.requests import get_user_info, get_channels_dict


# Telegram Bot API 9.4 custom emoji button icons. The emoji is not part of
# the text sent back when a ReplyKeyboard button is pressed.
_BUTTON_EMOJI_IDS = {'‼️': '5440660757194744323', 'ℹ️': '5334544901428229844', '⌛️': '5891211339170326418', '⌨️': '5879814368572478751', '⏳': '5891211339170326418', '⚙️': '6032742198179532882', '⚠️': '5447644880824181073', '⛔️': '5260293700088511294', '✅': '5206607081334906820', '✉️': '5253742260054409879', '✨': '5325547803936572038', '❌': '5210952531676504517', '❓': '5436113877181941026', '❗️': '5274099962655816924', '➕': '5397916757333654639', '➡️': '5345844853009828446', '⬅️': '5348414733806484250', '⬇️': '5348390385636883361', '🆓': '5895669571058142797', '🆔': '5890937706803894250', '🆘': '6035191085452497972', '🍾': '6034923938486684992', '🎁': '6037175527846975726', '🎉': '6041731551845159060', '🏆': '6032594876506312598', '👇': '5348390385636883361', '👈': '6039539366177541657', '👉': '6037622221625626773', '👤': '5904630315946611415', '👥': '6032609071373226027', '👨\u200d💻': '6030687898141987254', '💎': '5836907383292436018', '💘': '5994417835630137549', '💬': '5904248647972820334', '💰': '5769126056262898415', '💳': '5805550320985578625', '💸': '5904462880941545555', '📊': '5936143551854285132', '📢': '6039422865189638057', '📤': '6039573425268201570', '🔐': '5936035091045159318', '🔓': '5843918217323484232', '🔗': '5769289093221454192', '🔙': '5895507195524550741', '🔥': '5890925363067886150', '😉': '5935824500208702046', '🚀': '5881806211195605908', '🚚': '6043896193887506430', '🚫': '5774077015388852135', '🧑\u200d💻': '6030687898141987254'}

def _button_parts(text):
    icon_id = None
    clean = text
    for emoji, custom_id in sorted(_BUTTON_EMOJI_IDS.items(), key=lambda item: len(item[0]), reverse=True):
        if emoji in clean:
            if icon_id is None:
                icon_id = custom_id
            clean = clean.replace(emoji, '')
    return clean.strip(), icon_id

def I(text, **kwargs):
    clean, icon_id = _button_parts(text)
    return InlineKeyboardButton(text=clean, icon_custom_emoji_id=icon_id, **kwargs)

def R(text, **kwargs):
    clean, icon_id = _button_parts(text)
    return KeyboardButton(text=clean, icon_custom_emoji_id=icon_id, **kwargs)

# Alias used by the inline-keyboard declarations below.
InlineR = I


async def main_keyboard(user_id):
    keyboard = ReplyKeyboardBuilder()
    keyboard.row(
        R(text='👤 Профиль'), 
        R(text='💸 Заработать')
    )
    keyboard.row(
        R(text='👨‍💻 Информация о проекте'), 
        R(text='🆘 Тех. поддержка')
    )
    keyboard.row(
        R(text='🆓 ПОЛУЧИТЬ 10$ ЗА РЕГИСТРАЦИЮ!'),
        R(text='🎁 Ежедневный бонус') 
    )

    user = await get_user_info(user_id)

    if user.is_admin:
        keyboard.row(R(text='💎 Админка 💎'))

    return keyboard.as_markup(resize_keyboard=True)


async def channels_for_authorization_btn():
    keyboard = InlineKeyboardBuilder()
    for channel_id, channel_link in (await get_channels_dict()).items():
        channel_title = await get_channel_title(channel_id)
        keyboard.add(InlineR(text=channel_title, url=channel_link))
    keyboard.add(InlineR(text='✅ Проверить', callback_data='check_subscription_cb'))
    return keyboard.adjust(1).as_markup()

    
admin_panel_btns = InlineKeyboardMarkup(inline_keyboard=[
    [InlineR(text='💬 Доступные команды', callback_data='command_list')],
    [InlineR(text='📢 Управление каналами', callback_data='channel_management')],
    [InlineR(text='⚙️ Настройка начислений', callback_data='setting_up_accruals')],
    [InlineR(text='⚙️ Настройка выводов', callback_data='setting_up_withdrawal')],
    [InlineR(text='✉️ Рассылка', callback_data='mailing')]
])


channel_management_btns = InlineKeyboardMarkup(inline_keyboard=[
    [InlineR(text='📢 Показать каналы', callback_data='show_channels')],
    [InlineR(text='➕ Добавить канал', callback_data='add_channel')],
    [InlineR(text='❌ Удалить канал', callback_data='delete_channel')],
    [InlineR(text='🔙 Назад', callback_data='back_to_admin_panel')]
])


setting_up_accruals_btns = InlineKeyboardMarkup(inline_keyboard=[
    [InlineR(text='🎁 Изменить реферальную награду', callback_data='change_invitation_bonus')],
    [InlineR(text='💸 Изменить ежедневный бонус', callback_data='change_daily_bonus')],
    [InlineR(text='🔙 Назад', callback_data='back_to_admin_panel')]
])


setting_up_withdrawal_btns = InlineKeyboardMarkup(inline_keyboard=[
    [InlineR(text='💰 Изменить минимальный вывод', callback_data='change_min_cashout')],
    [InlineR(text='💸 Пополнить баланс бота', callback_data='topup_bot_balance')],
    [InlineR(text='💰 Баланс бота', callback_data='bot_balance')],
    [InlineR(text='🔐 Закрыть/открыть вывод', callback_data='prohibit_withdrawal')],
    [InlineR(text='🔙 Назад', callback_data='back_to_admin_panel')]
])


back_to_admin_panel_btn = InlineKeyboardMarkup(inline_keyboard=[
    [InlineR(text='🔙 Назад', callback_data='back_to_admin_panel')]])


async def to_pay_btn(pay_url):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineR(text='💳 Оплатить', url=pay_url))
    return keyboard.adjust(1).as_markup()


async def check_btn(check_url):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineR(text='💸 Получить', url=check_url))
    return keyboard.adjust(1).as_markup()


process_channel_data_cancel_btn = InlineKeyboardMarkup(inline_keyboard=[
    [InlineR(text='❌ Отменить', callback_data='process_channel_data_cancel')]])


cashout_btn = InlineKeyboardMarkup(inline_keyboard=[
    [InlineR(text='✨ Подать заявку на вывод', callback_data='cashout')]])


async def info_btn():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineR(text='🏆 Топ', callback_data='top'))
    keyboard.add(InlineR(text='🧑‍💻 Разработчик', callback_data='developer'))
    return keyboard.adjust(2).as_markup()


order_btn = InlineKeyboardMarkup(inline_keyboard=[
    [InlineR(text='🚚 Заказать', url='https://t.me/Brand0v')]])


async def acceptance_btn(withdrawal_request_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineR(text='✅ Одобрить', callback_data=f"approve:{withdrawal_request_id}"))
    keyboard.add(InlineR(text='❌ Отклонить', callback_data=f"reject:{withdrawal_request_id}"))
    return keyboard.adjust(2).as_markup()


approved_btn = InlineKeyboardMarkup(inline_keyboard=[
                [InlineR(text="✅ Одобрено", callback_data="approved")]])


rejected_btn = InlineKeyboardMarkup(inline_keyboard=[
                [InlineR(text="❌ Отклонено", callback_data="rejected")]])


async def show_referrals_btn(user_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineR(text='Рефералы', callback_data=f"show_referrals:{user_id}"))
    return keyboard.adjust(1).as_markup()


mailing_btn = InlineKeyboardMarkup(inline_keyboard=[
    [InlineR(text='✅ Отправить', callback_data='confirm_mailing'), 
     InlineR(text='❌ Отменить',callback_data='process_channel_data_cancel')]])


async def get_keyboard_show_referrals(referrer_id, page, total_pages):
    buttons = []

    if page > 1:
        buttons.append(InlineR(text=f"⬅️ {page - 1}", callback_data=f"show_referrals:{referrer_id}:{page - 1}"))

    if page < total_pages:
        buttons.append(InlineR(text=f"{page + 1} ➡️", callback_data=f"show_referrals:{referrer_id}:{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None


verification_btn = InlineKeyboardMarkup(inline_keyboard=[
    [InlineR(text='👉 Я не бот! 👈', callback_data='verification')]])
