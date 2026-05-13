import discord
import random
from datetime import datetime, timezone
from discord import app_commands
from discord.ext import commands
import json
import os
from discord.ext import commands
from discord.ext import tasks

# --- Config ---
TOKEN = os.environ.get("TOKEN")
QUARANTINE_CHANNEL_ID = 1501626333652979843  # Replace with your #quarantine channel ID
QUARANTINE_ROLE_NAME = "quarantine"         # Must match your role name exactly (case-insensitive)

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
    return cooldowns.get(str(user_id)) == get_today_utc()

def record_flip(user_id: int):
    cooldowns = load_cooldowns()
    cooldowns[str(user_id)] = get_today_utc()
    save_cooldowns(cooldowns)

def has_quarantine_role(member: discord.Member) -> bool:
    return any(r.name.lower() == QUARANTINE_ROLE_NAME.lower() for r in member.roles)

# --- Coin flip buttons ---
class CoinFlipView(discord.ui.View):
    def __init__(self, rigged: bool):
        super().__init__(timeout=30)
        self.rigged = rigged

    async def handle_flip(self, interaction: discord.Interaction, choice: str):
        if has_flipped_today(interaction.user.id):
            await interaction.response.send_message(
                "You've already flipped today. Try again tomorrow.", ephemeral=True
            )
            return

        record_flip(interaction.user.id)

        if self.rigged:
            # Always the opposite
            result = "Tails" if choice == "Heads" else "Heads"
        else:
            # Fair 50/50
            result = random.choice(["Heads", "Tails"])

        # Disable buttons after flip
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        if result.lower() == choice.lower():
            await interaction.followup.send(
                f"🪙 The coin lands on **{result}**.\nYou chose {choice}. You win!"
            )
        else:
            await interaction.followup.send(
                f"🪙 The coin lands on **{result}**.\nYou chose {choice}. So close! Better luck next time!"
            )

    @discord.ui.button(label="Heads", style=discord.ButtonStyle.primary, emoji="🪙")
    async def heads(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_flip(interaction, "Heads")

    @discord.ui.button(label="Tails", style=discord.ButtonStyle.secondary, emoji="🪙")
    async def tails(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_flip(interaction, "Tails")

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

# --- Bot setup ---
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Weekly reminder ---
@tasks.loop(hours=168)  # 168 hours = 1 week
async def weekly_reminder():
    channel = bot.get_channel(QUARANTINE_CHANNEL_ID)
    if channel:
        await channel.send(
            "👋 Reminder — you can try your luck with /coinflip once a day. "
            "Who knows, today might finally be your day."
        )

@bot.event
async def on_ready():
    await bot.tree.sync()
    weekly_reminder.start()
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="coinflip", description="Flip a coin — maybe today's your lucky day.")
async def coinflip(interaction: discord.Interaction):
    if interaction.channel_id != QUARANTINE_CHANNEL_ID:
        await interaction.response.send_message(
            "This command can only be used in quarantine.", ephemeral=True
        )
        return

    if has_flipped_today(interaction.user.id):
        await interaction.response.send_message(
            "You've already flipped today. Try again tomorrow.", ephemeral=True
        )
        return

    rigged = has_quarantine_role(interaction.user)
    view = CoinFlipView(rigged=rigged)
    await interaction.response.send_message("🪙 Choose your side:", view=view)

bot.run(TOKEN)


