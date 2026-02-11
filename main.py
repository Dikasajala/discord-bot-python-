import discord
import zipfile
import io
import re
import os

TOKEN = os.getenv("DISCORD_TOKEN")
SCAN_CHANNEL_ID = 1469740150522380299  # ganti dengan channel scan kamu

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

# =========================
# 🔎 SCANNER ENGINE
# =========================
def scan_content(content):
    content_lower = content.lower()
    risk_score = 0
    detected_patterns = []

    # 🔴 BERBAHAYA
    dangerous_patterns = [
        r"discord(app)?\.com/api/webhooks",
        r"api\.telegram\.org",
        r"t\.me/",
        r"performhttprequest",
        r"fetchremote",
        r"socket\.http",
        r"require\s*\(?['\"]socket",
        r"setclipboard",
        r"onclientkey",
        r"keyboard",
        r"keylogger"
    ]

    # 🟡 MENCURIGAKAN
    warning_patterns = [
        r"loadstring",
        r"assert\s*\(\s*load",
        r"base64",
        r"string\.char",
        r"\.\.",
        r"while\s+true\s+do"
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, content_lower):
            risk_score += 35
            detected_patterns.append(pattern)

    for pattern in warning_patterns:
        if re.search(pattern, content_lower):
            risk_score += 15
            detected_patterns.append(pattern)

    base64_strings = re.findall(r"[A-Za-z0-9+/=]{100,}", content)
    if base64_strings:
        risk_score += 25
        detected_patterns.append("Base64 Panjang")

    if risk_score > 100:
        risk_score = 100

    if risk_score >= 80:
        status = "BERBAHAYA"
    elif risk_score >= 40:
        status = "MENCURIGAKAN"
    else:
        status = "AMAN"

    return status, risk_score, detected_patterns

# =========================
# 🎨 EMBED BUILDER
# =========================
def create_embed(filename, size, user, status, risk_score, detected_files=None, patterns=None):
    if risk_score >= 80:
        color = discord.Color.red()
        icon = "🔴"
    elif risk_score >= 40:
        color = discord.Color.orange()
        icon = "🟡"
    else:
        color = discord.Color.green()
        icon = "🟢"

    embed = discord.Embed(
        title=f"🛡️ Hasil Scan: {filename}",
        color=color
    )

    embed.add_field(name="👤 Pengirim", value=user.mention, inline=True)
    embed.add_field(name="📦 Ukuran File", value=f"{size} KB", inline=True)

    embed.add_field(name="📊 Status", value=f"{icon} **{status}**", inline=False)
    embed.add_field(name="📈 Risiko", value=f"**{risk_score}%**", inline=False)

    if detected_files:
        file_list = "\n".join(f"• `{f}`" for f in detected_files)
        embed.add_field(name="📂 File Terdeteksi", value=file_list, inline=False)

    if patterns:
        pattern_list = "\n".join(f"• `{p}`" for p in patterns)
        embed.add_field(name="🔎 Pola Terdeteksi", value=pattern_list, inline=False)

    embed.set_footer(text="🔐 Tatang Bot")
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2910/2910763.png")

    return embed

# =========================
# 📂 ON_MESSAGE
# =========================
@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != SCAN_CHANNEL_ID:
        return

    for attachment in message.attachments:
        filename = attachment.filename.lower()
        size_kb = round(attachment.size / 1024, 2)

        if attachment.size > 3 * 1024 * 1024:
            await message.channel.send(f"⚠️ File `{attachment.filename}` terlalu besar (>3MB).")
            continue

        file_bytes = await attachment.read()
        final_status = "AMAN"
        final_risk = 0
        detected_patterns = []
        detected_files = []

        # Scan .lua / .luac
        if filename.endswith((".lua", ".luac")):
            try:
                if filename.endswith(".lua"):
                    content = file_bytes.decode("utf-8", errors="ignore")
                else:
                    content = file_bytes.decode("latin1", errors="ignore")
            except:
                content = file_bytes.decode("latin1", errors="ignore")

            status, risk_score, patterns = scan_content(content)
            final_status = status
            final_risk = risk_score
            detected_patterns = patterns
            detected_files = [attachment.filename]

        # Scan .zip
        elif filename.endswith(".zip"):
            try:
                zip_file = zipfile.ZipFile(io.BytesIO(file_bytes))
                for file in zip_file.namelist():
                    if file.endswith((".lua", ".luac")):
                        content_bytes = zip_file.read(file)
                        try:
                            if file.endswith(".lua"):
                                content = content_bytes.decode("utf-8", errors="ignore")
                            else:
                                content = content_bytes.decode("latin1", errors="ignore")
                        except:
                            content = content_bytes.decode("latin1", errors="ignore")

                        status, risk_score, patterns = scan_content(content)

                        if risk_score > final_risk:
                            final_status = status
                            final_risk = risk_score
                            detected_patterns = patterns
                            detected_files = [file]
            except Exception:
                final_status = "MENCURIGAKAN"
                final_risk = 50
                detected_patterns = ["Error membaca zip"]

        embed = create_embed(
            filename=attachment.filename,
            size=size_kb,
            user=message.author,
            status=final_status,
            risk_score=final_risk,
            detected_files=detected_files if detected_files else None,
            patterns=detected_patterns
        )

        await message.channel.send(embed=embed)

# =========================
# 📋 SLASH MENU
# =========================
@tree.command(name="menu", description="Tampilkan menu Tatang Bot")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ Tatang Bot — Pemindai Keamanan",
        description="🔐 Sistem keamanan otomatis untuk file SA-MP",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="📂 Cara Menggunakan",
        value=(
            "1️⃣ Upload file di channel scan khusus\n"
            "2️⃣ Bot akan otomatis memeriksa file\n"
            "3️⃣ Hasil scan akan muncul beberapa detik kemudian"
        ),
        inline=False
    )

    embed.add_field(
        name="📁 Format File Didukung",
        value=(
            "• `.lua`\n"
            "• `.luac`\n"
            "• `.zip` (isi lua/luac otomatis discan)"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Status Scan",
        value=(
            "🟢 **AMAN** → File bersih\n"
            "🟡 **MENCURIGAKAN** → Ditemukan kode mencurigakan\n"
            "🔴 **BERBAHAYA** → Terdeteksi webhook / Telegram"
        ),
        inline=False
    )

    embed.set_footer(text="🔐 Tatang Bot")
    await interaction.response.send_message(embed=embed)

# =========================
# 🔔 READY
# =========================
@client.event
async def on_ready():
    await tree.sync()
    print(f"Tatang Bot aktif sebagai {client.user}")

# =========================
# 🚀 RUN BOT
# =========================
client.run(TOKEN)
