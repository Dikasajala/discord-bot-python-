require('dotenv').config();
const {
  Client,
  GatewayIntentBits,
  Events,
  EmbedBuilder
} = require('discord.js');
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
   GLOBAL ERROR HANDLER
========================= */
process.on("unhandledRejection", console.error);
process.on("uncaughtException", console.error);

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

    const embed = new EmbedBuilder()
      .setColor("Green")
      .setTitle("🏓 Pong!")
      .addFields(
        { name: "Status", value: "Online", inline: true },
        { name: "Latensi", value: `${client.ws.ping} ms`, inline: true },
        { name: "Uptime", value: `${hours} jam ${minutes} menit`, inline: false }
      )
      .setFooter({ text: "Tatang Bot Security System" })
      .setTimestamp();

    return message.reply({ embeds: [embed] });
  }

/* =========================
   !MENU
========================= */
  if (message.content === "!menu") {
    const embed = new EmbedBuilder()
      .setColor("Blue")
      .setTitle("🤖 TATANG BOT — MENU")
      .setDescription(`
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
`)
      .setFooter({ text: "Security Scanner Lua" })
      .setTimestamp();

    return message.reply({ embeds: [embed] });
  }

/* =========================
   !AI (LOCK CHANNEL)
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
      if (!reply) return message.reply("⚠️ AI tidak merespon.");

      return message.reply(
        reply.length > 2000 ? reply.slice(0, 1990) : reply
      );

    } catch (err) {
      console.log("AI ERROR:", err.response?.data || err.message);
      return message.reply("⚠️ Error AI, cek log Railway.");
    }
  }

/* =========================
   FILE SCANNER (EMBED)
========================= */
  if (message.channel.id === CHANNEL_SCAN && message.attachments.size > 0) {

    const file = message.attachments.first();
    const ext = path.extname(file.name).toLowerCase();

    if (!allowedExt.includes(ext)) {
      return message.reply("❌ Format file tidak didukung.");
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

      let status = "🟢 Aman";
      let color = "Green";

      if (risk >= 60) {
        status = "🔴 Bahaya";
        color = "Red";
      } else if (risk >= 30) {
        status = "🟡 Mencurigakan";
        color = "Yellow";
      }

      const embed = new EmbedBuilder()
        .setColor(color)
        .setTitle("🛡️ HASIL PEMINDAIAN FILE")
        .addFields(
          { name: "Pengguna", value: `${message.author}`, inline: true },
          { name: "Nama File", value: file.name, inline: true },
          { name: "Ukuran", value: `${(file.size / 1024 / 1024).toFixed(2)} MB`, inline: true },
          { name: "Status", value: status, inline: true },
          { name: "Tingkat Risiko", value: `${risk}%`, inline: true },
          {
            name: "Detail Deteksi",
            value: found.length ? found.map(f => `• ${f}`).join("\n") : "Tidak ada pola mencurigakan"
          }
        )
        .setFooter({ text: "Tatang Bot Security Scanner" })
        .setTimestamp();

      return message.reply({ embeds: [embed] });

    } catch (err) {
      console.log("SCAN ERROR:", err.message);
      return message.reply("⚠️ Gagal memindai file.");
    }
  }

});

client.login(process.env.DISCORD_TOKEN);
