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

/* ================= CONFIG ================= */
const CHANNEL_SCAN = "1469740150522380299";
const CHANNEL_AI = "1475164217115021475";
const MAX_SIZE = 5 * 1024 * 1024;
const allowedExt = ['.lua', '.luac', '.zip', '.rar', '.7z', '.txt'];
const startTime = Date.now();

/* ================= UTIL ================= */
function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/* ================= READY ================= */
client.once(Events.ClientReady, (c) => {
  console.log(`✅ Bot online sebagai ${c.user.tag}`);
});

/* ================= ERROR HANDLER ================= */
process.on("unhandledRejection", console.error);
process.on("uncaughtException", console.error);

/* ================= MESSAGE ================= */
client.on(Events.MessageCreate, async (message) => {
  if (message.author.bot) return;

/* ================= !PING ================= */
  if (message.content === "!ping") {

    const uptime = Math.floor((Date.now() - startTime) / 1000);
    const hours = Math.floor(uptime / 3600);
    const minutes = Math.floor((uptime % 3600) / 60);

    const embed = new EmbedBuilder()
      .setColor("#00ff88")
      .setTitle("🏓 Pong — System Status")
      .setDescription("```Sistem aktif & berjalan normal```")
      .addFields(
        { name: "⚡ Latency", value: `\`${client.ws.ping} ms\``, inline: true },
        { name: "⏳ Uptime", value: `\`${hours} jam ${minutes} menit\``, inline: true },
        { name: "🟢 Status", value: "`Online`", inline: true }
      )
      .setFooter({ text: "Tatang Bot • Security System" })
      .setTimestamp();

    return message.reply({ embeds: [embed] });
  }

/* ================= !MENU ================= */
  if (message.content === "!menu") {

    const embed = new EmbedBuilder()
      .setColor("#5865F2")
      .setTitle("📘 Tatang Bot — Control Panel")
      .setDescription(`
🛡️ **Scanner Channel**
<#${CHANNEL_SCAN}>

🤖 **AI Channel**
<#${CHANNEL_AI}>
`)
      .addFields(
        {
          name: "📂 Format Didukung",
          value: "`.lua` `.luac` `.zip` `.rar` `.7z` `.txt`"
        },
        {
          name: "📦 Batas Ukuran",
          value: "`Maksimal 5MB per file`"
        },
        {
          name: "📊 Status Scan",
          value: "🟢 Aman\n🟡 Mencurigakan\n🔴 Bahaya"
        }
      )
      .setFooter({ text: "Gunakan bot dengan bijak 🚀" })
      .setTimestamp();

    return message.reply({ embeds: [embed] });
  }

/* ================= !AI ================= */
  if (message.content.toLowerCase().startsWith("!ai")) {

    if (message.channel.id !== CHANNEL_AI) {
      return message.reply(`⚠️ Gunakan di <#${CHANNEL_AI}>`);
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
            { role: "system", content: "Kamu adalah AI Discord yang santai, jelas, dan profesional." },
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

      return message.reply(reply.slice(0, 1990));

    } catch (err) {
      console.log(err.response?.data || err.message);
      return message.reply("⚠️ Terjadi error pada AI.");
    }
  }

/* ================= SCANNER ================= */
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
      const response = await axios.get(file.url, { responseType: "arraybuffer" });
      const content = Buffer.from(response.data).toString("utf8");

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
        found.push("Obfuscation pattern terdeteksi");
      }

      let status = "🟢 Aman";
      let color = "#00ff88";

      if (risk >= 60) {
        status = "🔴 Bahaya";
        color = "#ff3b3b";
      } else if (risk >= 30) {
        status = "🟡 Mencurigakan";
        color = "#ffcc00";
      }

      const embed = new EmbedBuilder()
        .setColor(color)
        .setTitle("🛡️ Hasil Analisis Keamanan")
        .setDescription("```Analisis file selesai diproses```")
        .addFields(
          { name: "👤 Pengguna", value: `${message.author}`, inline: true },
          { name: "📄 Nama File", value: `\`${file.name}\``, inline: true },
          { name: "📦 Ukuran File", value: `\`${formatSize(file.size)}\``, inline: true },
          { name: "📊 Status", value: status, inline: true },
          { name: "⚠️ Tingkat Risiko", value: `\`${risk}%\``, inline: true },
          {
            name: "🔎 Detail Deteksi",
            value: found.length
              ? found.map(f => `• ${f}`).join("\n")
              : "Tidak ditemukan pola mencurigakan"
          }
        )
        .setFooter({ text: "Tatang Bot • Advanced Security Scanner" })
        .setTimestamp();

      return message.reply({ embeds: [embed] });

    } catch (err) {
      console.log(err.message);
      return message.reply("⚠️ Gagal memproses file.");
    }
  }

});

client.login(process.env.DISCORD_TOKEN);
