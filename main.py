import discord
import zipfile
import io
import re
import os
import time

TOKEN = os.getenv("DISCORD_TOKEN")
SCAN_CHANNEL_ID = 1469740150522380299  # Channel khusus scan keylogger
MAX_FILE_SIZE = 8 * 1024 * 1024       # 8 MB
START_TIME = time.time()               # Waktu bot mulai

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

    # 🔴 BERBAHAYA → keylogger / webhook / Telegram
    dangerous_patterns = [
        r"discord(app)?\.com/api/webhooks",
        r"api\.telegram\.org",
        r"t\.me/",
        r"onclientkey",
        r"keyboard",
        r"keylogger"
    ]

    # 🟡 MENCURIGAKAN → obfuscation ringan, tapi bukan illegal tools
    warning_patterns = [
        r"loadstring\s*\(",
        r"assert\s*\(\s*load",
        r"[A-Za-z0-9+/=]{100,}"  # Base64 panjang
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, content_lower):
            risk_score += 50
            detected_patterns.append(pattern)

    for pattern in warning_patterns:
        if re.search(pattern, content_lower):
            risk_score += 25
            detected_patterns.append(pattern)

    # Variabel/fungsi acak pendek → indikasi obf ringan
    short_vars = re.findall(r"\b[a-z]{1,2}\b", content_lower)
    if len(short_vars) > 20:
        risk_score += 10
        detected_patterns.append("Variabel pendek/acak banyak → obf")

    if risk_score > 100:
        risk_score = 100

    if risk_score >= 80:
        status = "BERBAHAYA"
    elif risk_score >= 30:
        status = "MENCURIGAKAN"
    else:
        status = "AMAN"

    # Jika aman dan tidak ada pola → tampilkan teks khusus
    if status == "AMAN" and not detected_patterns:
        detected_patterns = ["Tidak terdeteksi pola mencurigakan"]

    return status, risk_score, detected_patterns

# =========================
# 🎨 EMBED BUILDER
# =========================
def create_embed(filename, size, user, status, risk_score, patterns=None):
    if status == "BERBAHAYA":
        color = discord.Color.red()
        icon = "🔴"
    elif status == "MENCURIGAKAN":
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

    if patterns:
        pattern_list = "\n".join(f"• {p}" for p in patterns)
        embed.add_field(name="🔎 Pola Terdeteksi", value=pattern_list, inline=False)

    embed.set_footer(text="🔐 Tatang Bot")
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2910/2910763.png")
    return embed

# =========================
# 📝 RINGKASAN MULTI FILE
# =========================
def summary_multiple(files_results):
    grouped = {"AMAN": [], "MENCURIGAKAN": [], "BERBAHAYA": []}

    for f in files_results:
        grouped[f["status"]].append(f)

    lines = []

    for status in ["AMAN", "MENCURIGAKAN", "BERBAHAYA"]:
        if grouped[status]:
            icon = "🟢" if status=="AMAN" else "🟡" if status=="MENCURIGAKAN" else "🔴"
            lines.append(f"{icon} {status}")
            for idx, file in enumerate(grouped[status], 1):
                lines.append(f"{idx}. {file['filename']}")
                if file.get("patterns"):
                    for p in file["patterns"]:
                        lines.append(f"   └ {p}")
            lines.append("")
    return "\n".join(lines)

# =========================
# 📂 ON_MESSAGE
# =========================
@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != SCAN_CHANNEL_ID:
        return

    files_results = []

    for attachment in message.attachments:
        filename = attachment.filename.lower()
        size_kb = round(attachment.size / 1024, 2)

        # Batasi file ≤8MB
        if attachment.size > MAX_FILE_SIZE:
            await message.channel.send(f"⚠️ File `{attachment.filename}` terlalu besar (>8MB).")
            continue

        file_bytes = await attachment.read()
        final_status = "AMAN"
        final_risk = 0
        detected_patterns = []

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
                        # Ambil risiko paling tinggi
                        if risk_score > final_risk:
                            final_status = status
                            final_risk = risk_score
                            detected_patterns = patterns
            except Exception:
                final_status = "MENCURIGAKAN"
                final_risk = 50
                detected_patterns = ["Error membaca zip"]

        # Embed per file
        embed = create_embed(
            filename=attachment.filename,
            size=size_kb,
            user=message.author,
            status=final_status,
            risk_score=final_risk,
            patterns=detected_patterns
        )
        await message.channel.send(embed=embed)

        files_results.append({
            "filename": attachment.filename,
            "status": final_status,
            "patterns": detected_patterns
        })

    # Kirim summary multi file
    if files_results:
        summary_text = summary_multiple(files_results)
        await message.channel.send(f"📄 **Ringkasan Scan**\n```\n{summary_text}\n```")

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
            "3️⃣ Hasil scan dan ringkasan akan muncul beberapa detik kemudian"
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
            "🔴 **BERBAHAYA** → Terdeteksi keylogger / webhook / Telegram"
        ),
        inline=False
    )
    embed.set_footer(text="🔐 Tatang Bot")
    await interaction.response.send_message(embed=embed)

# =========================
# ⚡ STATUS BOT
# =========================
def format_uptime():
    delta = int(time.time() - START_TIME)
    hours, remainder = divmod(delta, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}j {minutes}m {seconds}s"

@tree.command(name="status", description="Cek status Tatang Bot")
async def status(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🟢 Status Tatang Bot",
        color=discord.Color.green()
    )
    embed.add_field(name="🤖 Bot Aktif", value="✅ Online", inline=True)
    embed.add_field(name="🕒 Waktu Aktif", value=format_uptime(), inline=True)
    embed.add_field(name="📝 Informasi", value="Tatang Bot siap memindai file SA-MP dengan aman", inline=False)
    embed.add_field(name="💾 Versi Bot", value="v1.0.0", inline=True)
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
