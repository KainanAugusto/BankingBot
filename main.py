from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from pymongo import MongoClient
from datetime import datetime

client = MongoClient('mongodb://localhost:27017/')
db = client.banking_bot
users = db.users

API_TOKEN: Final = 'THAT_IS_A_SECRET'


def get_or_create_user(chat_id):
    user = users.find_one({"chat_id": chat_id})
    if user is None:
        users.insert_one({
            "chat_id": chat_id,
            "balance": 0,
            "last_transaction": None,
            "methods": []
        })
        user = users.find_one({"chat_id": chat_id})
    return user


async def initiate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 Check Balance", callback_data='check_balance')],
        [InlineKeyboardButton("💵 Deposit", callback_data='deposit')],
        [InlineKeyboardButton("💸 Withdraw", callback_data='withdraw')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('👋 Hello! What do you want to do?', reply_markup=reply_markup)


async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_or_create_user(query.message.chat.id)
    balance = user['balance']
    last_transaction = user['last_transaction']

    if last_transaction:
        last_time = last_transaction['time']
        last_amount = last_transaction['amount']
        last_type = last_transaction['type']
        message = f"💵 Your balance is: ${balance:.2f}.\n📝 Last {last_type}: ${last_amount:.2f} at {last_time}."
    else:
        message = f"💵 Your balance is: ${balance:.2f}. No transactions yet."

    keyboard = [[InlineKeyboardButton("🔄 New Transaction", callback_data='start_transaction')]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("💵 You are about to deposit. Please type the amount:")
    context.user_data['operation'] = 'deposit'


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("💸 How much do you want to withdraw? Type a number.")
    context.user_data['operation'] = 'withdraw'


async def handle_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_method_details', False):
        await save_method(update, context)
        return

    user = get_or_create_user(update.message.chat.id)
    operation = context.user_data.get('operation')

    try:
        amount = int(update.message.text)
        if amount <= 0:
            await update.message.reply_text("⚠️ Enter a valid number greater than 0.")
            return

        if operation == 'withdraw':
            if amount > user['balance']:
                keyboard = [
                    [InlineKeyboardButton("🔄 Try Again", callback_data='withdraw')],
                    [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"⚠️ Insufficient funds. Your balance is ${user['balance']:.2f}.",
                    reply_markup=reply_markup
                )
                return

        context.user_data['amount'] = amount
        await ask_for_method(update, context)

    except ValueError:
        await update.message.reply_text("⚠️ Enter a valid number.")


async def ask_for_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.message.chat.id)
    methods = user.get('methods', [])

    buttons = []
    if methods:
        for i, method in enumerate(methods):
            buttons.append([InlineKeyboardButton(method['description'], callback_data=f'method_{i}')])

    buttons.append([InlineKeyboardButton("➕ Add New Method", callback_data='add_method')])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel')])

    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("💳 Select a method for your transaction:", reply_markup=reply_markup)


async def add_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    buttons = [
        [InlineKeyboardButton("🏦 Bank Transfer", callback_data='new_bank_transfer')],
        [InlineKeyboardButton("💸 PayPal", callback_data='new_paypal')],
        [InlineKeyboardButton("₿ Crypto", callback_data='new_crypto')],
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text("Select the method type:", reply_markup=reply_markup)


async def new_bank_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['method_type'] = 'bank_transfer'
    await query.edit_message_text("Please type the name of your bank.")
    context.user_data['awaiting_method_details'] = True


async def new_paypal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['method_type'] = 'paypal'
    await query.edit_message_text("Please enter your PayPal email address.")
    context.user_data['awaiting_method_details'] = True


async def new_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    buttons = [
        [InlineKeyboardButton("BTC", callback_data='crypto_btc')],
        [InlineKeyboardButton("ETH", callback_data='crypto_eth')],
        [InlineKeyboardButton("USDT", callback_data='crypto_usdt')]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text("Choose the cryptocurrency:", reply_markup=reply_markup)


async def crypto_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['crypto_type'] = query.data.split('_')[1]
    context.user_data['method_type'] = 'crypto'
    await query.edit_message_text(f"Please enter your {context.user_data['crypto_type']} address.")
    context.user_data['awaiting_method_details'] = True


async def save_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.message.chat.id)
    method_type = context.user_data.get('method_type')
    if method_type is None:
        await update.message.reply_text("⚠️ No payment method selected. Please start again.")
        return

    if method_type == 'bank_transfer':
        method_description = f"Bank Transfer: {update.message.text}"
    elif method_type == 'paypal':
        method_description = f"PayPal: {update.message.text}"
    elif method_type == 'crypto':
        method_description = f"{context.user_data['crypto_type'].upper()}: {update.message.text}"

    users.update_one({"chat_id": update.message.chat.id}, {
        "$push": {
            "methods": {
                "type": method_type,
                "description": method_description
            }
        }
    })

    context.user_data.pop('method_type', None)
    context.user_data.pop('crypto_type', None)
    context.user_data['awaiting_method_details'] = False

    await update.message.reply_text(f"✅ Method '{method_description}' added.")
    await ask_for_method(update, context)


async def select_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_or_create_user(query.message.chat.id)

    method_index = int(query.data.split('_')[1])
    selected_method = user['methods'][method_index]

    context.user_data['selected_method'] = selected_method

    amount = context.user_data['amount']
    method_description = selected_method['description']
    operation = context.user_data['operation']

    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f'confirm_{operation}')],
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"💵 Confirm {operation} of ${amount:.2f} using {method_description}?",
        reply_markup=reply_markup
    )


async def confirm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_or_create_user(query.message.chat.id)
    amount = context.user_data['amount']

    new_balance = user['balance'] + amount
    users.update_one({"chat_id": query.message.chat.id}, {
        "$set": {
            "balance": new_balance,
            "last_transaction": {
                "type": "deposit",
                "amount": amount,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    })

    keyboard = [[InlineKeyboardButton("🔄 New Transaction", callback_data='start_transaction')]]
    await query.edit_message_text(
        f"✅ Deposit of ${amount:.2f} confirmed. New balance: ${new_balance:.2f}.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def confirm_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_or_create_user(query.message.chat.id)
    amount = context.user_data['amount']

    if amount > user['balance']:
        keyboard = [
            [InlineKeyboardButton("🔄 Try Again", callback_data='withdraw')],
            [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"⚠️ Insufficient funds. Your balance is ${user['balance']:.2f}.",
            reply_markup=reply_markup
        )
        return

    new_balance = user['balance'] - amount
    users.update_one({"chat_id": query.message.chat.id}, {
        "$set": {
            "balance": new_balance,
            "last_transaction": {
                "type": "withdrawal",
                "amount": amount,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    })

    new_text = f"✅ Withdrawal of ${amount:.2f} confirmed. New balance: ${new_balance:.2f}."
    keyboard = [[InlineKeyboardButton("🔄 New Transaction", callback_data='start_transaction')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(new_text, reply_markup=reply_markup)


async def start_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("💰 Check Balance", callback_data='check_balance')],
        [InlineKeyboardButton("💵 Deposit", callback_data='deposit')],
        [InlineKeyboardButton("💸 Withdraw", callback_data='withdraw')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('🔄 What would you like to do next?', reply_markup=reply_markup)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("❌ Operation cancelled.")


async def log_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')


if __name__ == '__main__':
    app = Application.builder().token(API_TOKEN).build()

    app.add_handler(CommandHandler('start', initiate_command))
    app.add_handler(CallbackQueryHandler(check_balance, pattern='check_balance'))
    app.add_handler(CallbackQueryHandler(deposit, pattern='deposit'))
    app.add_handler(CallbackQueryHandler(withdraw, pattern='withdraw'))
    app.add_handler(CallbackQueryHandler(confirm_deposit, pattern='confirm_deposit'))
    app.add_handler(CallbackQueryHandler(confirm_withdraw, pattern='confirm_withdraw'))
    app.add_handler(CallbackQueryHandler(cancel, pattern='cancel'))
    app.add_handler(CallbackQueryHandler(start_transaction, pattern='start_transaction'))
    app.add_handler(CallbackQueryHandler(add_method, pattern='add_method'))
    app.add_handler(CallbackQueryHandler(new_bank_transfer, pattern='new_bank_transfer'))
    app.add_handler(CallbackQueryHandler(new_paypal, pattern='new_paypal'))
    app.add_handler(CallbackQueryHandler(new_crypto, pattern='new_crypto'))
    app.add_handler(CallbackQueryHandler(crypto_address, pattern='crypto_'))
    app.add_handler(CallbackQueryHandler(select_method, pattern=r'method_\d+'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transaction))
    app.add_error_handler(log_error)

    print('Starting polling...')
    app.run_polling(poll_interval=2)
