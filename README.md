# MEXC AI Scalper Telegram Bot

Files:
- bot.py — telegram bot entrypoint (ApplicationBuilder, async)
- suggest.py — market scan & AI-style analysis
- config.py — optional token fallback
- requirements.txt — libs

Deployment (Render)
1. Create repo with these files
2. In Render, create Web Service -> connect repo
3. Set environment variable TELEGRAM_BOT_TOKEN with your bot token
4. Start command (Render): `python bot.py`
5. Deploy (manual) — service will start and poll Telegram

Notes:
- This bot suggests trade ideas only (not executing orders).
- Thoroughly test suggestions on a demo account before trading live.
