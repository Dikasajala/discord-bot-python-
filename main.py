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
SCAN_CHANNEL_ID = 1469740150522380299      # Channel Scan
REQ_VIP_CHANNEL_ID = 1472535677634740398   # Channel Request VIP
ADMIN_ROLE_ID = 1471265207945924619        # Role Management
OWNER_ID = 1465731110162927707             # ID Owner
VIP_FILE = "vips.json"

# ================= DATABASE & TOOLS =================
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
    
    # 1. Deteksi Link (Webhook Discord & Telegram)
    dw_regex = r"https://discord\.com/api/webhooks/\d+/\S+"
    tg_regex = r"https://api\.telegram\.org/bot\d+:\S+"
    
    dw_links = re.findall(dw_regex, content)
    tg_links = re.findall(tg_regex, content)
    
    if dw_links: found_links.extend(dw_links)
    if tg_links: found_links.extend(tg_links)
        
    # 2. Deteksi Pola Mencurigakan (Non-Webhook)
    danger_map = {
        "os.execute": "System Command Execution (os.execute)",
        "io.popen": "Remote Process Open (io.popen)",
        "loadstring": "Hidden Executable Code (loadstring)",
        "sampGetPlayerNickname": "Data Grabber (sampGetPlayerNickname)",
        "sampGetCurrentServerAddress": "IP Logger (sampGetCurrentServerAddress)",
        "LuaObfuscator.com": "Obfuscated Code (Anti-Read)"
    }

    for key, label in danger_map.items():
        if key in content:
            pola_terdeteksi.append(f"• {label}")

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

# ================= EVENTS =================
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is Online and Protecting!")

@bot.event
async def on_message(message):
    if message.author.bot: return

    # Logika Scan di Channel Tertentu
    if message.channel.id == SCAN_CHANNEL_ID and message.attachments:
        vips = load_vips()
        
        # JIKA BUKAN VIP
        if message.author.id not in vips:
            embed = discord.Embed(title="🔒 PREMIUM ACCESS REQUIRED", color=0xffd700)
            embed.description = (
                f"Halo {message.author.mention}, fitur **Deep Scanner** hanya untuk VIP.\n\n"
                f"🛡️ **Minta Akses:** <#{REQ_VIP_CHANNEL_ID}>\n"
                f"👑 **Owner:** <@{OWNER_ID}>"
            )
            embed.set_image(url="https://share.cdn.viber.com/client/cgi-bin/get_sticker.cgi?f=7944111&s=400&u=0")
            return await message.reply(embed=embed)

        # JIKA VIP, PROSES SCAN
        for attachment in message.attachments:
            ext = os.path.splitext(attachment.filename)[1].lower()
            if ext not in [".lua", ".zip", ".7z"]: continue

            await message.add_reaction("⏳")
            file_data = await attachment.read()
            threats_pola = []
            threats_links = []

            # Membaca isi file (Support Zip & 7z)
            try:
                if ext == ".lua":
                    content = file_data.decode(errors="ignore")
                    threats_pola, threats_links = analyze_content(content)
                elif ext == ".zip":
                    with zipfile.ZipFile(io.BytesIO(file_data)) as z:
                        for f in z.namelist():
                            if f.endswith(".lua"):
                                c = z.read(f).decode(errors="ignore")
                                p, l = analyze_content(c)
                                threats_pola.extend(p); threats_links.extend(l)
                elif ext == ".7z":
                    with py7zr.SevenZipFile(io.BytesIO(file_data), mode='r') as z:
                        for name, bio in z.readall().items():
                            if name.endswith(".lua"):
                                c = bio.read().decode(errors="ignore")
                                p, l = analyze_content(c)
                                threats_pola.extend(p); threats_links.extend(l)
            except Exception as e:
                return await message.reply(f"❌ Error saat membaca file: `{e}`")

            # Tentukan Status UI
            threats_pola = list(set(threats_pola))
            threats_links = list(set(threats_links))

            if threats_links:
                title, color = "🔴 🚨 BAHAYA TINGGI", 0xff0000
            elif threats_pola:
                title, color = "🟡 ⚠️ SANGAT MENCURIGAKAN", 0xffa500
            else:
                title, color = "✅ 🛡️ AMAN", 0x00ff00

            # UI Final
            embed = discord.Embed(title=title, color=color)
            embed.add_field(name="👤 **User Scanner:**", value=message.author.mention, inline=True)
            embed.add_field(name="📂 **Nama File:**", value=f"`{attachment.filename}`", inline=True)
            embed.add_field(name="📊 **Ukuran File:**", value=f"`{format_size(attachment.size)}`", inline=True)

            if threats_pola:
                embed.add_field(name="📝 **Pola Terdeteksi:**", value="\n".join(threats_pola), inline=False)
            
            if threats_links:
                links_text = "\n".join([f"🔗 [KLIK LINK WEBHOOK]({l})" for l in threats_links])
                embed.add_field(name="🌐 **Webhook Terdeteksi:**", value=links_text, inline=False)

            embed.set_footer(text="Dianalisis Otomatis • Tatang Bot v2.0", icon_url=bot.user.avatar.url)
            await message.reply(content=f"📊 **Hasil Scan untuk {message.author.mention}:**", embed=embed)
            await message.remove_reaction("⏳", bot.user)

# ================= SLASH COMMANDS =================

@bot.tree.command(name="menu", description="Dashboard utama bot")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 TATANG BOT | MAIN MENU", color=0x3498db)
    embed.add_field(name="👑 **MANAGEMENT**", value="`/addvip` • `/removevip`\n`/listvip` • Cek Database", inline=False)
    embed.add_field(name="⚙️ **SYSTEM**", value="`/status` • `/help`", inline=False)
    embed.set_image(url="https://share.cdn.viber.com/client/cgi-bin/get_sticker.cgi?f=7944111&s=400&u=0")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="addvip", description="Berikan akses VIP")
async def addvip(interaction: discord.Interaction, member: discord.Member):
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if interaction.user.id != OWNER_ID and role not in interaction.user.roles:
        return await interaction.response.send_message("❌ Izin Management diperlukan!", ephemeral=True)
    
    vips = load_vips()
    if member.id not in vips:
        vips.append(member.id)
        save_vips(vips)
        await interaction.response.send_message(f"✅ {member.mention} Berhasil menjadi VIP!")
    else:
        await interaction.response.send_message("User sudah VIP.", ephemeral=True)

@bot.tree.command(name="listvip", description="Daftar semua member VIP")
async def listvip(interaction: discord.Interaction):
    vips = load_vips()
    if not vips: return await interaction.response.send_message("Database Kosong.", ephemeral=True)
    
    text = "\n".join([f"{i+1}. <@{uid}>" for i, uid in enumerate(vips)])
    embed = discord.Embed(title="👑 DAFTAR USER VIP", description=text, color=0xffd700)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="status", description="Cek mesin bot")
async def status(interaction: discord.Interaction):
    ram = psutil.virtual_memory().percent
    await interaction.response.send_message(f"🟢 **Online** | 🧠 **RAM:** `{ram}%` | ⚡ **Ping:** `{round(bot.latency * 1000)}ms`")

bot.run(TOKEN)
