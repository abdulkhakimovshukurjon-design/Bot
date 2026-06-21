const API = {
  async init(data) {
    const r = await fetch("/api/games/init", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return r.json();
  },
  async play(game, payload) {
    payload.user_id = user ? user.id : null;
    payload.initData = initDataStr;
    const r = await fetch(`/api/games/${game}/play`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return r.json();
  },
  async upgradeStatus(initData) {
    const r = await fetch("/api/games/upgrade/status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ initData, user_id: user ? user.id : null }),
    });
    return r.json();
  },
};

let tg = null;
try { tg = window.Telegram.WebApp; tg.expand(); } catch (e) { tg = null; }
let user = null, balance = 0, currentGame = null, selectedBet = 0, initDataStr = "";

function $(id) { return document.getElementById(id); }

// ===== PARTICLES =====
function spawnParticles() {
  const container = $("particles");
  for (let i = 0; i < 30; i++) {
    const p = document.createElement("div");
    p.className = "particle";
    p.style.left = Math.random() * 100 + "%";
    p.style.animationDuration = (10 + Math.random() * 20) + "s";
    p.style.animationDelay = (Math.random() * 20) + "s";
    p.style.width = p.style.height = (2 + Math.random() * 4) + "px";
    const colors = ["var(--neon-purple)", "var(--neon-blue)", "var(--neon-gold)", "var(--neon-cyan)"];
    p.style.background = colors[Math.floor(Math.random() * colors.length)];
    container.appendChild(p);
  }
  const coins = ["🪙", "💰", "✨"];
  for (let i = 0; i < 6; i++) {
    const c = document.createElement("div");
    c.className = "floating-coin";
    c.textContent = coins[Math.floor(Math.random() * coins.length)];
    c.style.left = Math.random() * 100 + "%";
    c.style.fontSize = (14 + Math.random() * 14) + "px";
    c.style.animationDuration = (25 + Math.random() * 25) + "s";
    c.style.animationDelay = (Math.random() * 30) + "s";
    container.appendChild(c);
  }
}

// ===== TOAST =====
function showToast(msg, isGood) {
  const t = $("toast");
  t.textContent = msg;
  t.style.background = isGood ? "linear-gradient(135deg, rgba(16,185,129,0.9), rgba(6,182,212,0.9))" : "linear-gradient(135deg, rgba(239,68,68,0.9), rgba(168,85,247,0.9))";
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2800);
}

function updateBalanceUI() {
  $("balance").textContent = balance.toLocaleString();
}

// ===== INIT =====
async function init() {
  spawnParticles();
  if (tg && tg.initData) initDataStr = tg.initData;
  const urlParams = new URLSearchParams(window.location.search);
  const urlUserId = urlParams.get("user_id") ? parseInt(urlParams.get("user_id")) : null;

  if (initDataStr) {
    const res = await API.init({ initData: initDataStr });
    if (res.ok) { user = res.user; balance = res.balance; updateBalanceUI(); afterLogin(); return; }
  }
  if (urlUserId) {
    const res = await API.init({ user_id: urlUserId });
    if (res.ok) { user = res.user; balance = res.balance; updateBalanceUI(); afterLogin(); return; }
  }

  $("app").innerHTML = `
    <div id="login-form">
      <h2 style="font-family:Orbitron,sans-serif;color:var(--neon-gold);">🎮 Free UC Bot</h2>
      <p style="color:var(--text-secondary);margin:16px 0;">Telegram ID ingizni kiriting:</p>
      <input type="number" id="uid-input" placeholder="Telegram ID" style="padding:12px;border-radius:10px;border:1px solid var(--glass-border);width:200px;font-size:16px;background:var(--glass);color:#fff;text-align:center;outline:none;">
      <button id="uid-login-btn" style="display:block;width:200px;margin:12px auto;padding:14px;border:none;border-radius:12px;font-size:16px;font-weight:700;background:linear-gradient(135deg,var(--neon-purple),var(--neon-pink));color:#fff;cursor:pointer;font-family:Orbitron,sans-serif;">Kirish</button>
      <p style="color:#666;font-size:12px;margin-top:12px;">ID ni botdagi profil bo'limidan topasiz</p>
    </div>`;
  document.getElementById("uid-login-btn").addEventListener("click", async () => {
    const uid = parseInt(document.getElementById("uid-input").value);
    if (!uid) return showToast("ID kiriting", false);
    const res = await API.init({ user_id: uid });
    if (res.ok) { user = res.user; balance = res.balance; updateBalanceUI(); location.reload(); }
    else { showToast(res.error || "Xatolik", false); }
  });
}

function afterLogin() {
  $("stat-level").textContent = "5";
  loadWinners();
}

// ===== GAME CARDS =====
document.querySelectorAll(".game-card").forEach((card) => {
  card.addEventListener("click", () => {
    const g = card.dataset.game;
    currentGame = g; selectedBet = 0;
    $("app").style.display = "none";
    $("game-screen").style.display = "block";
    $("game-screen-title").textContent = card.querySelector(".game-name").textContent;
    showGame(g);
  });
});
$("game-back-btn").addEventListener("click", () => {
  $("game-screen").style.display = "none";
  $("app").style.display = "block";
  currentGame = null;
});

// ===== FEATURE BUTTONS =====
$("daily-bonus-btn").addEventListener("click", () => showToast("🎁 Kunlik bonus olindi! +10 UC", true));
$("settings-btn").addEventListener("click", () => showToast("⚙️ Sozlamalar tez kunda", false));
document.querySelectorAll("#scroll-bonus,#scroll-withdraw,#scroll-referral,#scroll-leaderboard,#scroll-profile").forEach(el => {
  el.addEventListener("click", () => showToast("⭐ Tez kunda", false));
});

// ===== GAME RENDERERS =====
function showGame(game) {
  const c = $("game-content"); c.innerHTML = "";
  if (game === "baraban") renderBaraban(c);
  else if (game === "plinko") renderPlinko(c);
  else if (game === "upgrade") renderUpgrade(c);
  else if (game === "dice") renderDice(c);
  else if (game === "battle") renderBattle(c);
}

function renderBetSelector(container, amounts = [10, 25, 50, 100, 250, 500]) {
  const div = document.createElement("div"); div.className = "bet-btns";
  amounts.forEach(a => {
    const btn = document.createElement("button"); btn.className = "bet-btn";
    btn.textContent = a + " UC"; btn.dataset.amount = a;
    btn.addEventListener("click", () => {
      div.querySelectorAll(".bet-btn").forEach(b => b.classList.remove("selected"));
      btn.classList.add("selected"); selectedBet = a;
    });
    div.appendChild(btn);
  });
  container.appendChild(div);
}

// ===== BARABAN =====
function renderBaraban(c) {
  c.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;margin-bottom:8px;">🎰 Aylantirib katta yutib oling! 0x – 20x</p>';
  renderBetSelector(c);
  const btn = document.createElement("button"); btn.className = "play-btn";
  btn.innerHTML = '<span class="spinner" style="display:none;" id="spin-spinner"></span> <span id="spin-text">🎰 Aylantirish</span>';
  btn.addEventListener("click", async () => {
    if (!selectedBet) return showToast("Avval tikish miqdorini tanlang", false);
    btn.disabled = true; btn.querySelector("#spin-text").textContent = "⏳...";
    try {
      const res = await API.play("baraban", { amount: selectedBet });
      if (res.ok) { balance = res.balance; updateBalanceUI(); showResultBaraban(c, res); }
      else showToast(res.error || "Xatolik", false);
    } catch (e) { showToast("Server xatosi", false); }
    btn.disabled = false; btn.querySelector("#spin-text").textContent = "🎰 Aylantirish";
  });
  c.appendChild(btn);
}
function showResultBaraban(c, res) {
  const old = c.querySelector(".result"); if (old) old.remove();
  const d = document.createElement("div"); d.className = "result " + (res.win > 0 ? "win" : "lose");
  d.innerHTML = `<div class="wheel-display">${res.wheel || ""}</div>` + (res.win > 0 ? `🎉 Yutdingiz! <strong>+${res.win} UC</strong> (x${res.multiplier})` : `😔 Yutqazdingiz. -${res.amount} UC`) + `<br><span style="font-size:13px;color:var(--neon-gold);">💰 ${res.balance} UC</span>`;
  c.appendChild(d);
}

// ===== PLINKO =====
function renderPlinko(c) {
  c.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;margin-bottom:8px;">🧩 Plinko — to\'pni tashlang va ko\'paytirib oling!</p>';
  renderBetSelector(c);
  const btn = document.createElement("button"); btn.className = "play-btn"; btn.textContent = "🧩 Tashlash";
  btn.addEventListener("click", async () => {
    if (!selectedBet) return showToast("Avval tikish miqdorini tanlang", false);
    btn.disabled = true; btn.textContent = "⏳...";
    try {
      const res = await API.play("plinko", { amount: selectedBet });
      if (res.ok) { balance = res.balance; updateBalanceUI(); showResultPlinko(c, res); }
      else showToast(res.error || "Xatolik", false);
    } catch (e) { showToast("Server xatosi", false); }
    btn.disabled = false; btn.textContent = "🧩 Tashlash";
  });
  c.appendChild(btn);
}
function showResultPlinko(c, res) {
  const old = c.querySelector(".result"); if (old) old.remove();
  const d = document.createElement("div"); d.className = "result " + (res.win > 0 ? "win" : "lose");
  d.innerHTML = (res.board ? `<div class="plinko-board">${res.board.replace(/\n/g,"<br>")}</div>` : "") + (res.win > 0 ? `🎉 Yutdingiz! <strong>+${res.win} UC</strong> (x${res.multiplier})` : `😔 Yutqazdingiz. -${res.amount} UC`) + `<br><span style="font-size:13px;color:var(--neon-gold);">💰 ${res.balance} UC</span>`;
  c.appendChild(d);
}

// ===== UPGRADE =====
async function renderUpgrade(c) {
  c.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;margin-bottom:8px;">⬆️ Darajangizni oshiring! Muvaffaqiyatsiz bo\'lsa 0 ga tushadi.</p>';
  const info = document.createElement("div"); info.className = "level-info"; info.id = "upgrade-info"; c.appendChild(info);
  const btn = document.createElement("button"); btn.className = "play-btn"; btn.textContent = "⬆️ Yangilash";
  btn.addEventListener("click", async () => {
    btn.disabled = true; btn.textContent = "⏳...";
    try {
      const res = await API.play("upgrade", {});
      if (res.ok) { balance = res.balance; updateBalanceUI(); showResultUpgrade(c, res); await refreshUpgradeInfo(info); }
      else showToast(res.error || "Xatolik", false);
    } catch (e) { showToast("Server xatosi", false); }
    btn.disabled = false; btn.textContent = "⬆️ Yangilash";
  });
  c.appendChild(btn);
  await refreshUpgradeInfo(info);
}
async function refreshUpgradeInfo(el) {
  try {
    const res = await API.upgradeStatus();
    if (res.ok) el.innerHTML = `🔧 Daraja: <strong>${res.level}</strong> | Narx: <strong>${res.cost} UC</strong> | Muvaffaqiyat: <strong>${res.chance}%</strong>`;
  } catch (e) {}
}
function showResultUpgrade(c, res) {
  const old = c.querySelector(".result"); if (old) old.remove();
  const d = document.createElement("div"); d.className = "result " + (res.win > 0 ? "win" : "lose");
  d.innerHTML = (res.win > 0 ? `✅ Yangilash muvaffaqiyatli!<br>Daraja: <strong>${res.level}</strong><br>+${res.win} UC` : `❌ Muvaffaqiyatsiz!<br>Daraja 0 ga tushdi`) + `<br><span style="font-size:13px;color:var(--neon-gold);">💰 ${res.balance} UC</span>`;
  c.appendChild(d);
}

// ===== DICE =====
function renderDice(c) {
  c.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;margin-bottom:8px;">🎲 Sonni toping va x6 yutib oling!</p>';
  renderBetSelector(c);
  const facesDiv = document.createElement("div"); facesDiv.className = "dice-faces";
  let selectedFace = 0;
  for (let i = 1; i <= 6; i++) {
    const f = document.createElement("div"); f.className = "dice-face";
    f.textContent = ["⚀","⚁","⚂","⚃","⚄","⚅"][i-1]; f.dataset.num = i;
    f.addEventListener("click", () => { facesDiv.querySelectorAll(".dice-face").forEach(x => x.classList.remove("selected")); f.classList.add("selected"); selectedFace = i; });
    facesDiv.appendChild(f);
  }
  c.appendChild(facesDiv);
  const btn = document.createElement("button"); btn.className = "play-btn"; btn.textContent = "🎲 Tashlash";
  btn.addEventListener("click", async () => {
    if (!selectedBet) return showToast("Avval tikish miqdorini tanlang", false);
    if (!selectedFace) return showToast("Son tanlang (1-6)", false);
    btn.disabled = true; btn.textContent = "⏳...";
    try {
      const res = await API.play("dice", { amount: selectedBet, number: selectedFace });
      if (res.ok) { balance = res.balance; updateBalanceUI(); showResultDice(c, res); }
      else showToast(res.error || "Xatolik", false);
    } catch (e) { showToast("Server xatosi", false); }
    btn.disabled = false; btn.textContent = "🎲 Tashlash";
  });
  c.appendChild(btn);
}
function showResultDice(c, res) {
  const old = c.querySelector(".result"); if (old) old.remove();
  const d = document.createElement("div"); d.className = "result " + (res.win > 0 ? "win" : "lose");
  d.innerHTML = `<div style="font-size:48px;margin:8px 0;">${res.dice_face || ""}</div>` + `Siz: ${res.chosen} | Tushdi: ${res.result}<br>` + (res.win > 0 ? `🎉 Tabriklaymiz! <strong>+${res.win} UC</strong> (x6)` : `😔 Yutqazdingiz. -${res.amount} UC`) + `<br><span style="font-size:13px;color:var(--neon-gold);">💰 ${res.balance} UC</span>`;
  c.appendChild(d);
}

// ===== BATTLE =====
async function renderBattle(c) {
  c.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;margin-bottom:8px;">⚔️ Boshqa o\'yinchi bilan jang qiling!</p>';
  renderBetSelector(c, [10, 25, 50, 100, 250]);
  const statusDiv = document.createElement("div"); statusDiv.id = "battle-status"; c.appendChild(statusDiv);
  const createBtn = document.createElement("button"); createBtn.className = "play-btn"; createBtn.textContent = "⚔️ Battle yaratish";
  createBtn.addEventListener("click", async () => {
    if (!selectedBet) return showToast("Avval tikish miqdorini tanlang", false);
    createBtn.disabled = true; createBtn.textContent = "⏳...";
    try {
      const res = await API.play("battle_create", { amount: selectedBet });
      if (res.ok) { statusDiv.innerHTML = `✅ Battle yaratildi! ID: <strong>${res.battle_id}</strong><br>Raqib kutilmoqda...`; showToast("Battle yaratildi!", true); }
      else showToast(res.error || "Xatolik", false);
    } catch (e) { showToast("Server xatosi", false); }
    createBtn.disabled = false; createBtn.textContent = "⚔️ Battle yaratish";
  });
  c.appendChild(createBtn);
  const joinBtn = document.createElement("button"); joinBtn.className = "play-btn"; joinBtn.textContent = "🔍 Battlega qo'shilish";
  joinBtn.style.background = "linear-gradient(135deg, #0f3460, #1a5276)";
  joinBtn.addEventListener("click", async () => {
    joinBtn.disabled = true; joinBtn.textContent = "⏳...";
    try {
      const res = await API.play("battle_list", {});
      if (res.ok && res.battles && res.battles.length > 0) {
        let html = "Mavjud battellar:<br>";
        res.battles.forEach(b => { html += `<button class="bet-btn" onclick="window.joinBattle(${b.id},${b.amount})" style="margin:4px;">${b.creator_name || b.creator_id}: ${b.amount} UC</button> `; });
        statusDiv.innerHTML = html;
      } else showToast("Hozircha battel yo'q", false);
    } catch (e) { showToast("Server xatosi", false); }
    joinBtn.disabled = false; joinBtn.textContent = "🔍 Battlega qo'shilish";
  });
  c.appendChild(joinBtn);
}
window.joinBattle = async (bid, amt) => {
  try {
    const res = await API.play("battle_join", { battle_id: bid });
    if (res.ok) { balance = res.balance; updateBalanceUI(); showResultBattle(document.getElementById("game-content"), res); }
    else showToast(res.error || "Xatolik", false);
  } catch (e) { showToast("Server xatosi", false); }
};
function showResultBattle(c, res) {
  const old = c.querySelector(".result"); if (old) old.remove();
  const d = document.createElement("div"); d.className = "result " + (res.win > 0 ? "win" : "lose");
  d.innerHTML = (res.win > 0 ? `🏆 Siz yutdingiz! +${res.total} UC!` : `😔 Raqib yutdi. -${res.amount} UC`) + `<br><span style="font-size:13px;color:var(--neon-gold);">💰 ${res.balance} UC</span>`;
  c.appendChild(d);
}

// ===== WINNERS (mock) =====
function loadWinners() {
  const names = ["Shukurjon", "Botir", "Zafar", "Dilmurod", "Akmal", "Jasur", "Ozod", "Hamid"];
  const games = ["Baraban", "Plinko", "Dice", "Upgrade", "Battle"];
  const amounts = [100, 250, 500, 50, 1000, 150, 300, 750];
  const list = $("winners-list"); list.innerHTML = "";
  for (let i = 0; i < 5; i++) {
    const d = document.createElement("div"); d.className = "winner-item";
    d.innerHTML = `
      <div class="winner-avatar">${names[i % names.length][0]}</div>
      <div class="winner-info">
        <div class="winner-name">${names[i % names.length]}</div>
        <div class="winner-meta">${games[i % games.length]} • ${i+1} daqiqa oldin</div>
      </div>
      <div class="winner-amount">+${amounts[i % amounts.length]} UC</div>`;
    list.appendChild(d);
  }
}

// ===== START =====
init();
