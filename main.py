import discord
import os
import json
import psutil
from discord.ext import commands
from discord import app_commands

# ================= KONFIGURASI =================
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1469740150522380299
VIP_FILE = "vips.json"

# ID YANG KAMU BERIKAN
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
        intents.members = True # HARUS NYALA DI PORTAL DEV
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = TatangBot()

# ================= COMMANDS =================

@bot.tree.command(name="addvip", description="Memberikan status VIP kepada user")
async def addvip(interaction: discord.Interaction, member: discord.Member):
    # Cek Role Management
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if role not in interaction.user.roles:
        return await interaction.response.send_message("❌ **Akses Ditolak!** Izin Management diperlukan.", ephemeral=True)

    vips = load_vips()
    if member.id not in vips:
        vips.append(member.id)
        save_vips(vips)
        
        embed = discord.Embed(
            title="✨ VIP ACCESS GRANTED",
            description=f"Selamat {member.mention}, status VIP kamu telah **Aktif**! ✅",
            color=0x2ecc71
        )
        embed.set_image(url="https://share.cdn.viber.com/client/cgi-bin/get_sticker.cgi?f=7944111&s=400&u=0")
        embed.set_footer(text=f"Authorized by {interaction.user.name}")
        await interaction.response.send_message(content=f"🔔 {member.mention}", embed=embed)
    else:
        await interaction.response.send_message(f"ℹ️ {member.mention} sudah menjadi VIP.", ephemeral=True)

@bot.tree.command(name="removevip", description="Mencabut status VIP dari user")
async def removevip(interaction: discord.Interaction, member: discord.Member):
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if role not in interaction.user.roles:
        return await interaction.response.send_message("❌ **Akses Ditolak!**", ephemeral=True)

    vips = load_vips()
    if member.id in vips:
        vips.remove(member.id)
        save_vips(vips)
        await interaction.response.send_message(f"🗑️ Status VIP {member.mention} berhasil **Dihapus**.")
    else:
        await interaction.response.send_message(f"❓ {member.mention} bukan user VIP.", ephemeral=True)

@bot.tree.command(name="listvip", description="Melihat daftar semua user VIP")
async def listvip(interaction: discord.Interaction):
    # Cek Role Management (Opsional: Hapus blok if ini jika ingin semua orang bisa lihat)
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if role not in interaction.user.roles:
         return await interaction.response.send_message("❌ Hanya Management yang boleh melihat data VIP.", ephemeral=True)

    vips = load_vips()
    if not vips:
        return await interaction.response.send_message("📂 **Database Kosong:** Belum ada user VIP.", ephemeral=True)

    # Membuat daftar nama dengan format rapi
    vip_list_text = ""
    for index, user_id in enumerate(vips, 1):
        vip_list_text += f"**{index}.** <@{user_id}> (`{user_id}`)\n"

    embed = discord.Embed(title="👑 DAFTAR USER VIP", color=0xffd700)
    embed.add_field(name=f"Total Member: {len(vips)}", value=vip_list_text, inline=False)
    embed.set_footer(text="Database Tatang Bot • Updated Realtime")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="menu", description="Menu utama bot")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 TATANG BOT MENU", color=0x3498db)
    embed.add_field(name="👑 Management", value="`/addvip` • `/removevip`\n`/listvip` • Cek Data VIP", inline=True)
    embed.add_field(name="⚙️ System", value="`/status` • `/help`", inline=True)
    embed.set_image(url="https://share.cdn.viber.com/client/cgi-bin/get_sticker.cgi?f=7944111&s=400&u=0")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="status", description="Cek status server bot")
async def status(interaction: discord.Interaction):
    ram = psutil.virtual_memory().percent
    embed = discord.Embed(title="⚙️ SYSTEM STATUS", color=0x9b59b6)
    embed.add_field(name="Status", value="🟢 Online", inline=True)
    embed.add_field(name="RAM", value=f"`{ram}%`", inline=True)
    embed.add_field(name="Ping", value=f"`{round(bot.latency * 1000)}ms`", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Bantuan penggunaan")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="❓ PANDUAN PENGGUNAAN", color=0xf1c40f)
    embed.description = (
        "**Fitur Scanner VIP:**\n"
        "1. Pastikan kamu memiliki role **VIP**.\n"
        f"2. Kirim file script di channel <#{CHANNEL_ID}>.\n"
        "3. Bot akan menganalisa keamanan file secara otomatis.\n\n"
        f"📩 **Hubungi Owner:** <@{OWNER_ID}>"
    )
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)
