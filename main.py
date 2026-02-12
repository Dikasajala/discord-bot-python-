import discord
import os
import zipfile
import re
import py7zr
from discord.ext import commands

# ================= CONFIG =================

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1469740150522380299
MAX_SIZE = 8 * 1024 * 1024  # 8MB

ALLOWED_EXT = (".lua", ".luac", ".zip", ".txt", ".7z")

# ================= SCANNER ENGINE =================

PATTERNS = {
    "api.telegram.org": 4,
    "telegram token": 4,
    "discord webhook": 5,
    "token": 3,
    "password": 3,
    "loadstring": 2,
    "io.open": 2,
    "LuaObfuscator": 3,
    "sampGetPlayerNickname": 1
}

WEBHOOK_REGEX = r"https:\/\/(discord\.com|discordapp\.com)\/api\/webhooks\/\S+"


def scan_content(text):
    found = []
    score = 0

    for p, lvl in PATTERNS.items():
        if p.lower() in text.lower():
            found.append((p, lvl))
            score += lvl

    if re.search(WEBHOOK_REGEX, text):
        found.append(("Discord Webhook URL", 5))
        score += 5

    return found, score


def scan_zip(path):
    results = []
    score = 0

    try:
        with zipfile.ZipFile(path, 'r') as z:
            for name in z.namelist():
                if name.endswith((".lua", ".luac", ".txt")):
                    data = z.read(name).decode(errors="ignore")
                    found, s = scan_content(data)
                    results.extend(found)
                    score += s
    except:
        pass

    return results, score


def scan_7z(path):
    results = []
    score = 0

    try:
        with py7zr.SevenZipFile(path, mode='r') as z:
            for name, bio in z.readall().items():
                if name.endswith((".lua", ".luac", ".txt")):
                    data = bio.read().decode(errors="ignore")
                    found, s = scan_content(data)
                    results.extend(found)
                    score += s
    except:
        pass

    return results, score


def scan_file(path):

    if path.endswith(".zip"):
        return scan_zip(path)

    if path.endswith(".7z"):
        return scan_7z(path)

    if path.endswith(".txt"):
        with open(path, "r", errors="ignore") as f:
            content = f.read()
        return scan_content(content)

    with open(path, "rb") as f:
        content = f.read().decode(errors="ignore")

    return scan_content(content)


def danger_level(score):
    if score == 0:
        return "🟢 AMAN", 0x2ecc71
    elif score <= 3:
        return "🟡 MENCURIGAKAN", 0xf1c40f
    elif score <= 7:
        return "🟠 SANGAT MENCURIGAKAN", 0xe67e22
    else:
        return "🔴 BAHAYA TINGGI", 0xe74c3c


# ================= BOT SETUP =================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ================= READY =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot online sebagai {bot.user}")


# ================= STATUS =================

@bot.tree.command(name="status", description="Lihat status bot scanner")
async def status(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🤖 Status Bot Scanner",
        color=0x3498db
    )

    embed.add_field(name="📡 Status", value="🟢 Online", inline=True)
    embed.add_field(name="📁 Channel Scanner", value=f"<#{CHANNEL_ID}>", inline=True)
    embed.add_field(name="⚙️ Sistem", value="Pattern Detection", inline=True)

    embed.set_footer(text="Keylogger Detection Bot 🔍")

    await interaction.response.send_message(embed=embed)


# ================= MENU =================

@bot.tree.command(name="menu", description="Menu bantuan bot scanner")
async def menu(interaction: discord.Interaction):

    embed = discord.Embed(
        title="📋 Menu Bot Scanner",
        description="Upload file ke channel scanner untuk dianalisis",
        color=0x9b59b6
    )

    embed.add_field(
        name="📤 Cara Pakai",
        value=f"Upload file `.lua`, `.luac`, `.zip`, `.txt`, `.7z` di <#{CHANNEL_ID}>",
        inline=False
    )

    embed.add_field(
        name="🧪 Fitur Deteksi",
        value="""
🔹 Discord Webhook  
🔹 Telegram Token  
🔹 Password Grabber  
🔹 Obfuscator  
🔹 Loadstring Abuse  
""",
        inline=False
    )

    embed.set_footer(text="Scanner berbasis pattern 🔬")

    await interaction.response.send_message(embed=embed)


# ================= FILE SCANNER =================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.id != CHANNEL_ID:
        return

    if message.attachments:

        for attachment in message.attachments:

            # ===== LIMIT SIZE =====
            if attachment.size > MAX_SIZE:

                embed = discord.Embed(
                    title="📦 File Terlalu Besar",
                    description="⚠️ Ukuran file melebihi batas 8MB.",
                    color=0xe74c3c
                )

                embed.add_field(name="📁 File", value=attachment.filename, inline=False)
                embed.add_field(
                    name="📏 Ukuran",
                    value=f"{round(attachment.size / 1024 / 1024, 2)} MB",
                    inline=True
                )

                embed.set_footer(text="Scanner Bot 🔍")

                await message.channel.send(embed=embed)
                return

            filename = attachment.filename.lower()

            # ===== FILE TYPE CHECK =====
            if not filename.endswith(ALLOWED_EXT):

                embed = discord.Embed(
                    title="🚫 Format File Tidak Didukung",
                    description="File yang dikirim tidak termasuk format yang bisa discan.",
                    color=0xe74c3c
                )

                embed.add_field(name="📁 File Diterima", value=attachment.filename, inline=False)
                embed.add_field(
                    name="✅ Format yang Didukung",
                    value="`.lua` `.luac` `.zip` `.txt` `.7z`",
                    inline=False
                )

                embed.set_footer(text="Silakan kirim file sesuai format 🔍")

                await message.channel.send(embed=embed)
                return

            temp = f"temp_{filename}"
            await attachment.save(temp)

            patterns, score = scan_file(temp)
            status, color = danger_level(score)

            embed = discord.Embed(
                title="🔍 Hasil Analisis File",
                color=color
            )

            embed.add_field(name="📁 File", value=attachment.filename, inline=False)
            embed.add_field(name="⚠️ Status", value=status, inline=True)
            embed.add_field(name="📊 Score", value=str(score), inline=True)

            if patterns:
                text = "\n".join([f"🔸 {p} (Level {l})" for p, l in patterns])
            else:
                text = "✅ Tidak ditemukan pola mencurigakan"

            embed.add_field(name="🧬 Pola Terdeteksi", value=text, inline=False)

            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.set_footer(text=f"Diminta oleh {message.author}")

            await message.channel.send(embed=embed)

            os.remove(temp)

    await bot.process_commands(message)


bot.run(TOKEN)
