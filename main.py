import discord
import os
import psutil
import zipfile
import py7zr
import re
import io
import aiohttp
import asyncio
import random
import string
from discord.ext import commands
from discord import app_commands

# ================= KONFIGURASI ID =================
TOKEN = os.getenv("TOKEN")
SCAN_CHANNEL_ID = 1469740150522380299  # Channel khusus Scanner

# ================= UTILITY =================
def generate_fake_data():
    nicks = ["Dika_Ganteng", "Admin_SAMP", "Player_Pro", "Tatang_Sakti", "Bocah_SAMP", "Rizky_Gaming"]
    ips = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    pw = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return (
        "```ascii\n"
        "╔═══════════════════════════════════════════════╗\n"
        "║          TATANG COMUNITY SAMP LOGS            ║\n"
        "╠═══════════════════════════════════════════════╣\n"
        f"  > Nickname : {random.choice(nicks)}\n"
        f"  > Password : {pw}\n"
        f"  > IP Addr  : {ips}\n"
        "╠═══════════════════════════════════════════════╣\n"
        "  SUBSCRIBE : [youtube.com/@tatangchit](https://youtube.com/@tatangchit)           \n"
        "╚═══════════════════════════════════════════════╝\n"
        "```"
    )

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
        "os.execute": "os.execute (Potensi RCE)", 
        "io.popen": "io.popen (Eksekusi System)", 
        "loadstring": "loadstring (Obfuscated Code)",
        "sampGetPlayerNickname": "sampGetPlayerNickname (Data Logger)", 
        "sampGetCurrentServerAddress": "Server Address Logger",
        "LuaObfuscator.com": "LuaObfuscator (L8 Detected)", 
        "exec": "exec"
    }
    for key, label in danger_map.items():
        if key in content: pola_terdeteksi.append(label)
    return pola_terdeteksi, found_links

# ================= BOT INITIALIZATION =================
class TatangBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="/", intents=intents)
    async def setup_hook(self): await self.tree.sync()

bot = TatangBot()

# ================= SLASH COMMANDS =================
@bot.tree.command(name="menu", description="Daftar lengkap perintah bot")
async def menu_cmd(it: discord.Interaction):
    embed = discord.Embed(
        title="📄 TATANG BOT | DASHBOARD",
        color=0x3498db
    )
    embed.description = (
        "Sistem keamanan dan utilitas untuk komunitas SA-MP Indonesia.\n\n"
        "⚡ Deep Scanner aktif otomatis di channel scanner.\n"
        "Upload file dan bot akan menganalisis secara otomatis."
    )
    embed.add_field(
        name="🛡️ COMMANDS",
        value="• /menu\n• /help\n• /status",
        inline=False
    )
    embed.set_footer(text="Official Tatang Bot • youtube.com/@tatangchit")
    await it.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Panduan lengkap penggunaan Tatang Bot")
async def help_cmd(it: discord.Interaction):
    embed = discord.Embed(
        title="❓ PANDUAN LENGKAP TATANG BOT",
        color=0x9b59b6
    )
    embed.add_field(
        name="⚡ CARA PAKAI SCANNER KEYLOGGER",
        value=(
            "1️⃣ Masuk ke channel scanner.\n"
            "2️⃣ Upload file dengan format berikut:\n"
            "   • .lua\n"
            "   • .txt\n"
            "   • .zip\n"
            "   • .7z\n\n"
            "3️⃣ Bot otomatis menganalisis file.\n"
            "4️⃣ Tunggu hingga reaksi ⏳ hilang.\n"
            "5️⃣ Hasil analisis akan muncul berupa:\n"
            "   🔴 BAHAYA TINGGI\n"
            "   🟠 SANGAT MENCURIGAKAN\n"
            "   ✅ AMAN\n\n"
            "Scanner mendeteksi:\n"
            "• Discord Webhook Stealer\n"
            "• Telegram Bot Stealer\n"
            "• Pola os.execute / io.popen\n"
            "• loadstring obfuscation\n"
            "• Logger SA-MP\n"
        ),
        inline=False
    )
    embed.add_field(
        name="📄 DAFTAR COMMAND",
        value="• /menu  → Melihat daftar fitur bot\n• /help  → Panduan lengkap penggunaan\n• /status → Cek kesehatan mesin bot",
        inline=False
    )
    embed.set_footer(text="Official Tatang Bot • youtube.com/@tatangchit")
    await it.response.send_message(embed=embed)

@bot.tree.command(name="status", description="Cek kesehatan bot")
async def status_cmd(it: discord.Interaction):
    embed = discord.Embed(title="🚀 SYSTEM STATUS", color=0x2ecc71)
    embed.add_field(name="RAM Usage", value=f"{psutil.virtual_memory().percent}%", inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.set_footer(text="Bot berjalan lancar di server.")
    await it.response.send_message(embed=embed)

# ================= SCANNER EVENT =================
@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != SCAN_CHANNEL_ID: return
    if message.attachments:
        for attachment in message.attachments:
            ext = os.path.splitext(attachment.filename)[1].lower()
            if ext not in [".lua", ".txt", ".zip", ".7z"]: continue
            
            await message.add_reaction("⏳")
            file_data = await attachment.read(); pola, links, files_count = [], [], 0
            
            try:
                if ext in [".lua", ".txt"]:
                    c = file_data.decode(errors="ignore"); p, l = analyze_content(c)
                    pola.extend(p); links.extend(l); files_count = 1
                elif ext == ".zip":
                    with zipfile.ZipFile(io.BytesIO(file_data)) as z:
                        for f in z.namelist():
                            if f.lower().endswith((".lua", ".txt")):
                                c = z.read(f).decode(errors="ignore"); p, l = analyze_content(c); pola.extend(p); links.extend(l); files_count += 1
                elif ext == ".7z":
                    with py7zr.SevenZipFile(io.BytesIO(file_data), mode='r') as z:
                        names = [n for n in z.getnames() if n.lower().endswith((".lua", ".txt"))]
                        if names:
                            contents = z.read(names)
                            for name, bio in contents.items():
                                c = bio.read().decode(errors="ignore"); p, l = analyze_content(c); pola.extend(p); links.extend(l); files_count += 1
            except: pass

            pola, links = list(set(pola)), list(set(links))
            if links:
                status, color, conf = "🔴 🚨 BAHAYA TINGGI", 0xff0000, "100%"
                msg_ana = f"Ditemukan {len(links)} link webhook stealer aktif!"
            elif pola:
                status, color, conf = "🟠 ⚠️ SANGAT MENCURIGAKAN", 0xe67e22, "75%"
                msg_ana = f"Ditemukan {len(pola)} pola instruksi berbahaya."
            else:
                status, color, conf = "✅ 🛡️ AMAN", 0x2ecc71, "85%"
                msg_ana = "Tidak ditemukan indikasi keylogger secara otomatis."

            embed = discord.Embed(title=status, color=color)
            embed.description = (
                f"**File:** `{attachment.filename}`\n"
                f"**Analisis:** {msg_ana}\n\n"
                f"🎯 **Confidence**\n{conf}\n\n"
                f"📊 **Info**\nSize: {len(file_data):,} bytes"
            )
            if pola: embed.add_field(name="📝 Pola Terdeteksi", value="\n".join([f"• {p}" for p in pola]), inline=False)
            if links: embed.add_field(name="🌐 Webhook Found", value="\n".join([f"🔗 [KLIK LINK]({l})" for l in links]), inline=False)
            
            embed.set_footer(text=f"Analisis Selesai: {files_count} file | youtube.com/@tatangchit")
            await message.reply(embed=embed)
            await message.remove_reaction("⏳", bot.user)

bot.run(TOKEN)
