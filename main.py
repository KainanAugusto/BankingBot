from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from pymongo import MongoClient
from datetime import datetime

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client.banking_bot
users = db.users

API_TOKEN: Final = 'ASK_ME_IF_YOU_NEED'
# Retrieve or create user
def get_or_create_user(chat_id):
    user = users.find_one({"chat_id": chat_id})
    if user is None:
        users.insert_one({
            "chat_id": chat_id,
            "balance": 0,
            "last_transaction": None
        })
        user = users.find_one({"chat_id": chat_id})
    return user

# Start command
async def initiate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 Check Balance", callback_data='check_balance')],
        [InlineKeyboardButton("💵 Deposit", callback_data='deposit')],
        [InlineKeyboardButton("💸 Withdraw", callback_data='withdraw')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('👋 Hello! What do you want to do?', reply_markup=reply_markup)

# Check balance
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

    keyboard = [
        [InlineKeyboardButton("🔄 New Transaction", callback_data='start_transaction')]
    ]

    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

# Handle deposit
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("💵 How much do you want to deposit? Type a number.")
    context.user_data['operation'] = 'deposit'

# Handle withdraw
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("💸 How much do you want to withdraw? Type a number.")
    context.user_data['operation'] = 'withdraw'

# Handle transactions
async def handle_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.message.chat.id)
    operation = context.user_data.get('operation')

    try:
        amount = int(update.message.text)
        if amount <= 0:
            await update.message.reply_text("⚠️ Enter a valid number greater than 0.")
            return

        if operation == 'deposit':
            context.user_data['amount'] = amount
            keyboard = [
                [InlineKeyboardButton("✅ Confirm", callback_data='confirm_deposit')],
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ]
            await update.message.reply_text(f"💵 Confirm deposit of ${amount:.2f}?", reply_markup=InlineKeyboardMarkup(keyboard))

        elif operation == 'withdraw':
            if amount > user['balance']:
                balance = user['balance']
                keyboard = [
                    [InlineKeyboardButton("🔄 New Transaction", callback_data='start_transaction')]
                ]
                await update.message.reply_text(f"⚠️ You cannot withdraw more than your balance! \n💵 Your current balance is: ${balance:.2f}.", reply_markup=InlineKeyboardMarkup(keyboard))
                return

            context.user_data['amount'] = amount
            keyboard = [
                [InlineKeyboardButton("✅ Confirm", callback_data='confirm_withdraw')],
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ]
            await update.message.reply_text(f"💸 Confirm withdrawal of ${amount:.2f}?", reply_markup=InlineKeyboardMarkup(keyboard))

    except ValueError:
        await update.message.reply_text("⚠️ Enter a valid number.")

# Confirm deposit
async def confirm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_or_create_user(query.message.chat.id)
    amount = context.user_data['amount']

    # Update balance
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

    keyboard = [
        [InlineKeyboardButton("🔄 New Transaction", callback_data='start_transaction')]
    ]

    await query.edit_message_text(f"✅ Deposit of ${amount:.2f} confirmed. New balance: ${new_balance:.2f}.", reply_markup=InlineKeyboardMarkup(keyboard))

# Confirm withdrawal
async def confirm_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_or_create_user(query.message.chat.id)
    amount = context.user_data['amount']

    # Update balance
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

    keyboard = [
        [InlineKeyboardButton("🔄 New Transaction", callback_data='start_transaction')]
    ]

    await query.edit_message_text(f"✅ Withdrawal of ${amount:.2f} confirmed. New balance: ${new_balance:.2f}.", reply_markup=InlineKeyboardMarkup(keyboard))

# Start new transaction
async def start_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    keyboard = [
        [InlineKeyboardButton("💰 Check Balance", callback_data='check_balance')],
        [InlineKeyboardButton("💵 Deposit", callback_data='deposit')],
        [InlineKeyboardButton("💸 Withdraw", callback_data='withdraw')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text('🔄 What would you like to do next?', reply_markup=reply_markup)

# Cancel operation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("❌ Operation cancelled.")

# Log errors
async def log_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

# Start the bot
if __name__ == '__main__':
    app = Application.builder().token(API_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler('start', initiate_command))

    # Callback query handlers
    app.add_handler(CallbackQueryHandler(check_balance, pattern='check_balance'))
    app.add_handler(CallbackQueryHandler(deposit, pattern='deposit'))
    app.add_handler(CallbackQueryHandler(withdraw, pattern='withdraw'))
    app.add_handler(CallbackQueryHandler(confirm_deposit, pattern='confirm_deposit'))
    app.add_handler(CallbackQueryHandler(confirm_withdraw, pattern='confirm_withdraw'))
    app.add_handler(CallbackQueryHandler(cancel, pattern='cancel'))
    app.add_handler(CallbackQueryHandler(start_transaction, pattern='start_transaction'))

    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transaction))

    # Error handler
    app.add_error_handler(log_error)

    print('Starting polling...')
    app.run_polling(poll_interval=2)
