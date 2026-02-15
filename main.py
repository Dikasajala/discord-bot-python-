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

# ================= CONFIGURATION =================
TOKEN = os.getenv("TOKEN")
SCAN_CHANNEL_ID = 1469740150522380299      
REQ_VIP_CHANNEL_ID = 1472535677634740398   
ADMIN_ROLE_ID = 1471265207945924619        
VIP_FILE = "vips.json"

# ================= DATABASE TOOLS =================
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
        "sampGetCurrentServerAddress": "IP Logger (Server)",
        "LuaObfuscator.com": "Highly Obfuscated (Anti-Read)",
        "getSAMPUserProfile": "Account Data Stealer"
    }

    for key, label in danger_map.items():
        if key in content:
            pola_terdeteksi.append(f"• {label}")

    return pola_terdeteksi, found_links

# ================= BOT INITIALIZATION =================
class TatangBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = TatangBot()

# ================= APP COMMANDS (SLASH) =================

@bot.tree.command(name="menu", description="Dashboard Utama Tatang Bot")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📑 TATANG BOT | DASHBOARD MENU",
        description="Pusat kendali fitur keamanan dan manajemen VIP server.",
        color=0x3498db
    )
    embed.add_field(
        name="👑 **ADMINISTRATION**", 
        value="> `/addvip` • Berikan akses VIP\n> `/removevip` • Cabut akses VIP\n> `/listvip` • Database User VIP", 
        inline=False
    )
    embed.add_field(
        name="🛠️ **UTILITY & INFO**", 
        value="> `/status` • Status sistem bot\n> `/help` • Panduan Deep Scanner", 
        inline=False
    )
    embed.add_field(
        name="🛡️ **SECURITY STATUS**", 
        value=f"> **Scanner:** Aktif ✅\n> **Channel:** <#{SCAN_CHANNEL_ID}>\n> **Format:** `.lua`, `.zip`, `.7z`", 
        inline=False
    )
    embed.set_image(url="https://share.cdn.viber.com/client/cgi-bin/get_sticker.cgi?f=7944111&s=400&u=0")
    embed.set_footer(text="Premium Management System • v2.1", icon_url=bot.user.avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Panduan lengkap penggunaan scanner")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="❓ CARA KERJA DEEP SCANNER", color=0x9b59b6)
    embed.add_field(name="1. Upload File", value="Kirim file `.lua`, `.zip`, atau `.7z` di channel scan.", inline=False)
    embed.add_field(name="2. Analisis Pola", value="Bot membongkar isi file dan mencari baris kode berbahaya (Stealer/Logger).", inline=False)
    embed.add_field(name="3. Tingkat Bahaya", value="**10%** = Aman\n**25-50%** = Mencurigakan\n**100%** = Bahaya Link Webhook", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="addvip", description="Berikan akses VIP (Management Only)")
async def addvip(interaction: discord.Interaction, member: discord.Member):
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if role not in interaction.user.roles:
        return await interaction.response.send_message("❌ **Akses Ditolak!** Khusus Role Management.", ephemeral=True)

    vips = load_vips()
    if member.id not in vips:
        vips.append(member.id)
        save_vips(vips)
        embed = discord.Embed(title="✨ VIP ACCESS GRANTED", description=f"{member.mention} Berhasil menjadi VIP! ✅", color=0x2ecc71)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("User sudah VIP.", ephemeral=True)

# ================= SCANNER LOGIC =================
@bot.event
async def on_message(message):
    if message.author.bot: return

    if message.channel.id == SCAN_CHANNEL_ID and message.attachments:
        vips = load_vips()
        
        if message.author.id not in vips:
            embed = discord.Embed(title="🔒 PREMIUM ACCESS REQUIRED", color=0xffd700)
            embed.description = (
                f"Halo {message.author.mention}, fitur **Deep Scanner** hanya untuk VIP.\n\n"
                f"🛡️ **Minta Akses:** <#{REQ_VIP_CHANNEL_ID}>"
            )
            embed.set_image(url="https://share.cdn.viber.com/client/cgi-bin/get_sticker.cgi?f=7944111&s=400&u=0")
            return await message.reply(embed=embed)

        for attachment in message.attachments:
            ext = os.path.splitext(attachment.filename)[1].lower()
            if ext not in [".lua", ".zip", ".7z"]: continue

            await message.add_reaction("⏳")
            file_data = await attachment.read()
            threats_pola, threats_links = [], []

            try:
                # Logic pembacaan file sama (Lua, Zip, 7z)
                if ext == ".lua":
                    content = file_data.decode(errors="ignore")
                    threats_pola, threats_links = analyze_content(content)
                elif ext == ".zip":
                    with zipfile.ZipFile(io.BytesIO(file_data)) as z:
                        for f in z.namelist():
                            if f.endswith(".lua"):
                                c = z.read(f).decode(errors="ignore"); p, l = analyze_content(c)
                                threats_pola.extend(p); threats_links.extend(l)
                elif ext == ".7z":
                    with py7zr.SevenZipFile(io.BytesIO(file_data), mode='r') as z:
                        for name, bio in z.readall().items():
                            if name.endswith(".lua"):
                                c = bio.read().decode(errors="ignore"); p, l = analyze_content(c)
                                threats_pola.extend(p); threats_links.extend(l)
            except Exception as e:
                return await message.reply(f"❌ Read Error: `{e}`")

            # TINGKAT BAHAYA (%) [Requirement User]
            threats_pola = list(set(threats_pola))
            threats_links = list(set(threats_links))
            
            if threats_links:
                status, color, danger, conf = "🔴 BAHAYA TINGGI", 0xff0000, "100%", "95%"
            elif len(threats_pola) > 2:
                status, color, danger, conf = "🟠 SANGAT MENCURIGAKAN", 0xe67e22, "50%", "80%"
            elif len(threats_pola) > 0:
                status, color, danger, conf = "🟡 MENCURIGAKAN", 0xf1c40f, "25%", "75%"
            else:
                status, color, danger, conf = "✅ AMAN", 0x2ecc71, "10%", "85%"

            # UI FINAL RAPI & PANJANG
            embed = discord.Embed(title=status, color=color)
            embed.add_field(name="👤 **User Scanner:**", value=message.author.mention, inline=True)
            embed.add_field(name="📂 **Nama File:**", value=f"`{attachment.filename}`", inline=True)
            embed.add_field(name="📊 **Ukuran File:**", value=f"`{format_size(attachment.size)}`", inline=True)
            
            embed.add_field(name="🎯 **Confidence:**", value=f"`{conf}`", inline=True)
            embed.add_field(name="💀 **Tingkat Bahaya:**", value=f"**{danger}**", inline=True)
            embed.add_field(name="🔍 **Metode:**", value="Analisis Berbasis Pola", inline=True)

            if threats_pola:
                embed.add_field(name="📝 **Pola Terdeteksi:**", value="\n".join(threats_pola), inline=False)
            
            if threats_links:
                links_text = "\n".join([f"🔗 [KLIK LINK WEBHOOK]({l})" for l in threats_links])
                embed.add_field(name="🌐 **Webhook Terdeteksi:**", value=links_text, inline=False)

            embed.set_footer(text="Dianalisis Otomatis • Tatang Bot v2.1")
            await message.reply(content=f"📊 **Hasil Scan untuk {message.author.mention}:**", embed=embed)
            await message.remove_reaction("⏳", bot.user)

bot.run(TOKEN)
