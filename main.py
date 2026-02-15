import discord
import os
import json
import psutil
import zipfile
import py7zr
import re
import io
import math
from discord.ext import commands
from discord import app_commands

# ================= KONFIGURASI ID =================
TOKEN = os.getenv("TOKEN")
SCAN_CHANNEL_ID = 1469740150522380299      
REQ_VIP_CHANNEL_ID = 1472535677634740398   
ADMIN_ROLE_ID = 1471265207945924619        
VIP_FILE = "vips.json"

# ================= UTILITY FUNCTIONS =================
def load_vips():
    if not os.path.exists(VIP_FILE):
        with open(VIP_FILE, "w") as f: json.dump([], f)
    try:
        with open(VIP_FILE, "r") as f: return json.load(f)
    except: return []

def save_vips(vips):
    with open(VIP_FILE, "w") as f: json.dump(vips, f)

def format_size(size_bytes):
    if size_bytes == 0: return "0B"
    size_name = ("B", "KB", "MB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# ================= SCANNER ENGINE =================
def analyze_content(content):
    pola_terdeteksi = []
    found_links = []
    dw_regex = r"https://discord\.com/api/webhooks/\d+/\S+"
    tg_regex = r"https://api\.telegram\.org/bot\d+:\S+"
    dw_links = re.findall(dw_regex, content)
    tg_links = re.findall(tg_regex, content)
    if dw_links: found_links.extend(dw_links)
    if tg_links: found_links.extend(tg_links)
    danger_map = {
        "os.execute": "System Command Execution",
        "io.popen": "Remote Process Open",
        "loadstring": "Hidden Executable Code",
        "sampGetPlayerNickname": "Data Grabber (Nickname)",
        "sampGetCurrentServerAddress": "IP Logger (Server IP)",
        "LuaObfuscator.com": "Highly Obfuscated Code",
        "exec": "Dynamic Command Execution"
    }
    for key, label in danger_map.items():
        if key in content: pola_terdeteksi.append(f"• {label}")
    return pola_terdeteksi, found_links

# ================= BOT SETUP =================
class TatangBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = TatangBot()

# ================= SEMUA FITUR SLASH COMMANDS =================

@bot.tree.command(name="menu", description="Dashboard Lengkap")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(title="✨ TATANG BOT | DASHBOARD", color=0x3498db)
    embed.add_field(name="👑 **ADMIN**", value="`/addvip`, `/removevip`, `/listvip`", inline=False)
    embed.add_field(name="⚙️ **SYSTEM**", value="`/status`, `/help`, `/ping`", inline=False)
    embed.set_image(url="https://share.cdn.viber.com/client/cgi-bin/get_sticker.cgi?f=7944111&s=400&u=0")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="addvip", description="Tambah Member VIP")
async def addvip(interaction: discord.Interaction, member: discord.Member):
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if role not in interaction.user.roles:
        return await interaction.response.send_message("❌ No Permission!", ephemeral=True)
    vips = load_vips()
    if member.id not in vips:
        vips.append(member.id)
        save_vips(vips)
        await interaction.response.send_message(f"✅ {member.mention} added to VIP.")
    else: await interaction.response.send_message("Already VIP.", ephemeral=True)

@bot.tree.command(name="removevip", description="Hapus Member VIP")
async def removevip(interaction: discord.Interaction, member: discord.Member):
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if role not in interaction.user.roles:
        return await interaction.response.send_message("❌ No Permission!", ephemeral=True)
    vips = load_vips()
    if member.id in vips:
        vips.remove(member.id)
        save_vips(vips)
        await interaction.response.send_message(f"❌ {member.mention} removed from VIP.")
    else: await interaction.response.send_message("User not in VIP list.", ephemeral=True)

@bot.tree.command(name="listvip", description="Cek Semua Member VIP")
async def listvip(interaction: discord.Interaction):
    vips = load_vips()
    if not vips: return await interaction.response.send_message("Database VIP Kosong.")
    list_txt = "\n".join([f"• <@{uid}> (`{uid}`)" for uid in vips])
    embed = discord.Embed(title="👑 DATABASE MEMBER VIP", description=list_txt, color=0xffd700)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="status", description="Cek Status Bot")
async def status(interaction: discord.Interaction):
    ram = psutil.virtual_memory().percent
    cpu = psutil.cpu_percent()
    embed = discord.Embed(title="🚀 SYSTEM STATUS", color=0x2ecc71)
    embed.add_field(name="RAM Usage", value=f"{ram}%", inline=True)
    embed.add_field(name="CPU Usage", value=f"{cpu}%", inline=True)
    embed.add_field(name="Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Panduan Scanner")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ CARA KERJA SCANNER", color=0x9b59b6)
    embed.description = "1. Kirim file (.lua, .txt, .zip, .7z) di channel <#1469740150522380299>.\n2. Bot akan membongkar script dan mencari webhook/logger.\n3. Hasil akan keluar dengan tingkat bahaya %."
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Cek Latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")

# ================= SCANNER LOGIC (VIP ONLY) =================
@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != SCAN_CHANNEL_ID: return
    if message.attachments:
        vips = load_vips()
        if message.author.id not in vips:
            return await message.reply(f"🔒 **VIP ONLY!** Silakan minta akses di <#{REQ_VIP_CHANNEL_ID}>")

        for attachment in message.attachments:
            ext = os.path.splitext(attachment.filename)[1].lower()
            if ext not in [".lua", ".txt", ".zip", ".7z"]: continue
            await message.add_reaction("⏳")
            file_data = await attachment.read()
            pola, links, files_count = [], [], 0
            try:
                if ext in [".lua", ".txt"]:
                    content = file_data.decode(errors="ignore")
                    p, l = analyze_content(content)
                    pola.extend(p); links.extend(l); files_count = 1
                elif ext == ".zip":
                    with zipfile.ZipFile(io.BytesIO(file_data)) as z:
                        for f in z.namelist():
                            if f.lower().endswith((".lua", ".txt")):
                                c = z.read(f).decode(errors="ignore")
                                p, l = analyze_content(c); pola.extend(p); links.extend(l); files_count += 1
                elif ext == ".7z":
                    with py7zr.SevenZipFile(io.BytesIO(file_data), mode='r') as z:
                        names = [n for n in z.getnames() if n.lower().endswith((".lua", ".txt"))]
                        if names:
                            contents = z.read(names)
                            for name, bio in contents.items():
                                c = bio.read().decode(errors="ignore")
                                p, l = analyze_content(c); pola.extend(p); links.extend(l); files_count += 1
            except Exception as e: return await message.reply(f"❌ Error: `{e}`")

            pola, links = list(set(pola)), list(set(links))
            if links: s, c, d, cf = "🔴 BAHAYA TINGGI", 0xff0000, "100%", "95%"
            elif len(pola) >= 3: s, c, d, cf = "🟠 SANGAT MENCURIGAKAN", 0xe67e22, "50%", "80%"
            elif len(pola) >= 1: s, c, d, cf = "🟡 MENCURIGAKAN", 0xf1c40f, "25%", "75%"
            else: s, c, d, cf = "✅ AMAN", 0x2ecc71, "10%", "85%"

            embed = discord.Embed(title=s, color=c)
            embed.add_field(name="👤 User", value=message.author.mention, inline=True)
            embed.add_field(name="📂 File", value=f"`{attachment.filename}`", inline=True)
            embed.add_field(name="💀 Danger", value=f"**{d}**", inline=True)
            if pola: embed.add_field(name="📝 Pola", value="\n".join(pola), inline=False)
            if links: embed.add_field(name="🌐 Webhook", value="\n".join([f"🔗 [LINK]({l})" for l in links]), inline=False)
            embed.set_footer(text=f"Checked {files_count} files • Tatang Bot v2.6")
            await message.reply(embed=embed)
            await message.remove_reaction("⏳", bot.user)

bot.run(TOKEN)
