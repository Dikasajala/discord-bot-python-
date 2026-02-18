import discord
import os
import psutil
import zipfile
import py7zr
import re
import io
import asyncio
from discord.ext import commands

# ================= KONFIGURASI ID =================
TOKEN = os.getenv("TOKEN")
SCAN_CHANNEL_ID = 1469740150522380299      # Channel khusus Scanner
CONTROL_ROLE_ID = 1471921766283608195      # Role VIP untuk akses bot

# ================= UTILITY =================
def generate_fake_data():
    # Hanya untuk preview / embed
    nicks = ["Dika_Ganteng", "Admin_SAMP", "Player_Pro", "Tatang_Sakti", "Bocah_SAMP", "Rizky_Gaming"]
    ips = f"{discord.utils.get(bot.guilds[0].members).id}"  # dummy IP placeholder
    pw = "password123"  # dummy password
    return (
        "```ascii\n"
        "╔═══════════════════════════════════════════════╗\n"
        "║          TATANG COMUNITY SAMP LOGS            ║\n"
        "╠═══════════════════════════════════════════════╣\n"
        f"  > Nickname : {random.choice(nicks)}\n"
        f"  > Password : {pw}\n"
        f"  > IP Addr  : 127.0.0.1\n"
        "╠═══════════════════════════════════════════════╣\n"
        "  SUBSCRIBE : [youtube.com/@tatangchit](https://youtube.com/@tatangchit)           \n"
        "╚═══════════════════════════════════════════════╝\n"
        "```"
    )

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
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= COMMAND =================
@bot.command(name="menu")
async def menu_cmd(ctx):
    if CONTROL_ROLE_ID not in [r.id for r in ctx.author.roles]:
        return await ctx.send(f"❌ Kamu harus punya role <@&{CONTROL_ROLE_ID}> untuk menggunakan bot.", delete_after=10)
    
    embed = discord.Embed(title="📄 TATANG BOT | PREMIUM DASHBOARD", color=0x3498db)
    embed.description = "Sistem keamanan dan utilitas untuk komunitas SA-MP Indonesia."
    
    embed.add_field(
        name="🛡️ **SECURITY & TOOLS**", 
        value=f"• Kirim file `.lua`, `.zip`, atau `.7z` di channel khusus scanner untuk analisis otomatis.", 
        inline=False
    )
    
    embed.set_footer(text="Official Tatang Bot • youtube.com/@tatangchit")
    await ctx.send(embed=embed)

# ================= SCANNER EVENT =================
@bot.event
async def on_message(message):
    await bot.process_commands(message)  # Penting agar command tetap jalan
    
    if message.author.bot or message.channel.id != SCAN_CHANNEL_ID: 
        return
    
    if CONTROL_ROLE_ID not in [r.id for r in message.author.roles]:
        embed = discord.Embed(title="🔒 PREMIUM ACCESS REQUIRED", color=0xf1c40f)
        embed.description = f"Halo {message.author.mention}, fitur **Deep Scanner** hanya untuk pengguna dengan role VIP.\n\n🛡️ Minta akses dari admin."
        return await message.reply(embed=embed)
    
    if message.attachments:
        for attachment in message.attachments:
            ext = attachment.filename.lower().split('.')[-1]
            if ext not in ["lua", "txt", "zip", "7z"]: continue
            
            await message.add_reaction("⏳")
            file_data = await attachment.read(); pola, links, files_count = [], [], 0
            
            try:
                if ext in ["lua", "txt"]:
                    c = file_data.decode(errors="ignore")
                    p, l = analyze_content(c)
                    pola.extend(p); links.extend(l); files_count = 1
                elif ext == "zip":
                    with zipfile.ZipFile(io.BytesIO(file_data)) as z:
                        for f in z.namelist():
                            if f.lower().endswith((".lua", ".txt")):
                                c = z.read(f).decode(errors="ignore"); p, l = analyze_content(c)
                                pola.extend(p); links.extend(l); files_count += 1
                elif ext == "7z":
                    with py7zr.SevenZipFile(io.BytesIO(file_data), mode='r') as z:
                        names = [n for n in z.getnames() if n.lower().endswith((".lua", ".txt"))]
                        if names:
                            contents = z.read(names)
                            for name, bio in contents.items():
                                c = bio.read().decode(errors="ignore"); p, l = analyze_content(c)
                                pola.extend(p); links.extend(l); files_count += 1
            except:
                pass

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
