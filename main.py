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
ADMIN_ROLE_ID = 1471265207945924619        
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

# ================= BOT =================
class TatangBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = TatangBot()

# ================= MENU =================
@bot.tree.command(name="menu", description="Dashboard Utama Tatang Bot")
async def menu(interaction: discord.Interaction):
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
        value=f"**Scanner:** Aktif ✅\n**Channel:** <#{SCAN_CHANNEL_ID}>\n**Format:** .lua, .zip, .7z",
        inline=False
    )

    embed.set_footer(text="Premium Management System • v2.1")
    await interaction.response.send_message(embed=embed)

# ================= ADD VIP =================
@bot.tree.command(name="addvip", description="Berikan akses VIP kepada user")
async def addvip(interaction: discord.Interaction, member: discord.Member):
    role_admin = interaction.guild.get_role(ADMIN_ROLE_ID)
    if role_admin not in interaction.user.roles:
        return await interaction.response.send_message("❌ **Akses Ditolak!**", ephemeral=True)

    vip_role = interaction.guild.get_role(VIP_ROLE_ID)
    if vip_role:
        await member.add_roles(vip_role)

    embed = discord.Embed(
        title="✨ VIP ACCESS GRANTED",
        description=f"{member.mention} Berhasil menjadi VIP! ✅",
        color=0x2ecc71
    )
    await interaction.response.send_message(embed=embed)

# ================= SCANNER =================
@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != SCAN_CHANNEL_ID:
        return

    if message.attachments:

        # CEK ROLE SAJA
        if VIP_ROLE_ID not in [role.id for role in message.author.roles]:
            embed = discord.Embed(title="🔒 PREMIUM ACCESS REQUIRED", color=0xf1c40f)
            embed.description = f"Halo {message.author.mention}, fitur **Deep Scanner** hanya untuk VIP.\n\n🛡️ **Minta Akses:** <#{REQ_VIP_CHANNEL_ID}>"
            return await message.reply(embed=embed)

        for attachment in message.attachments:
            ext = os.path.splitext(attachment.filename)[1].lower()
            if ext not in [".lua", ".txt", ".zip", ".7z"]:
                continue

            await message.add_reaction("⏳")
            file_data = await attachment.read()

            pola, links = [], []
            files_count = 0

            try:
                if ext in [".lua", ".txt"]:
                    content = file_data.decode(errors="ignore")
                    p, l = analyze_content(content)
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

            except Exception as e:
                await message.remove_reaction("⏳", bot.user)
                return await message.reply(f"❌ **Read Error:** `{e}`")

            pola = list(set(pola))
            links = list(set(links))

            if links:
                status, color = "🔴 🚨 BAHAYA TINGGI", 0xff0000
            elif len(pola) >= 2:
                status, color = "🟠 ⚠️ SANGAT MENCURIGAKAN", 0xe67e22
            elif len(pola) == 1:
                status, color = "🟡 🤔 MENCURIGAKAN", 0xf1c40f
            else:
                status, color = "✅ 🛡️ AMAN", 0x2ecc71

            embed = discord.Embed(title=status, color=color)
            embed.description = f"**File:** `{attachment.filename}`"

            await message.reply(embed=embed)
            await message.remove_reaction("⏳", bot.user)

bot.run(TOKEN)
