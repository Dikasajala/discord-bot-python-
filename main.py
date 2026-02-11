import discord
import zipfile
import io
import re
import os

TOKEN = os.getenv("DISCORD_TOKEN")
SCAN_CHANNEL_ID = 1469740150522380299

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

# =========================
# 🔎 SCANNER ENGINE + RISK %
# =========================
def scan_content(content):
    content_lower = content.lower()

    dangerous_patterns = [
        r"discord\.com/api/webhooks",
        r"discordapp\.com/api/webhooks",
        r"api\.telegram\.org",
        r"t\.me/",
        r"sendmessage",
        r"requests\.post",
        r"http\.request",
        r"socket\.connect"
    ]

    warning_patterns = [
        r"loadstring",
        r"base64",
        r"require\s*\(",
        r"setclipboard"
    ]

    risk_score = 0
    detected_patterns = []

    # 🔴 Dangerous
    for pattern in dangerous_patterns:
        if re.search(pattern, content_lower):
            risk_score += 40
            detected_patterns.append(pattern)

    # 🟡 Mencurigakan
    for pattern in warning_patterns:
        if re.search(pattern, content_lower):
            risk_score += 15
            detected_patterns.append(pattern)

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
def create_embed(filename, size, user, status, risk_score, detected_file=None, patterns=None):

    # Warna berdasarkan persen
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
        title="🛡️ Tatang Bot — SA-MP Security Scanner",
        color=color
    )

    embed.add_field(
        name="📦 Informasi File",
        value=f"• **Nama:** `{filename}`\n• **Ukuran:** `{size} KB`",
        inline=False
    )

    embed.add_field(
        name="👤 Pengirim",
        value=user.mention,
        inline=False
    )

    embed.add_field(
        name="📊 Status Scan",
        value=f"{icon} **{status}**",
        inline=False
    )

    embed.add_field(
        name="📈 Tingkat Risiko",
        value=f"**{risk_score}%**",
        inline=False
    )

    if detected_file:
        embed.add_field(
            name="📂 File Terdeteksi",
            value=f"`{detected_file}`",
            inline=False
        )

    if patterns:
        embed.add_field(
            name="🔎 Pola Terdeteksi",
            value=f"`{', '.join(patterns)}`",
            inline=False
        )

    embed.set_footer(text="🔐 Tatang Security System")

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

        if filename.endswith((".lua", ".luac", ".zip")):
            file_bytes = await attachment.read()
            size_kb = round(len(file_bytes) / 1024, 2)

            final_status = "AMAN"
            final_risk = 0
            detected_patterns = []
            detected_file = None

            # 🔹 LUA / LUAC
            if filename.endswith((".lua", ".luac")):
                content = file_bytes.decode("utf-8", errors="ignore")
                status, risk, patterns = scan_content(content)
                final_status = status
                final_risk = risk
                detected_patterns = patterns
                detected_file = attachment.filename

            # 🔹 ZIP
            elif filename.endswith(".zip"):
                try:
                    zip_file = zipfile.ZipFile(io.BytesIO(file_bytes))
                    for file in zip_file.namelist():
                        if file.endswith((".lua", ".luac")):
                            content = zip_file.read(file).decode("utf-8", errors="ignore")
                            status, risk, patterns = scan_content(content)

                            if risk > final_risk:
                                final_status = status
                                final_risk = risk
                                detected_patterns = patterns
                                detected_file = file
                except:
                    final_status = "MENCURIGAKAN"
                    final_risk = 50

            embed = create_embed(
                attachment.filename,
                size_kb,
                message.author,
                final_status,
                final_risk,
                detected_file,
                detected_patterns
            )

            await message.channel.send(embed=embed)


# =========================
# 📋 SLASH MENU
# =========================
@tree.command(name="menu", description="Tampilkan menu Tatang Scanner")
async def menu(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🛡️ Tatang Bot — Security Scanner",
        description="🔐 Sistem keamanan otomatis untuk file SA-MP",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="📂 Cara Menggunakan",
        value=(
            "1️⃣ Upload file di channel scan\n"
            "2️⃣ Bot akan otomatis memeriksa\n"
            "3️⃣ Hasil scan muncul dalam beberapa detik"
        ),
        inline=False
    )

    embed.add_field(
        name="📁 Format Didukung",
        value=(
            "• `.lua`\n"
            "• `.luac`\n"
            "• `.zip` (isi lua otomatis discan)"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Sistem Status",
        value=(
            "🟢 **AMAN** → File bersih\n"
            "🟡 **MENCURIGAKAN** → Ditemukan kode yang perlu diperiksa\n"
            "🔴 **BERBAHAYA** → Terdeteksi webhook / Telegram"
        ),
        inline=False
    )

    embed.set_footer(text="🔐 Tatang Security System")

    await interaction.response.send_message(embed=embed)


@client.event
async def on_ready():
    await tree.sync()
    print(f"Bot aktif sebagai {client.user}")


client.run(TOKEN)
