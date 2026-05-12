import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime, timezone

# --- Config ---
TOKEN = "YOUR_BOT_TOKEN_HERE"
QUARANTINE_CHANNEL_ID = 1501626333652979843  # Replace with your #quarantine channel ID

COOLDOWNS_FILE = "cooldowns.json"

# --- Cooldown helpers ---
def load_cooldowns():
    if os.path.exists(COOLDOWNS_FILE):
        with open(COOLDOWNS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cooldowns(data):
    with open(COOLDOWNS_FILE, "w") as f:
        json.dump(data, f)

def get_today_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def has_flipped_today(user_id: int) -> bool:
    cooldowns = load_cooldowns()
    uid = str(user_id)
    return cooldowns.get(uid) == get_today_utc()

def record_flip(user_id: int):
    cooldowns = load_cooldowns()
    cooldowns[str(user_id)] = get_today_utc()
    save_cooldowns(cooldowns)

# --- Bot setup ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="coinflip", description="Flip a coin — maybe today's your lucky day.")
@app_commands.describe(choice="heads or tails")
async def coinflip(interaction: discord.Interaction, choice: str):
    # Only works in the quarantine channel
    if interaction.channel_id != QUARANTINE_CHANNEL_ID:
        await interaction.response.send_message(
            "This command can only be used in quarantine.", ephemeral=True
        )
        return

    choice = choice.lower().strip()
    if choice not in ["heads", "tails"]:
        await interaction.response.send_message(
            "Please choose **heads** or **tails**.", ephemeral=True
        )
        return

    if has_flipped_today(interaction.user.id):
        await interaction.response.send_message(
            "You've already flipped today. Try again tomorrow.", ephemeral=True
        )
        return

    # Record the attempt (rigged — always the opposite)
    record_flip(interaction.user.id)
    result = "tails" if choice == "heads" else "heads"

    await interaction.response.send_message(
        f"🪙 The coin lands on **{result}**.\n"
        f"You chose {choice}. So close! Better luck next time!"
    )

bot.run(TOKEN)
