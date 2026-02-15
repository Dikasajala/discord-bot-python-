import discord
import os
import zipfile
import re
import py7zr
import json
import aiohttp
from discord.ext import commands
from discord import app_commands

# ================= KONFIGURASI =================
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1469740150522380299
MAX_SIZE = 8 * 1024 * 1024 # 8MB
ALLOWED_EXT = (".lua", ".luac", ".zip", ".txt", ".7z")
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

# ================= SCANNER ENGINE =================
PATTERNS = {
    "api.telegram.org": 5,
    "discord.com/api/webhooks": 5,
    "os.execute": 4,
    "io.popen": 4,
    "io.open": 2,
    "loadstring": 3,
    "LuaObfuscator": 4,
    "password": 3,
    "steal": 5,
    "grabber": 5,
    "sampGetPlayerNickname": 1
}

WEBHOOK_REGEX = r"https:\/\/(?:discord\.com|discordapp\.com)\/api\/webhooks\/[0-9]+\/[A-Za-z0-9\-_]+"
TELEGRAM_REGEX = r"[0-9]{7,10}:[a-zA-Z0-9_-]{35}"

def is_library_file(filepath):
    parts = filepath.replace("\\", "/").lower().split("/")
    return "lib" in parts or "libs" in parts

def scan_content(text):
    found = []
    score = 0
    extracted_links = []
    
    webhooks = re.findall(WEBHOOK_REGEX, text)
    tokens = re.findall(TELEGRAM_REGEX, text)
    
    for wh in webhooks:
        found.append(("Discord Webhook", 5))
        score += 5
        extracted_links.append(f"🔗 **Webhook:** {wh}")

    for tk in tokens:
        found.append(("Telegram Bot Token", 5))
        score += 5
        extracted_links.append(f"🤖 **Bot Token:** {tk}")

    for p, lvl in PATTERNS.items():
        if p.lower() in text.lower():
            if not any(p in f[0] for f in found):
                found.append((p, lvl))
                score += lvl

    return found, score, extracted_links

def scan_archive(path, archive_type="zip"):
    results, score, all_links = [], 0, []
    try:
        if archive_type == "zip":
            with zipfile.ZipFile(path, 'r') as z:
                for name in z.namelist():
                    if is_library_file(name): continue
                    if name.endswith((".lua", ".luac", ".txt")):
                        data = z.read(name).decode(errors="ignore")
                        f, s, l = scan_content(data)
                        results.extend(f); score += s; all_links.extend(l)
        else:
            with py7zr.SevenZipFile(path, mode='r') as z:
                for name, bio in z.readall().items():
                    if is_library_file(name): continue
                    if name.endswith((".lua", ".luac", ".txt")):
                        data = bio.read().decode(errors="ignore")
                        f, s, l = scan_content(data)
                        results.extend(f); score += s; all_links.extend(l)
    except: pass
    return list(set(results)), score, list(set(all_links))

def get_danger_info(score):
    if score == 0: return "✅ AMAN", 0x2ecc71
    if score <= 4: return "⚠️ MENCURIGAKAN", 0xf1c40f
    if score <= 8: return "🔥 BAHAYA", 0xe67e22
    return "💀 SANGAT BERBAHAYA", 0xe74c3c

# ================= BOT SETUP =================
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# ================= COMMANDS =================

@bot.tree.command(name="addvip", description="Berikan akses VIP Scanner ke user")
async def addvip(interaction: discord.Interaction, member: discord.Member):
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if role not in interaction.user.roles:
        return await interaction.response.send_message("❌ Anda tidak memiliki izin Management!", ephemeral=True)

    vips = load_vips()
    if member.id not in vips:
        vips.append(member.id)
        save_vips(vips)
        embed = discord.Embed(title="✨ VIP ACCESS GRANTED", description=f"Selamat {member.mention}, status VIP kamu telah aktif!", color=0x2ecc71)
        embed.set_image(url="https://share.cdn.viber.com/client/cgi-bin/get_sticker.cgi?f=7944111&s=400&u=0")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("User sudah VIP.", ephemeral=True)

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != CHANNEL_ID: return

    if message.attachments:
        vips = load_vips()
        if message.author.id not in vips:
            embed = discord.Embed(
                title="🔒 PREMIUM FEATURE LOCKED",
                description=f"Halo {message.author.mention}, fitur scanner ini hanya untuk **User VIP**.\n\nSilakan hubungi **Owner** (<@{OWNER_ID}>) untuk akses!",
                color=0xffd700
            )
            embed.set_image(url="https://share.cdn.viber.com/client/cgi-bin/get_sticker.cgi?f=7944111&s=400&u=0")
            return await message.reply(embed=embed)

        for attachment in message.attachments:
            if attachment.size > MAX_SIZE:
                return await message.reply("❌ File terlalu besar (Max 8MB).")

            ext = os.path.splitext(attachment.filename)[1].lower()
            if ext not in ALLOWED_EXT: continue

            temp_path = f"temp_{attachment.filename}"
            await attachment.save(temp_path)

            if ext == ".zip": f, s, l = scan_archive(temp_path, "zip")
            elif ext == ".7z": f, s, l = scan_archive(temp_path, "7z")
            else:
                with open(temp_path, "r", errors="ignore") as file: f, s, l = scan_content(file.read())

            status_txt, color = get_danger_info(s)
            size_txt = f"{round(attachment.size/1024, 1)} KB"

            embed = discord.Embed(title="🔍 ANALISIS SECURITY - ANTI STEALER", color=color)
            embed.description = f"👤 **Pengirim:** {message.author.mention}\n📂 **File:** `{attachment.filename}`\n📏 **Ukuran:** `{size_txt}`"
            embed.add_field(name="🛡️ Status", value=f"**{status_txt}**", inline=True)
            embed.add_field(name="📊 Score", value=f"`{s}`", inline=True)
            
            if f:
                det = "\n".join([f"🔸 {p} *(Lvl {lv})*" for p, lv in list(set(f))])
                embed.add_field(name="🧩 Pola Terdeteksi", value=det, inline=False)
            
            if l:
                embed.add_field(name="🚨 DATA TEREKSTRAK", value=f"```\n" + "\n".join(l) + "\n```", inline=False)

            embed.set_footer(text="Anti-Stealer Lab • Lib folder skipped")
            embed.set_thumbnail(url=message.author.display_avatar.url)
            
            await message.channel.send(content=message.author.mention, embed=embed)
            os.remove(temp_path)

bot.run(TOKEN)
