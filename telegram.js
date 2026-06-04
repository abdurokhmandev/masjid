const TelegramBot = require('node-telegram-bot-api');

// Replace with your own bot token and admin chat ID
const BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN';
const ADMIN_CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID';

const bot = new TelegramBot(BOT_TOKEN, { polling: true });

function notifyAdmin(message) {
  if (BOT_TOKEN && ADMIN_CHAT_ID) {
    bot.sendMessage(ADMIN_CHAT_ID, message).catch(err => console.error('Telegram send error:', err));
  } else {
    console.warn('Telegram bot token or admin chat ID not set.');
  }
}

module.exports = { notifyAdmin, bot };
