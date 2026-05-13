import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime, timezone

# --- Config ---
TOKEN = os.environ.get("TOKEN")
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
    return cooldowns.get(str(user_id)) == get_today_utc()
 
def record_flip(user_id: int):
    cooldowns = load_cooldowns()
    cooldowns[str(user_id)] = get_today_utc()
    save_cooldowns(cooldowns)
 
# --- Coin flip buttons ---
class CoinFlipView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)  # Buttons expire after 30 seconds
 
    async def handle_flip(self, interaction: discord.Interaction, choice: str):
        if has_flipped_today(interaction.user.id):
            await interaction.response.send_message(
                "You've already flipped today. Try again tomorrow.", ephemeral=True
            )
            return
 
        record_flip(interaction.user.id)
        result = "Tails" if choice == "Heads" else "Heads"
 
        # Disable buttons after flip
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
 
        await interaction.followup.send(
            f"🪙 The coin lands on **{result}**.\n"
            f"You chose {choice}. So close! Better luck next time!"
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
bot = commands.Bot(command_prefix="!", intents=intents)
 
@bot.event
async def on_ready():
    await bot.tree.sync()
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
 
    view = CoinFlipView()
    await interaction.response.send_message("🪙 Choose your side:", view=view)
 
bot.run(TOKEN)

