import discord
import zipfile
import io
import re
import os

TOKEN = os.getenv("DISCORD_TOKEN")
SCAN_CHANNEL_ID = 1469740150522380299  # channel khusus scan

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

# =========================
# 🔎 SCANNER ENGINE + RISK %
# =========================
def scan_content(content):
    content_lower = content.lower()
    risk_score = 0
    detected_patterns = []

    # 🔴 DETEKSI BERAT (keylogger / exfiltration)
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

    # 🟡 DETEKSI OBFS / MENCURIGAKAN
    warning_patterns = [
        r"loadstring",
        r"assert\s*\(\s*load",
        r"base64",
        r"string\.char",
        r"\.\.",            # string concat obfuscation
        r"while\s+true\s+do"
    ]

    # 🔎 Scan dangerous
    for pattern in dangerous_patterns:
        if re.search(pattern, content_lower):
            risk_score += 35
            detected_patterns.append(pattern)

    # 🔎 Scan warning
    for pattern in warning_patterns:
        if re.search(pattern, content_lower):
            risk_score += 15
            detected_patterns.append(pattern)

    # 📏 Deteksi Base64 panjang (sering sembunyikan webhook)
    base64_strings = re.findall(r"[A-Za-z0-9+/=]{100,}", content)
    if base64_strings:
        risk_score += 25
        detected_patterns.append("Base64 Panjang")

    # Batasi max
    if risk_score > 100:
        risk_score = 100

    # Tentukan status
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

    # Warna otomatis
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

    # Info ringkas
    embed.add_field(
        name="👤 Pengirim",
        value=user.mention,
        inline=True
    )

    embed.add_field(
        name="📦 Ukuran File",
        value=f"{size} KB",
        inline=True
    )

    # Status
    embed.add_field(
        name="📊 Status",
        value=f"{icon} **{status}**",
        inline=False
    )

    # Risiko di bawah status
    embed.add_field(
        name="📈 Risiko",
        value=f"**{risk_score}%**",
        inline=False
    )

    # File terdeteksi
    if detected_files:
        file_list = "\n".join(f"• `{f}`" for f in detected_files)
        embed.add_field(
            name="📂 File Terdeteksi",
            value=file_list,
            inline=False
        )

    # Pola terdeteksi
    if patterns:
        pattern_list = "\n".join(f"• `{p}`" for p in patterns)
        embed.add_field(
            name="🔎 Pola Terdeteksi",
            value=pattern_list,
            inline=False
        )

    embed.set_footer(text="🔐 Tatang Bot")
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2910/2910763.png")  # opsional

    return embed

# =========================
# 📂 AUTO SCAN FILE
# =========================
@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id != SCAN_CHANNEL_ID:
        return

    for attachment in message.attachments:
        filename = attachment.filename.lower()

        # Hanya scan file didukung
        if filename.endswith((".lua", ".luac", ".zip")):
            file_bytes = await attachment.read()
            size_kb = round(len(file_bytes) / 1024, 2)

            final_status = "AMAN"
            final_risk = 0
            detected_patterns = []
            detected_file = None

            # 🔹 Scan LUA / LUAC langsung
            if filename.endswith((".lua", ".luac")):
                content = file_bytes.decode("utf-8", errors="ignore")
                status, risk, patterns = scan_content(content)
                final_status = status
                final_risk = risk
                detected_patterns = patterns
                detected_file = attachment.filename

            # 🔹 Scan ZIP / Library
            elif filename.endswith(".zip"):
                try:
                    zip_file = zipfile.ZipFile(io.BytesIO(file_bytes))
                    for file in zip_file.namelist():
                        if file.endswith((".lua", ".luac")):
                            content = zip_file.read(file).decode("utf-8", errors="ignore")
                            status, risk, patterns = scan_content(content)

                            # Update final risk jika lebih tinggi
                            if risk > final_risk:
                                final_status = status
                                final_risk = risk
                                detected_patterns = patterns
                                detected_file = file
                except:
                    final_status = "MENCURIGAKAN"
                    final_risk = 50

            # Kirim embed hasil scan
            embed = create_embed(
                attachment.filename,
                size_kb,
                message.author,
                final_status,
                final_risk,
                detected_file=[detected_file] if detected_file else None,
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
            "• `.zip` (isi lua/luaC otomatis discan)"
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
# 🔔 READY EVENT
# =========================
@client.event
async def on_ready():
    await tree.sync()
    print(f"Bot aktif sebagai {client.user}")

# =========================
# 🚀 RUN BOT
# =========================
client.run(TOKEN)
