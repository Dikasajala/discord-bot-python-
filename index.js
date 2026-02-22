require('dotenv').config();
const { Client, GatewayIntentBits, Events } = require('discord.js');
const axios = require('axios');
const path = require('path');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ]
});

/* =========================
   CONFIG
========================= */
const CHANNEL_SCAN = "1469740150522380299";
const CHANNEL_AI = "1475164217115021475";
const MAX_SIZE = 5 * 1024 * 1024;
const allowedExt = ['.lua', '.luac', '.zip', '.rar', '.7z', '.txt'];
const startTime = Date.now();

/* =========================
   READY
========================= */
client.once(Events.ClientReady, (c) => {
  console.log(`✅ Bot online sebagai ${c.user.tag}`);
});

/* =========================
   MESSAGE HANDLER
========================= */
client.on(Events.MessageCreate, async (message) => {
  if (message.author.bot) return;

/* =========================
   !PING
========================= */
  if (message.content === "!ping") {
    const uptime = Math.floor((Date.now() - startTime) / 1000);
    const hours = Math.floor(uptime / 3600);
    const minutes = Math.floor((uptime % 3600) / 60);

    return message.reply(`
━━━━━━━━━━━━━━━━━━
🏓 PONG!
━━━━━━━━━━━━━━━━━━

🤖 Status          : Online
⚡ Latensi         : ${client.ws.ping} ms
🕒 Uptime          : ${hours} jam ${minutes} menit
📡 Kondisi Server  : Stabil

━━━━━━━━━━━━━━━━━━
🟢 Sistem Aktif & Berjalan Normal
━━━━━━━━━━━━━━━━━━
`);
  }

/* =========================
   !MENU
========================= */
  if (message.content === "!menu") {
    return message.reply(`
━━━━━━━━━━━━━━━━━━━━━━━━
🤖 TATANG BOT — MENU
━━━━━━━━━━━━━━━━━━━━━━━━

🛡️ Scanner aktif di:
<#${CHANNEL_SCAN}>

🤖 AI aktif di:
<#${CHANNEL_AI}>

📂 Format Didukung:
.lua .luac .zip .rar .7z .txt
📦 Maksimal ukuran 5MB

📊 Status Scan:
🟢 Aman
🟡 Mencurigakan
🔴 Bahaya

━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Deteksi manual by Tatang Bot
━━━━━━━━━━━━━━━━━━━━━━━━
`);
  }

/* =========================
   !AI (ONLY AI CHANNEL)
========================= */
  if (message.content.toLowerCase().startsWith("!ai")) {

    if (message.channel.id !== CHANNEL_AI) {
      return message.reply(`⚠️ Gunakan perintah ini di <#${CHANNEL_AI}>`);
    }

    const prompt = message.content.slice(3).trim();
    if (!prompt) return message.reply("Tulis pertanyaan setelah !ai");

    try {
      await message.channel.sendTyping();

      const response = await axios.post(
        "https://api.groq.com/openai/v1/chat/completions",
        {
          model: "llama-3.1-8b-instant",
          messages: [
            { role: "system", content: "Kamu adalah AI Discord yang santai dan ramah." },
            { role: "user", content: prompt }
          ],
          temperature: 0.7
        },
        {
          headers: {
            Authorization: `Bearer ${process.env.AI_KEY}`,
            "Content-Type": "application/json"
          }
        }
      );

      const reply = response.data?.choices?.[0]?.message?.content;
      if (!reply) return message.reply("⚠️ AI tidak memberikan respon.");

      return message.reply(
        reply.length > 2000 ? reply.slice(0, 1990) : reply
      );

    } catch (err) {
      console.log("AI ERROR:", err.response?.data || err.message);
      return message.reply("⚠️ Error AI, cek log Railway.");
    }
  }

/* =========================
   FILE SCANNER (SCAN CHANNEL ONLY)
========================= */
  if (message.channel.id === CHANNEL_SCAN && message.attachments.size > 0) {

    const file = message.attachments.first();
    const ext = path.extname(file.name).toLowerCase();

    if (!allowedExt.includes(ext)) {
      return message.reply(`
━━━━━━━━━━━━━━━━━━
❌ FORMAT FILE TIDAK DIDUKUNG
━━━━━━━━━━━━━━━━━━

👤 Pengguna        : ${message.author}
📄 Status File     : Tidak Valid

📂 Ketentuan:
• File harus berisi script Lua (.lua / .luac)
• Maksimal ukuran file 5MB

⚠️ Silakan upload file yang sesuai.

━━━━━━━━━━━━━━━━━━
💡 Ketik !menu untuk bantuan
━━━━━━━━━━━━━━━━━━
`);
    }

    if (file.size > MAX_SIZE) {
      return message.reply("❌ File melebihi batas 5MB.");
    }

    try {
      const response = await axios.get(file.url);
      const content = response.data.toString();

      let risk = 0;
      let found = [];

      if (content.includes("discord.com/api/webhooks")) {
        risk += 50;
        found.push("Webhook Discord terdeteksi");
      }

      if (content.toLowerCase().includes("getfenv") || content.includes("http.request")) {
        risk += 30;
        found.push("Struktur kode mencurigakan");
      }

      if (content.includes("string.char")) {
        risk += 20;
        found.push("Pola obfuscation terdeteksi");
      }

      let status = "🟢 AMAN";
      if (risk >= 60) status = "🔴 BAHAYA";
      else if (risk >= 30) status = "🟡 MENCURIGAKAN";

      return message.reply(`
━━━━━━━━━━━━━━━━━━
🛡️ HASIL PEMINDAIAN FILE
━━━━━━━━━━━━━━━━━━

👤 Pengguna : ${message.author}

📄 Nama File :
${file.name}

📦 Ukuran :
${(file.size / 1024 / 1024).toFixed(2)} MB

📊 Status :
${status}

⚠️ Tingkat Risiko :
${risk}%

🧠 Jumlah Pola Terdeteksi :
${found.length} pola

🔎 Detail Analisis :
${found.length ? found.map(f => "• " + f).join("\n") : "Tidak terdeteksi pola mencurigakan"}

━━━━━━━━━━━━━━━━━━
🔍 Deteksi manual by Tatang Bot
━━━━━━━━━━━━━━━━━━
`);
    } catch (err) {
      console.log("SCAN ERROR:", err.message);
      return message.reply("⚠️ Gagal memindai file.");
    }
  }

});

client.login(process.env.DISCORD_TOKEN);
