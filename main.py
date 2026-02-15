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
        
    danger_map = {
        "os.execute": "os.execute",
        "io.popen": "io.popen",
        "loadstring": "loadstring",
        "sampGetPlayerNickname": "sampGetPlayerNickname",
        "sampGetCurrentServerAddress": "sampGetCurrentServerAddress",
        "LuaObfuscator.com": "LuaObfuscator.com (L8)",
        "exec": "exec"
    }

    for key, label in danger_map.items():
        if key in content:
            pola_terdeteksi.append(label)

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

# ================= SEMUA SLASH COMMANDS (LENGKAP) =================

@bot.tree.command(name="menu", description="Dashboard Utama Tatang Bot")
async def menu(interaction: discord.Interaction):
    # Match Dashboard v2.1
    embed = discord.Embed(title="📄 TATANG BOT | DASHBOARD MENU", color=0x3498db)
    embed.description = "Pusat kendali fitur keamanan dan manajemen VIP server."
    
    embed.add_field(
        name="👑 **ADMINISTRATION**",
        value="`/addvip` • Berikan akses VIP\n`/removevip` • Cabut akses VIP\n`/listvip` • Database User VIP",
        inline=False
    )
    
    embed.add_field(
        name="🛠️ **UTILITY & INFO**",
        value="`/status` • Status sistem bot\n`/help` • Panduan Deep Scanner",
        inline=False
    )
    
    embed.add_field(
        name="🛡️ **SECURITY STATUS**",
        value=f"**Scanner:** Aktif ✅\n**Channel:** <#1469740150522380299>\n**Format:** .lua, .zip, .7z",
        inline=False
    )

    embed.set_footer(text="Premium Management System • v2.1")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Panduan Cara Kerja Scanner")
async def help_cmd(interaction: discord.Interaction):
    # Match Help Style
    embed = discord.Embed(title="❓ CARA KERJA DEEP SCANNER", color=0x9b59b6)
    embed.add_field(name="1. Upload File", value="Kirim file `.lua`, `.zip`, atau `.7z` di channel scan.", inline=False)
    embed.add_field(name="2. Analisis Pola", value="Bot membongkar isi file dan mencari baris kode berbahaya (Stealer/Logger).", inline=False)
    embed.add_field(name="3. Tingkat Bahaya", value="**10%** = Aman\n**25-50%** = Mencurigakan\n**100%** = Bahaya Link Webhook", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="addvip", description="Berikan akses VIP kepada user")
async def addvip(interaction: discord.Interaction, member: discord.Member):
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if role not in interaction.user.roles:
        return await interaction.response.send_message("❌ **Akses Ditolak!**", ephemeral=True)
    
    vips = load_vips()
    if member.id not in vips:
        vips.append(member.id)
        save_vips(vips)
        # Match VIP Granted Style
        embed = discord.Embed(title="✨ VIP ACCESS GRANTED", description=f"{member.mention} Berhasil menjadi VIP! ✅", color=0x2ecc71)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("User sudah VIP.", ephemeral=True)

@bot.tree.command(name="removevip", description="Cabut akses VIP user")
async def removevip(interaction: discord.Interaction, member: discord.Member):
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if role not in interaction.user.roles:
        return await interaction.response.send_message("❌ **Akses Ditolak!**", ephemeral=True)
    
    vips = load_vips()
    if member.id in vips:
        vips.remove(member.id)
        save_vips(vips)
        await interaction.response.send_message(f"✅ Akses VIP {member.mention} telah dicabut.")
    else:
        await interaction.response.send_message("User bukan anggota VIP.", ephemeral=True)

@bot.tree.command(name="listvip", description="Lihat daftar database member VIP")
async def listvip(interaction: discord.Interaction):
    vips = load_vips()
    if not vips:
        return await interaction.response.send_message("Database VIP masih kosong.")
    
    mentions = "\n".join([f"• <@{uid}>" for uid in vips])
    embed = discord.Embed(title="👑 DATABASE USER VIP", description=mentions, color=0xf1c40f)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="status", description="Cek status server bot")
async def status(interaction: discord.Interaction):
    ram = psutil.virtual_memory().percent
    ping = round(bot.latency * 1000)
    embed = discord.Embed(title="🚀 SYSTEM STATUS", color=0x2ecc71)
    embed.add_field(name="RAM Usage", value=f"{ram}%", inline=True)
    embed.add_field(name="Bot Latency", value=f"{ping}ms", inline=True)
    await interaction.response.send_message(embed=embed)

# ================= SCANNER LOGIC (VIP ONLY) =================
@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != SCAN_CHANNEL_ID: return

    if message.attachments:
        vips = load_vips()
        if message.author.id not in vips:
            # Match Required Style
            embed = discord.Embed(title="🔒 PREMIUM ACCESS REQUIRED", color=0xf1c40f)
            embed.description = f"Halo {message.author.mention}, fitur **Deep Scanner** hanya untuk VIP.\n\n🛡️ **Minta Akses:** <#{REQ_VIP_CHANNEL_ID}>"
            return await message.reply(embed=embed)

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
                    # FIX: Menghindari error 'readall'
                    with py7zr.SevenZipFile(io.BytesIO(file_data), mode='r') as z:
                        names = [n for n in z.getnames() if n.lower().endswith((".lua", ".txt"))]
                        if names:
                            contents = z.read(names)
                            for name, bio in contents.items():
                                c = bio.read().decode(errors="ignore")
                                p, l = analyze_content(c); pola.extend(p); links.extend(l); files_count += 1
            except Exception as e: 
                await message.remove_reaction("⏳", bot.user)
                return await message.reply(f"❌ **Read Error:** `{e}`")

            # Match Scan Result Style
            pola, links = list(set(pola)), list(set(links))
            if links:
                status, color, conf = "🔴 🚨 BAHAYA TINGGI", 0xff0000, "75%"
                analisis_msg = f"Ditemukan {len(links)} link webhook berbahaya."
            elif len(pola) >= 2:
                status, color, conf = "🟠 ⚠️ SANGAT MENCURIGAKAN", 0xe67e22, "75%"
                analisis_msg = f"Ditemukan {len(pola)} pola mencurigakan. Pola paling berbahaya memiliki level 3."
            elif len(pola) == 1:
                status, color, conf = "🟡 🤔 MENCURIGAKAN", 0xf1c40f, "75%"
                analisis_msg = "Ditemukan 1 pola mencurigakan. Pola paling berbahaya memiliki level 2."
            else:
                status, color, conf = "✅ 🛡️ AMAN", 0x2ecc71, "85%"
                analisis_msg = "Analisis manual tidak menemukan pola berbahaya."

            embed = discord.Embed(title=status, color=color)
            embed.description = (
                f"**File:** `{attachment.filename}`\n"
                f"**Tujuan Script:** Analisis manual berbasis pola\n"
                f"**Analisis:** {analisis_msg}\n\n"
                f"🎯 **Confidence**\n{conf}\n\n"
                f"📊 **File Info**\nSize: {len(file_data):,} bytes\nType: {ext}"
            )

            if pola:
                pola_list = "\n".join([f"• {p} di {attachment.filename}" for p in pola])
                embed.add_field(name=f"📝 Pola Terdeteksi ({len(pola)})", value=pola_list, inline=False)
            
            if links:
                links_list = "\n".join([f"🔗 [KLIK LINK WEBHOOK]({l})" for l in links])
                embed.add_field(name="🌐 Webhook Found", value=links_list, inline=False)

            embed.set_footer(text=f"Dianalisis oleh: Manual • {files_count} file diperiksa")
            await message.reply(embed=embed)
            await message.remove_reaction("⏳", bot.user)

bot.run(TOKEN)
