import discord
import os
import json
import psutil # Untuk cek ram/cpu di /status
from discord.ext import commands
from discord import app_commands

# ================= KONFIGURASI =================
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1469740150522380299
VIP_FILE = "vips.json"

# ID SESUAI REQUEST KAMU
ADMIN_ROLE_ID = 1471265207945924619  # Role Management
OWNER_ID = 1465731110162927707       # ID Owner

# ================= DATABASE VIP =================
def load_vips():
    if not os.path.exists(VIP_FILE):
        with open(VIP_FILE, "w") as f: json.dump([], f)
    try:
        with open(VIP_FILE, "r") as f: return json.load(f)
    except: return []

def save_vips(vips):
    with open(VIP_FILE, "w") as f: json.dump(vips, f)

# ================= BOT SETUP =================
class TatangBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True # HARUS AKTIF UNTUK TAG USER
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = TatangBot()

# ================= SLASH COMMANDS (VIP) =================

@bot.tree.command(name="addvip", description="Berikan akses VIP Scanner ke user")
@app_commands.describe(member="Pilih user yang ingin dijadikan VIP")
async def addvip(interaction: discord.Interaction, member: discord.Member):
    # Cek Role Management (Berdasarkan ID yang kamu kasih)
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if role not in interaction.user.roles:
        return await interaction.response.send_message(
            f"❌ Anda tidak memiliki izin **Management**!", 
            ephemeral=True
        )

    vips = load_vips()
    if member.id not in vips:
        vips.append(member.id)
        save_vips(vips)
        
        # Tampilan Sukses Rapi
        embed = discord.Embed(
            title="✨ VIP ACCESS GRANTED",
            description=f"Selamat {member.mention}, status VIP kamu telah **Aktif**! ✅",
            color=0x2ecc71
        )
        embed.set_image(url="https://share.cdn.viber.com/client/cgi-bin/get_sticker.cgi?f=7944111&s=400&u=0")
        embed.set_footer(text=f"Diaktifkan oleh {interaction.user.display_name}")
        
        await interaction.response.send_message(content=member.mention, embed=embed)
    else:
        await interaction.response.send_message(f"ℹ️ {member.mention} sudah menjadi VIP.", ephemeral=True)

# ================= NEW COMMANDS (/menu, /status, /help) =================

@bot.tree.command(name="menu", description="Lihat semua daftar perintah bot")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 MAIN MENU - TATANG BOT", color=0x3498db)
    embed.add_field(name="🛡️ Security", value="`/addvip` - Beri akses VIP\n`/removevip` - Hapus akses VIP", inline=False)
    embed.add_field(name="📋 Information", value="`/status` - Cek mesin bot\n`/help` - Bantuan penggunaan", inline=False)
    embed.add_field(name="🎭 Roleplay", value="`/panelcs` - Form Character Story", inline=False)
    embed.set_image(url="https://share.cdn.viber.com/client/cgi-bin/get_sticker.cgi?f=7944111&s=400&u=0")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="status", description="Cek performa mesin bot")
async def status(interaction: discord.Interaction):
    ram = psutil.virtual_memory().percent
    cpu = psutil.cpu_percent()
    embed = discord.Embed(title="⚙️ SYSTEM STATUS", color=0x9b59b6)
    embed.add_field(name="🤖 Bot Status", value="🟢 Online & Active", inline=True)
    embed.add_field(name="🧠 RAM Usage", value=f"`{ram}%`", inline=True)
    embed.add_field(name="⚡ CPU Usage", value=f"`{cpu}%`", inline=True)
    embed.set_footer(text="Running on Cloud High Speed")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Panduan cara pakai bot")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="❓ BUTUH BANTUAN?", color=0xf1c40f)
    embed.description = (
        "**Scanner Anti-Stealer:**\n"
        "1. Pastikan kamu sudah menjadi **VIP**.\n"
        f"2. Upload file `.lua` atau `.zip` di <#{CHANNEL_ID}>.\n\n"
        "**Character Story:**\n"
        "Gunakan `/panelcs` lalu ikuti petunjuk di layar.\n\n"
        f"🚨 **Kendala?** Hubungi Owner: <@{OWNER_ID}>"
    )
    await interaction.response.send_message(embed=embed)

# ================= ON MESSAGE (SCANNER LOGIC) =================

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != CHANNEL_ID: return

    if message.attachments:
        vips = load_vips()
        if message.author.id not in vips:
            embed = discord.Embed(
                title="🔒 PREMIUM ACCESS LOCKED",
                description=(
                    f"Halo {message.author.mention}, fitur scanner ini khusus **VIP**.\n\n"
                    f"Silakan hubungi **Owner** (<@{OWNER_ID}>) untuk mendaftar! ✨"
                ),
                color=0xffd700
            )
            embed.set_image(url="https://share.cdn.viber.com/client/cgi-bin/get_sticker.cgi?f=7944111&s=400&u=0")
            return await message.reply(embed=embed)

        # Lanjut logika scanner kamu di sini...
        pass

bot.run(TOKEN)
