import importlib
import re
from sys import argv
from typing import Optional

from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import Unauthorized, BadRequest, TimedOut, NetworkError, ChatMigrated, TelegramError
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from telegram.ext.dispatcher import run_async, DispatcherHandlerStop
from telegram.utils.helpers import escape_markdown

from lynda import dispatcher, updater, TOKEN, WEBHOOK, OWNER_ID, DONATION_LINK, CERT_PATH, PORT, URL, LOGGER, \
    ALLOW_EXCL, telethn

from lynda.modules import ALL_MODULES
from lynda.modules.helper_funcs.chat_status import is_user_admin
from lynda.modules.helper_funcs.misc import paginate_modules

PM_START_TEXT = """
Hi {}, my name is Sophia!
I am a Powerful Telegram Group Management bot with Some Anime Fun.
Add me to your group for spam free running.
================================
>> To see list of available commands hit /help.
>> For Updates Go [Here](t.me/ChiyoUpdates).
================================\n
"""

HELP_STRINGS = """
Hey there! My name is *Chiyo*.
Have a look at the following for an idea of some of the things I can help you with.\n
*Main* commands available:
◉ /start : start the bot
◉ /help : PM's you this message.
◉ /help <module name> : PM's you info about that module.
◉ /donate : information about how to donate!
◉ /settings : will redirect you to pm, with all that chat's settings.

{}
""".format(dispatcher.bot.first_name, "" if not ALLOW_EXCL else "\nAll commands can either be used with `/` or `!`.\n")

LYNDA_IMG = "https://telegra.ph/file/8af3961975d1cafd53839.jpg"

DONATE_STRING = """Heya, glad to hear you want to donate!
Lynda is hosted on one of Digital Ocean Servers. \
You can donate to the original writer of the Base code, Paul
There are two ways of supporting him; [PayPal](paypal.me/PaulSonOfLars), or [Monzo](monzo.me/paulnionvestergaardlarsen)."""

IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []

CHAT_SETTINGS = {}
USER_SETTINGS = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("lynda.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if imported_module.__mod_name__.lower() not in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception(
            "Can't have two modules with the same name! Please change one")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


# do not async
def send_help(chat_id, text, keyboard=None):
    """Send Help String in PM."""
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(chat_id=chat_id,
                                text=text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=keyboard,
                                disable_web_page_preview=True)


@run_async
def start(update: Update, context: CallbackContext):
    if update.effective_chat.type == "private":
        args = context.args
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, HELP_STRINGS)
            elif args[0].lower() == "markdownhelp":
                IMPORTED["extras"].markdown_help_sender(update)
            elif args[0].lower() == "nations":
                IMPORTED["nations"].send_nations(update)
            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))

                if is_user_admin(chat, update.effective_user.id):
                    send_settings(
                        match.group(1), update.effective_user.id, False)
                else:
                    send_settings(
                        match.group(1), update.effective_user.id, True)

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

        else:
            first_name = update.effective_user.first_name
            update.effective_message.reply_photo(LYNDA_IMG,
                PM_START_TEXT.format(escape_markdown(first_name), escape_markdown(bot.first_name), OWNER_ID),
                parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Add Chiyo To Your Group",
                                                                       url="t.me/{}?startgroup=true".format(bot.username))]]))
     else:
         update.effective_message.reply_text("Heya Am *Chiyo*!")


# for test purposes
def error_callback(_, __, error):
    """Callback error Handler"""
    try:
        raise error
    except Unauthorized:
        print(error)
        # remove update.message.chat_id from conversation list
    except BadRequest:
        print("BadRequest caught")
        print(error)

        # handle malformed requests - read more below!
    except TimedOut:
        print("no nono3")
        # handle slow connection problems
    except NetworkError:
        print("no nono4")
        # handle other connection problems
    except ChatMigrated as err:
        print(err)
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        print(error)
        # handle all other telegram related errors


@run_async
def help_button(update: Update, context: CallbackContext):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    try:
        if mod_match:
            module = mod_match.group(1)
            text = (
                "──「 Here is the help for *{}* 」──\n".format(
                    HELPABLE[module].__mod_name__
                )
                + HELPABLE[module].__help__
            )
            query.message.edit_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="Back", callback_data="help_back")]]
                ),
                disable_web_page_preview=True
            )

        elif back_match:
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help")),
                disable_web_page_preview=True
            )

        # ensure no spinny white circle
        context.bot.answer_callback_query(query.id)
        # query.message.delete()

    except BadRequest:
        pass



@run_async
def get_help(update: Update, context: CallbackContext):
    """Sends Help String"""
    message = update.effective_message
    chat = update.effective_chat  # type: Optional[Chat]
    args = context.args

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:

        message.reply_text("Contact me in PM to get the list of possible commands.",
                        reply_markup=InlineKeyboardMarkup(
                            [[InlineKeyboardButton(text="Help",
                                                    url="t.me/{}?start=help".format(
                                                        context.bot.username))]]))
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = "Here is the available help for the *{}* module:\n".format(
            HELPABLE[module].__mod_name__) + HELPABLE[module].__help__
        send_help(chat.id, text, InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Back", callback_data="help_back")]]))

    else:
        send_help(chat.id, HELP_STRINGS)


def send_settings(chat_id, user_id, user=False):
    """Sends Settings String"""
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join("*{}*:\n{}".format(mod.__mod_name__,
                                                    mod.__user_settings__(user_id)) for mod in USER_SETTINGS.values())
            dispatcher.bot.send_message(
                user_id,
                "These are your current settings:" +
                "\n\n" +
                settings,
                parse_mode=ParseMode.MARKDOWN)

        else:
            dispatcher.bot.send_message(
                user_id,
                "Seems like there aren't any user specific settings available :'(",
                parse_mode=ParseMode.MARKDOWN)

    else:
        if CHAT_SETTINGS:
            chat_name = dispatcher.bot.getChat(chat_id).title
            dispatcher.bot.send_message(
                user_id,
                text="Which module would you like to check {}'s settings for?".format(chat_name),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        0,
                        CHAT_SETTINGS,
                        "stngs",
                        chat=chat_id)))
        else:
            dispatcher.bot.send_message(
                user_id,
                "Seems like there aren't any chat settings available :'(\nSend this "
                "in a group chat you're admin in to find its current settings!",
                parse_mode=ParseMode.MARKDOWN)


@run_async
def settings_button(update: Update, context: CallbackContext):
    """Button for settings"""
    query = update.callback_query
    user = update.effective_user
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = context.bot.get_chat(chat_id)
            text = "*{}* has the following settings for the *{}* module:\n\n".format(
                escape_markdown(
                    chat.title),
                CHAT_SETTINGS[module].__mod_name__) + CHAT_SETTINGS[module].__chat_settings__(
                chat_id,
                user.id)
            query.message.reply_text(text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="stngs_back({})".format(chat_id))]]))

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = context.bot.get_chat(chat_id)
            query.message.reply_text(
                "Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(
                    chat.title), reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id)))

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = context.bot.get_chat(chat_id)
            query.message.reply_text(
                "Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(
                    chat.title), reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        next_page + 1, CHAT_SETTINGS, "stngs", chat=chat_id)))

        elif back_match:
            chat_id = back_match.group(1)
            chat = context.bot.get_chat(chat_id)
            query.message.reply_text(
                text="Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(
                    escape_markdown(
                        chat.title)), parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        0, CHAT_SETTINGS, "stngs", chat=chat_id)))

        # ensure no spinny white circle
        context.bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if (
            excp.message != "Message is not modified"
            and excp.message != "Query_id_invalid"
            and excp.message != "Message can't be deleted"
        ):
            LOGGER.exception(
                "Exception in settings buttons. %s", str(
                    query.data))


@run_async
def get_settings(update: Update, context: CallbackContext):
    """Getting Settings String"""
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User
