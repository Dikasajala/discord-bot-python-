import discord
import io
import zipfile
import os
import re
import time
import random
import base64
from discord.ui import View, Button

TOKEN = os.getenv("DISCORD_TOKEN")
SCAN_CHANNEL_ID = 1469740150522380299  # Channel scan keylogger
OPF_CHANNEL_ID = 1470767786652340390   # Channel OPF
MAX_FILE_SIZE = 8 * 1024 * 1024       # 8 MB
START_TIME = time.time()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

# =========================
# SCANNER ENGINE (Keylogger canggih)
# =========================
def scan_content(content):
    content_lower = content.lower()
    risk_score = 0
    detected_patterns = []

    # 🔴 BERBAHAYA → keylogger / webhook / telegram
    dangerous_patterns = [
        r"discord(app)?\.com/api/webhooks",
        r"api\.telegram\.org",
        r"t\.me/",
        r"keylogger",
        r"onclientkey",
        r"keyboard",
        r"setclipboard",
        r"fetchremote",
        r"performhttprequest"
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, content_lower):
            risk_score += 50
            detected_patterns.append(pattern)

    # 🟡 MENCURIGAKAN → loadstring / obf
    warning_patterns = [
        r"loadstring\s*\(",
        r"assert\s*\(\s*load",
        r"[A-Za-z0-9+/=]{100,}"
    ]
    for pattern in warning_patterns:
        if re.search(pattern, content_lower):
            risk_score += 25
            detected_patterns.append(pattern)

    # variabel/fungsi pendek → tambahan kecil
    short_var_names = re.findall(r"\b[a-z]{1,2}\b", content_lower)
    if len(short_var_names) > 20:
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

    return status, risk_score, detected_patterns

# =========================
# EMBED BUILDER
# =========================
def create_embed(filename, size, user, status, risk_score, detected_files=None, patterns=None):
    if risk_score >= 80:
        color = discord.Color.red()
        icon = "🔴"
    elif risk_score >= 30:
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
# RINGKASAN MULTI FILE
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
# OPF BUTTON VIEW
# =========================
class OpfLevelView(View):
    def __init__(self, file_bytes, filename, user):
        super().__init__(timeout=None)
        self.file_bytes = file_bytes
        self.filename = filename
        self.user = user
        self.add_item(Button(label="Low", style=discord.ButtonStyle.green, custom_id="opf_low"))
        self.add_item(Button(label="Medium", style=discord.ButtonStyle.blurple, custom_id="opf_medium"))
        self.add_item(Button(label="Hard", style=discord.ButtonStyle.red, custom_id="opf_hard"))

# =========================
# OBFSUCATE LUA
# =========================
def obfuscate_lua(content: str, level: str) -> bytes:
    if level == "Low":
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        obf_code = f"loadstring(game:HttpGet('data:text/plain;base64,{encoded}',true))()"
    elif level == "Medium":
        vars = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", content))
        for v in vars:
            if len(v) > 1:
                content = re.sub(rf"\b{v}\b", f"{v}_{random.randint(1000,9999)}", content)
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        obf_code = f"loadstring(game:HttpGet('data:text/plain;base64,{encoded}',true))()"
    elif level == "Hard":
        content_scramble = ''.join([chr(ord(c)^0x55) for c in content])
        encoded1 = base64.b64encode(content_scramble.encode("utf-8")).decode("utf-8")
        encoded2 = base64.b64encode(encoded1.encode("utf-8")).decode("utf-8")
        obf_code = f"loadstring(game:HttpGet('data:text/plain;base64,{encoded2}',true))()"
    return obf_code.encode("utf-8")

# =========================
# INTERACTION BUTTON
# =========================
@client.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    level_map = {"opf_low":"Low", "opf_medium":"Medium", "opf_hard":"Hard"}
    if interaction.data["custom_id"] not in level_map:
        return
    level = level_map[interaction.data["custom_id"]]
    view: OpfLevelView = interaction.message.components[0].view
    obf_bytes = obfuscate_lua(view.file_bytes.decode("utf-8", errors="ignore"), level)
    obf_filename = f"opf_{view.filename}"
    await interaction.response.send_message(
        content=f"✅ {interaction.user.mention}, file sudah diobfuscate dengan tingkat **{level}**",
        file=discord.File(io.BytesIO(obf_bytes), filename=obf_filename)
    )

# =========================
# ON MESSAGE (Scan + OPF)
# =========================
@client.event
async def on_message(message):
    if message.author.bot:
        return

    files_results = []

    # -------- CHANNEL SCAN KEYLOGGER --------
    if message.channel.id == SCAN_CHANNEL_ID:
        for attachment in message.attachments:
            filename = attachment.filename.lower()
            size_kb = round(attachment.size / 1024, 2)
            if attachment.size > MAX_FILE_SIZE:
                await message.channel.send(f"⚠️ File `{attachment.filename}` terlalu besar (>8MB).")
                continue
            file_bytes = await attachment.read()
            final_status, final_risk, detected_patterns = "AMAN", 0, []
            detected_files = []

            if filename.endswith((".lua", ".luac")):
                try:
                    if filename.endswith(".lua"):
                        content = file_bytes.decode("utf-8", errors="ignore")
                    else:
                        content = file_bytes.decode("latin1", errors="ignore")
                except:
                    content = file_bytes.decode("latin1", errors="ignore")
                final_status, final_risk, detected_patterns = scan_content(content)
                detected_files = [attachment.filename]
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
                except:
                    final_status = "MENCURIGAKAN"
                    final_risk = 50
                    detected_patterns = ["Error membaca zip"]

            embed = create_embed(
                filename=attachment.filename,
                size=size_kb,
                user=message.author,
                status=final_status,
                risk_score=final_risk,
                detected_files=detected_files,
                patterns=detected_patterns
            )
            await message.channel.send(embed=embed)
            files_results.append({
                "filename": attachment.filename,
                "status": final_status,
                "patterns": detected_patterns
            })
        if files_results:
            summary_text = summary_multiple(files_results)
            await message.channel.send(f"📄 **Ringkasan Scan**\n```\n{summary_text}\n```")
        return

    # -------- CHANNEL OPF --------
    if message.channel.id == OPF_CHANNEL_ID:
        for attachment in message.attachments:
            filename = attachment.filename.lower()
            size_kb = round(attachment.size / 1024, 2)
            if attachment.size > MAX_FILE_SIZE:
                await message.channel.send(f"⚠️ File `{attachment.filename}` terlalu besar (>8MB).")
                continue
            file_bytes = await attachment.read()
            embed = discord.Embed(
                title=f"🛡️ File OPF: {filename}",
                description="Pilih tingkat OPF (Low / Medium / Hard):",
                color=discord.Color.orange()
            )
            embed.add_field(name="👤 Pengirim", value=message.author.mention)
            embed.add_field(name="📦 Ukuran File", value=f"{size_kb} KB")
            embed.set_footer(text="🔐 OPF Bot")
            await message.channel.send(embed=embed, view=OpfLevelView(file_bytes, filename, message.author))
            await message.delete()
        return

# =========================
# SLASH COMMANDS /menu & /status
# =========================
def format_uptime():
    delta = int(time.time() - START_TIME)
    hours, remainder = divmod(delta, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}j {minutes}m {seconds}s"

@tree.command(name="menu", description="Tampilkan menu Tatang Bot")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ Tatang Bot — Pemindai & OPF",
        description="🔐 Sistem keamanan dan obfuscation otomatis untuk file SA-MP",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="📂 Cara Menggunakan",
        value=(
            "1️⃣ Upload file di channel scan → Bot otomatis scan keylogger\n"
            "2️⃣ Upload file di channel OPF → Bot otomatis obfuscate file\n"
            "3️⃣ Pilih tingkat OPF: Low / Medium / Hard"
        ),
        inline=False
    )
    embed.add_field(
        name="📁 Format File Didukung",
        value="• `.lua`\n• `.luac`\n• `.zip` (isi lua/luac otomatis discan/obfuscate)",
        inline=False
    )
    embed.add_field(
        name="📊 Status Scan",
        value="🟢 AMAN → File bersih\n🟡 MENCURIGAKAN → Ada kode mencurigakan\n🔴 BERBAHAYA → Terdeteksi keylogger / webhook / Telegram",
        inline=False
    )
    embed.add_field(
        name="📝 Channel Khusus",
        value=f"• Scan Keylogger → <#{SCAN_CHANNEL_ID}>\n• OPF Obfuscator → <#{OPF_CHANNEL_ID}>",
        inline=False
    )
    embed.add_field(name="💾 Versi Bot", value="v1.0.0", inline=True)
    embed.set_footer(text="🔐 Tatang Bot")
    await interaction.response.send_message(embed=embed)

@tree.command(name="status", description="Cek status Tatang Bot")
async def status(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🟢 Status Tatang Bot",
        color=discord.Color.green()
    )
    embed.add_field(name="🤖 Bot Aktif", value="✅ Online", inline=True)
    embed.add_field(name="🕒 Waktu Aktif", value=format_uptime(), inline=True)
    embed.add_field(name="💾 Versi Bot", value="v1.0.0", inline=True)
    embed.set_footer(text="🔐 Tatang Bot")
    await interaction.response.send_message(embed=embed)

# =========================
# READY
# =========================
@client.event
async def on_ready():
    await tree.sync()
    print(f"Tatang Bot aktif sebagai {client.user}")

# =========================
# RUN BOT
# =========================
client.run(TOKEN)
