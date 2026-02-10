import discord
from discord import app_commands
from discord.ext import commands
import base64, random, string, tempfile, os, time, ast
import yt_dlp
import qrcode
import requests

TOKEN = "ISI_TOKEN_BOT_KAMU"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

start_time = time.time()

# ======================
# UTIL
# ======================
def rand_var():
    return ''.join(random.choices(string.ascii_letters, k=8))

def obfuscate_code(text, level):
    if level == "low":
        encoded = base64.b64encode(text.encode()).decode()
        return f'import base64\nexec(base64.b64decode("{encoded}").decode())'

    elif level == "medium":
        encoded = base64.b64encode(text.encode()).decode()[::-1]
        v = rand_var()
        return f'import base64\n{v}="{encoded}"\nexec(base64.b64decode({v}[::-1]).decode())'

    elif level == "hard":
        encoded = base64.b64encode(text.encode()).decode()
        parts = [encoded[i:i+10] for i in range(0, len(encoded), 10)]
        var = rand_var()
        joined = " + ".join([f'"{p}"' for p in parts])
        return f'import base64\n{var} = {joined}\nexec(base64.b64decode({var}).decode())'

# ======================
# SAFE CALC
# ======================
def safe_calc(expr):
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp,
                                 ast.Num, ast.Add, ast.Sub, ast.Mult,
                                 ast.Div, ast.Pow, ast.Mod)):
            raise ValueError("Invalid expression")
    return eval(compile(tree, "<calc>", "eval"))

# ======================
# OBF VIEW
# ======================
class ObfView(discord.ui.View):
    def __init__(self, file):
        super().__init__(timeout=60)
        self.file = file

    async def process(self, interaction, level):
        data = await self.file.read()
        text = data.decode("utf-8", errors="ignore")
        result = obfuscate_code(text, level)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp:
            tmp.write(result.encode())
            filename = tmp.name

        await interaction.response.send_message(
            content=f"✅ **Obfuscation {level.upper()} berhasil!**",
            file=discord.File(filename, f"obf_{level}.py"),
            ephemeral=True
        )
        os.unlink(filename)

    @discord.ui.button(label="🟢 LOW", style=discord.ButtonStyle.success)
    async def low(self, interaction: discord.Interaction, _):
        await self.process(interaction, "low")

    @discord.ui.button(label="🟡 MEDIUM", style=discord.ButtonStyle.primary)
    async def medium(self, interaction: discord.Interaction, _):
        await self.process(interaction, "medium")

    @discord.ui.button(label="🔴 HARD", style=discord.ButtonStyle.danger)
    async def hard(self, interaction: discord.Interaction, _):
        await self.process(interaction, "hard")

# ======================
# MENU
# ======================
@bot.tree.command(name="menu")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📌 BOT MENU",
        description="🤖 Bot AI + Tools + Downloader + Obfuscation",
        color=0x00ffcc
    )
    embed.add_field(name="🛡️ Security", value="🔐 `/obf`", inline=False)
    embed.add_field(name="📥 Download", value="🎥 `/youtube`", inline=False)
    embed.add_field(name="🧰 Tools", value="/ping /uptime /calc /qr /poll", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ======================
# COMMANDS
# ======================
@bot.tree.command(name="obf")
@app_commands.describe(file="Upload script")
async def obf(interaction: discord.Interaction, file: discord.Attachment):
    embed = discord.Embed(
        title="🛡️ OBFUSCATION",
        description="Pilih level obfuscation",
        color=0x2ecc71
    )
    await interaction.response.send_message(embed=embed, view=ObfView(file), ephemeral=True)

@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="uptime")
async def uptime(interaction: discord.Interaction):
    seconds = int(time.time() - start_time)
    await interaction.response.send_message(f"⏰ Uptime: {seconds}s")

@bot.tree.command(name="calc")
async def calc(interaction: discord.Interaction, expr: str):
    try:
        result = safe_calc(expr)
        await interaction.response.send_message(f"🧮 Hasil: {result}")
    except:
        await interaction.response.send_message("❌ Ekspresi tidak valid")

@bot.tree.command(name="qr")
async def qr_cmd(interaction: discord.Interaction, text: str):
    filename = f"qr_{interaction.user.id}.png"
    img = qrcode.make(text)
    img.save(filename)
    await interaction.response.send_message(file=discord.File(filename))
    os.unlink(filename)

@bot.tree.command(name="poll")
async def poll(interaction: discord.Interaction, question: str):
    await interaction.response.send_message(f"📊 **Poll:** {question}")
    msg = await interaction.original_response()
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

# ======================
# YOUTUBE
# ======================
@bot.tree.command(name="youtube")
async def youtube(interaction: discord.Interaction, url: str):
    await interaction.response.defer()

    ydl_opts = {
        "format": "mp4",
        "outtmpl": "%(title)s.%(ext)s",
        "quiet": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url)
        filename = ydl.prepare_filename(info)

    if os.path.getsize(filename) > 25 * 1024 * 1024:
        os.unlink(filename)
        return await interaction.followup.send("❌ File terlalu besar untuk Discord")

    await interaction.followup.send(file=discord.File(filename))
    os.unlink(filename)

# ======================
# ERROR HANDLER
# ======================
@bot.tree.error
async def on_error(interaction, error):
    if interaction.response.is_done():
        await interaction.followup.send("❌ Terjadi error", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Terjadi error", ephemeral=True)

# ======================
# READY
# ======================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot Ready!")

bot.run(TOKEN)
