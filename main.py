import discord
import os
import psutil
import zipfile
import py7zr
import re
import io
from discord.ext import commands
from discord import app_commands

# ================= KONFIGURASI ID =================
TOKEN = os.getenv("TOKEN")
SCAN_CHANNEL_ID = 1469740150522380299
REQ_VIP_CHANNEL_ID = 1472535677634740398
VIP_ROLE_ID = 1471921766283608195

# ================= SCANNER ENGINE =================
def analyze_content(content):
    pola_terdeteksi = []
    found_links = []

    dw_regex = r"https://discord\.com/api/webhooks/\d+/\S+"
    tg_regex = r"https://api\.telegram\.org/bot\d+:\S+"

    dw_links = re.findall(dw_regex, content)
    tg_links = re.findall(tg_regex, content)

    if dw_links:
        found_links.extend(dw_links)
    if tg_links:
        found_links.extend(tg_links)

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
        if key in content:
            pola_terdeteksi.append(label)

    return pola_terdeteksi, found_links

# ================= BOT =================
class TatangBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = TatangBot()

# ================= ROLE CHECK =================
def is_vip(member):
    role = discord.utils.get(member.roles, id=VIP_ROLE_ID)
    return role is not None

# ================= MENU =================
@bot.tree.command(name="menu", description="Daftar lengkap perintah bot")
async def menu_cmd(it: discord.Interaction):

    embed = discord.Embed(title="📄 TATANG BOT | PREMIUM DASHBOARD", color=0x3498db)
    embed.description = "Sistem keamanan dan utilitas untuk komunitas SA-MP Indonesia."

    embed.add_field(
        name="👑 **ADMINISTRATION (Admin Only)**",
        value="• `/addvip` : Menambah user ke VIP Role",
        inline=False
    )

    embed.add_field(
        name="🛡️ **SECURITY & TOOLS**",
        value="• `/status` : Cek kesehatan mesin bot\n• `/help` : Panduan lengkap penggunaan scanner",
        inline=False
    )

    embed.add_field(
        name="⚡ **DEEP SCANNER**",
        value=f"Kirim file `.lua`, `.zip`, atau `.7z` di channel <#{SCAN_CHANNEL_ID}> untuk analisis otomatis.",
        inline=False
    )

    embed.set_footer(text="Official Tatang Bot • youtube.com/@tatangchit")
    await it.response.send_message(embed=embed)

# ================= ADD VIP =================
@bot.tree.command(name="addvip")
@app_commands.checks.has_permissions(administrator=True)
async def add_vip(it: discord.Interaction, member: discord.Member):

    role = it.guild.get_role(VIP_ROLE_ID)
    if role is None:
        return await it.response.send_message("❌ Role VIP tidak ditemukan.", ephemeral=True)

    await member.add_roles(role)

    embed = discord.Embed(title="✨ VIP ACCESS GRANTED", color=0x2ecc71)
    embed.description = f"{member.mention} Berhasil menjadi VIP! ✅"
    await it.response.send_message(embed=embed)

# ================= STATUS =================
@bot.tree.command(name="status")
async def status_cmd(it: discord.Interaction):
    embed = discord.Embed(title="🚀 SYSTEM STATUS", color=0x2ecc71)
    embed.add_field(name="RAM Usage", value=f"{psutil.virtual_memory().percent}%", inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.set_footer(text="Bot berjalan lancar di server.")
    await it.response.send_message(embed=embed)

# ================= HELP =================
@bot.tree.command(name="help")
async def help_cmd(it: discord.Interaction):

    embed = discord.Embed(title="❓ PANDUAN LENGKAP TATANG BOT", color=0x9b59b6)

    embed.add_field(
        name="🛡️ Cara Kerja Scanner",
        value=(
            "1. Masuk ke channel khusus scanner.\n"
            "2. Upload file (Lua, Zip, atau 7z).\n"
            "3. Bot akan memberikan reaksi ⏳ dan membongkar file.\n"
            "4. Jika ditemukan link Webhook atau pola stealer, bot akan menandai file tersebut sebagai **BAHAYA**."
        ),
        inline=False
    )

    embed.set_footer(text="Bantu kami membasmi keylogger! youtube.com/@tatangchit")
    await it.response.send_message(embed=embed)

# ================= SCANNER EVENT =================
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.id != SCAN_CHANNEL_ID:
        return

    if not is_vip(message.author):
        embed = discord.Embed(title="🔒 PREMIUM ACCESS REQUIRED", color=0xf1c40f)
        embed.description = f"Halo {message.author.mention}, fitur **Deep Scanner** hanya untuk VIP.\n\n🛡️ **Minta Akses:** <#{REQ_VIP_CHANNEL_ID}>"
        return await message.reply(embed=embed)

    if message.attachments:

        for attachment in message.attachments:

            ext = os.path.splitext(attachment.filename)[1].lower()
            if ext not in [".lua", ".txt", ".zip", ".7z"]:
                continue

            await message.add_reaction("⏳")

            file_data = await attachment.read()
            pola, links, files_count = [], [], 0

            try:
                if ext in [".lua", ".txt"]:
                    c = file_data.decode(errors="ignore")
                    p, l = analyze_content(c)
                    pola.extend(p)
                    links.extend(l)
                    files_count = 1

                elif ext == ".zip":
                    with zipfile.ZipFile(io.BytesIO(file_data)) as z:
                        for f in z.namelist():
                            if f.lower().endswith((".lua", ".txt")):
                                c = z.read(f).decode(errors="ignore")
                                p, l = analyze_content(c)
                                pola.extend(p)
                                links.extend(l)
                                files_count += 1

                elif ext == ".7z":
                    with py7zr.SevenZipFile(io.BytesIO(file_data), mode='r') as z:
                        names = [n for n in z.getnames() if n.lower().endswith((".lua", ".txt"))]
                        if names:
                            contents = z.read(names)
                            for name, bio in contents.items():
                                c = bio.read().decode(errors="ignore")
                                p, l = analyze_content(c)
                                pola.extend(p)
                                links.extend(l)
                                files_count += 1

            except:
                pass

            pola = list(set(pola))
            links = list(set(links))

            if links:
                status = "🔴 🚨 BAHAYA TINGGI"
                color = 0xff0000
                conf = "100%"
                msg_ana = f"Ditemukan {len(links)} link webhook stealer aktif!"

            elif pola:
                status = "🟠 ⚠️ SANGAT MENCURIGAKAN"
                color = 0xe67e22
                conf = "75%"
                msg_ana = f"Ditemukan {len(pola)} pola instruksi berbahaya."

            else:
                status = "✅ 🛡️ AMAN"
                color = 0x2ecc71
                conf = "85%"
                msg_ana = "Tidak ditemukan indikasi keylogger secara otomatis."

            embed = discord.Embed(title=status, color=color)
            embed.description = (
                f"**File:** `{attachment.filename}`\n"
                f"**Analisis:** {msg_ana}\n\n"
                f"🎯 **Confidence**\n{conf}\n\n"
                f"📊 **Info**\nSize: {len(file_data):,} bytes"
            )

            if pola:
                embed.add_field(
                    name="📝 Pola Terdeteksi",
                    value="\n".join([f"• {p}" for p in pola]),
                    inline=False
                )

            if links:
                embed.add_field(
                    name="🌐 Webhook Found",
                    value="\n".join([f"🔗 {l}" for l in links]),
                    inline=False
                )

            embed.set_footer(text=f"Analisis Selesai: {files_count} file | youtube.com/@tatangchit")

            await message.reply(embed=embed)
            await message.remove_reaction("⏳", bot.user)

bot.run(TOKEN)
