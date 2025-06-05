# BankingBot

A Telegram bot that simulates a banking system, allowing users to manage their virtual balance through deposits and withdrawals using various payment methods.

## Features

- 💰 Check balance
- 💵 Deposit money
- 💸 Withdraw money
- 💳 Multiple payment methods support:
  - Bank Transfer
  - PayPal
  - Cryptocurrency (BTC, ETH, USDT)

## Prerequisites

Before running the bot, make sure you have:

1. Python 3.7 or higher installed
2. MongoDB installed and running locally
3. A Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather))

## Installation

1. Clone the repository:
```bash
git clone https://github.com/KainanAugusto/BankingBot.git
cd BankingBot
```

2. Install the required dependencies:
```bash
pip install python-telegram-bot pymongo
```

3. Configure the bot:
   - Open `main.py`
   - Replace `'THAT_IS_A_SECRET'` with your actual Telegram Bot Token

## Running the Bot

1. Make sure MongoDB is running on your system
2. Run the bot:
```bash
python main.py
```

## How It Works

### User Flow

1. Start the bot with `/start` command
2. Choose an operation:
   - Check Balance
   - Deposit
   - Withdraw

### Payment Methods

The bot supports multiple payment methods that users can add:

1. **Bank Transfer**
   - Requires bank name
   
2. **PayPal**
   - Requires PayPal email address
   
3. **Cryptocurrency**
   - Supports BTC, ETH, and USDT
   - Requires wallet address

### Transaction Process

1. **Deposit**
   - Enter amount
   - Select or add payment method
   - Confirm transaction
   - Balance updates automatically

2. **Withdrawal**
   - Enter amount
   - Select payment method
   - Confirm transaction
   - Balance updates if sufficient funds

### Data Storage

- All user data is stored in MongoDB
- Each user document contains:
  - Chat ID
  - Balance
  - Payment methods
  - Last transaction details

## Security Features

- Balance verification before withdrawals
- Input validation for amounts
- Secure storage of payment methods

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License
