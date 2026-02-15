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

# ================= KONFIGURASI =================
TOKEN = os.getenv("TOKEN")
SCAN_CHANNEL_ID = 1469740150522380299      
REQ_VIP_CHANNEL_ID = 1472535677634740398   
ADMIN_ROLE_ID = 1471265207945924619        
VIP_FILE = "vips.json"

# ================= TOOLS =================
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
    
    # Regex Webhook & Telegram
    dw_regex = r"https://discord\.com/api/webhooks/\d+/\S+"
    tg_regex = r"https://api\.telegram\.org/bot\d+:\S+"
    
    dw_links = re.findall(dw_regex, content)
    tg_links = re.findall(tg_regex, content)
    
    if dw_links: found_links.extend(dw_links)
    if tg_links: found_links.extend(tg_links)
        
    # Daftar Pola Bahaya
    danger_map = {
        "os.execute": "System Command Execution",
        "io.popen": "Remote Process Open",
        "loadstring": "Hidden Executable Code",
        "sampGetPlayerNickname": "Data Grabber (Nickname)",
        "sampGetCurrentServerAddress": "IP Logger (Server)",
        "LuaObfuscator.com": "Highly Obfuscated (Anti-Read)",
        "exec": "Dynamic Command Execution"
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

# ================= COMMANDS =================
@bot.tree.command(name="menu", description="Dashboard Utama Tatang Bot")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(title="📑 TATANG BOT | DASHBOARD", color=0x3498db)
    embed.add_field(name="👑 **ADMIN**", value="`/addvip` • `/listvip`", inline=True)
    embed.add_field(name="🛠️ **INFO**", value="`/status` • `/help`", inline=True)
    embed.set_footer(text="Premium Security • v2.3")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="addvip", description="Tambah VIP (Management Only)")
async def addvip(interaction: discord.Interaction, member: discord.Member):
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if role not in interaction.user.roles: # Akses ditolak jika tidak punya role
        return await interaction.response.send_message("❌ **Akses Ditolak!** Khusus Management.", ephemeral=True)
    
    vips = load_vips()
    if member.id not in vips:
        vips.append(member.id)
        save_vips(vips)
        await interaction.response.send_message(f"✅ {member.mention} ditambahkan ke VIP.")

# ================= SCANNER LOGIC =================
@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != SCAN_CHANNEL_ID: return

    if message.attachments:
        vips = load_vips()
        if message.author.id not in vips: # Proteksi VIP
            embed = discord.Embed(title="🔒 PREMIUM ACCESS REQUIRED", color=0xffd700)
            embed.description = f"Halo {message.author.mention}, fitur scan hanya untuk VIP.\n\n🛡️ **Minta Akses:** <#{REQ_VIP_CHANNEL_ID}>"
            return await message.reply(embed=embed)

        for attachment in message.attachments:
            ext = os.path.splitext(attachment.filename)[1].lower()
            # SEKARANG MENDUKUNG .txt
            if ext not in [".lua", ".txt", ".zip", ".7z"]: continue

            await message.add_reaction("⏳")
            file_data = await attachment.read()
            pola, links = [], []
            files_count = 0

            try:
                # Scan File Satuan (.lua / .txt)
                if ext in [".lua", ".txt"]:
                    content = file_data.decode(errors="ignore")
                    p, l = analyze_content(content)
                    pola.extend(p); links.extend(l)
                    files_count = 1
                
                # Scan File Arsip (.zip)
                elif ext == ".zip":
                    with zipfile.ZipFile(io.BytesIO(file_data)) as z:
                        for f in z.namelist():
                            if f.lower().endswith((".lua", ".txt")):
                                c = z.read(f).decode(errors="ignore")
                                p, l = analyze_content(c); pola.extend(p); links.extend(l)
                                files_count += 1
                
                # Scan File Arsip (.7z) - FIX ERROR
                elif ext == ".7z":
                    with py7zr.SevenZipFile(io.BytesIO(file_data), mode='r') as z:
                        target_files = [n for n in z.getnames() if n.lower().endswith((".lua", ".txt"))]
                        if target_files:
                            contents = z.read(target_files)
                            for name, bio in contents.items():
                                c = bio.read().decode(errors="ignore")
                                p, l = analyze_content(c); pola.extend(p); links.extend(l)
                                files_count += 1
            except Exception as e:
                await message.remove_reaction("⏳", bot.user)
                return await message.reply(f"❌ **Read Error:** `{e}`")

            # TENTUKAN STATUS & BAHAYA %
            pola, links = list(set(pola)), list(set(links))
            if links:
                status, color, danger, conf = "🔴 BAHAYA TINGGI", 0xff0000, "100%", "95%"
            elif len(pola) >= 2:
                status, color, danger, conf = "🟠 SANGAT MENCURIGAKAN", 0xe67e22, "50%", "80%"
            elif len(pola) == 1:
                status, color, danger, conf = "🟡 MENCURIGAKAN", 0xf1c40f, "25%", "75%"
            else:
                status, color, danger, conf = "✅ AMAN", 0x2ecc71, "10%", "85%"

            # UI EMBED PREMIUM
            embed = discord.Embed(title=status, color=color)
            embed.add_field(name="👤 **User:**", value=message.author.mention, inline=True)
            embed.add_field(name="📂 **File:**", value=f"`{attachment.filename}`", inline=True)
            embed.add_field(name="📊 **Size:**", value=f"`{format_size(attachment.size)}`", inline=True)
            
            embed.add_field(name="🎯 **Confidence:**", value=f"`{conf}`", inline=True)
            embed.add_field(name="💀 **Danger:**", value=f"**{danger}**", inline=True)
            embed.add_field(name="🔍 **Files Checked:**", value=f"`{files_count} Files`", inline=True)

            if pola:
                embed.add_field(name="📝 **Pola Terdeteksi:**", value="\n".join(pola), inline=False)
            if links:
                links_text = "\n".join([f"🔗 [KLIK LINK WEBHOOK]({l})" for l in links])
                embed.add_field(name="🌐 **Webhook Found:**", value=links_text, inline=False)

            embed.set_footer(text="Dianalisis Otomatis • Tatang Bot v2.3")
            await message.reply(content=f"📊 **Hasil Scan untuk {message.author.mention}:**", embed=embed)
            await message.remove_reaction("⏳", bot.user)

bot.run(TOKEN)
