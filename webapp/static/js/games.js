const API = {
  async init(initData) {
    const r = await fetch("/api/games/init", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ initData }),
    });
    return r.json();
  },
  async play(game, payload) {
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
      body: JSON.stringify({ initData }),
    });
    return r.json();
  },
};

let tg = null;
try {
  tg = window.Telegram.WebApp;
  tg.expand();
} catch (e) {
  tg = null;
}

let user = null;
let balance = 0;
let currentGame = null;
let selectedBet = 0;
let initDataStr = "";

function $(id) { return document.getElementById(id); }

function showToast(msg, isGood) {
  const t = $("toast");
  t.textContent = msg;
  t.style.background = isGood ? "#2e7d32" : "#c62828";
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2500);
}

function updateBalanceUI() {
  $("balance").textContent = balance;
  const bi = $("balance-info");
  if (bi) bi.innerHTML = `💰 Balans: <span id="balance">${balance}</span> UC`;
}

async function init() {
  if (tg && tg.initData) {
    initDataStr = tg.initData;
  }
  try {
    const res = await API.init({ initData: initDataStr });
    if (res.ok) {
      user = res.user;
      balance = res.balance;
      updateBalanceUI();
    } else {
      showToast("Xatolik: " + (res.error || "Avtorizatsiyadan o'tilmadi"), false);
    }
  } catch (e) {
    showToast("Server bilan bog'lanib bo'lmadi", false);
  }
}

// Lobby
document.querySelectorAll(".game-card").forEach((card) => {
  card.addEventListener("click", () => {
    const g = card.dataset.game;
    currentGame = g;
    selectedBet = 0;
    $("lobby").style.display = "none";
    $("game-screen").style.display = "block";
    showGame(g);
  });
});

$("back-to-lobby").addEventListener("click", () => {
  $("game-screen").style.display = "none";
  $("lobby").style.display = "block";
  currentGame = null;
});

// Game renderers
function showGame(game) {
  const container = $("game-content");
  if (game === "baraban") renderBaraban(container);
  else if (game === "plinko") renderPlinko(container);
  else if (game === "upgrade") renderUpgrade(container);
  else if (game === "dice") renderDice(container);
  else if (game === "battle") renderBattle(container);
}

// Bet selector helper
function renderBetSelector(container, game, amounts = [10, 25, 50, 100, 250, 500]) {
  const div = document.createElement("div");
  div.className = "bet-btns";
  div.id = "bet-selector";
  amounts.forEach((a) => {
    const btn = document.createElement("button");
    btn.className = "bet-btn";
    btn.textContent = a + " UC";
    btn.dataset.amount = a;
    btn.addEventListener("click", () => {
      div.querySelectorAll(".bet-btn").forEach((b) => b.classList.remove("selected"));
      btn.classList.add("selected");
      selectedBet = a;
    });
    div.appendChild(btn);
  });
  container.appendChild(div);
}

// ---------- BARABAN ----------
function renderBaraban(container) {
  container.innerHTML = '<h2>🎰 Baraban</h2><p style="color:#888;font-size:13px;">0x, 0.5x, 1x, 1.5x, 2x, 3x, 5x, 10x, 20x</p>';
  renderBetSelector(container, "baraban");
  const playBtn = document.createElement("button");
  playBtn.className = "play-btn";
  playBtn.textContent = "🎰 Aylantirish";
  playBtn.addEventListener("click", async () => {
    if (!selectedBet) return showToast("Avval tikish miqdorini tanlang", false);
    playBtn.disabled = true;
    playBtn.textContent = "⏳ Aylanmoqda...";
    try {
      const res = await API.play("baraban", { amount: selectedBet, initData: initDataStr });
      if (res.ok) {
        balance = res.balance;
        updateBalanceUI();
        showResult(container, res);
      } else {
        showToast(res.error || "Xatolik", false);
      }
    } catch (e) {
      showToast("Server xatosi", false);
    }
    playBtn.disabled = false;
    playBtn.textContent = "🎰 Aylantirish";
  });
  container.appendChild(playBtn);
}

// ---------- PLINKO ----------
function renderPlinko(container) {
  container.innerHTML = '<h2>🧩 Plinko</h2><p style="color:#888;font-size:13px;">0.2x ~ 10x gacha</p>';
  renderBetSelector(container, "plinko");
  const playBtn = document.createElement("button");
  playBtn.className = "play-btn";
  playBtn.textContent = "🧩 Tashlash";
  playBtn.addEventListener("click", async () => {
    if (!selectedBet) return showToast("Avval tikish miqdorini tanlang", false);
    playBtn.disabled = true;
    playBtn.textContent = "⏳ Tushmoqda...";
    try {
      const res = await API.play("plinko", { amount: selectedBet, initData: initDataStr });
      if (res.ok) {
        balance = res.balance;
        updateBalanceUI();
        showResult(container, res);
      } else {
        showToast(res.error || "Xatolik", false);
      }
    } catch (e) {
      showToast("Server xatosi", false);
    }
    playBtn.disabled = false;
    playBtn.textContent = "🧩 Tashlash";
  });
  container.appendChild(playBtn);
}

// ---------- UPGRADE ----------
async function renderUpgrade(container) {
  container.innerHTML = '<h2>⬆️ Upgrade</h2>';
  const infoDiv = document.createElement("div");
  infoDiv.id = "upgrade-info";
  infoDiv.className = "level-info";
  container.appendChild(infoDiv);

  const playBtn = document.createElement("button");
  playBtn.className = "play-btn";
  playBtn.textContent = "⬆️ Yangilash";
  playBtn.addEventListener("click", async () => {
    playBtn.disabled = true;
    playBtn.textContent = "⏳...";
    try {
      const res = await API.play("upgrade", { initData: initDataStr });
      if (res.ok) {
        balance = res.balance;
        updateBalanceUI();
        showResult(container, res);
        await refreshUpgradeInfo(infoDiv);
      } else {
        showToast(res.error || "Xatolik", false);
      }
    } catch (e) {
      showToast("Server xatosi", false);
    }
    playBtn.disabled = false;
    playBtn.textContent = "⬆️ Yangilash";
  });
  container.appendChild(playBtn);

  await refreshUpgradeInfo(infoDiv);
}

async function refreshUpgradeInfo(el) {
  try {
    const initData = tg ? tg.initData : "";
    const res = await API.upgradeStatus(initData);
    if (res.ok) {
      el.innerHTML = `🔧 Daraja: ${res.level} | Narx: ${res.cost} UC | Muvaffaqiyat: ${res.chance}%`;
    }
  } catch (e) {}
}

// ---------- DICE ----------
function renderDice(container) {
  container.innerHTML = '<h2>🎲 Dice</h2><p style="color:#888;font-size:13px;">1-6 gacha son. To\'g\'ri topsangiz x6!</p>';
  renderBetSelector(container, "dice");

  const facesDiv = document.createElement("div");
  facesDiv.className = "dice-faces";
  let selectedFace = 0;
  for (let i = 1; i <= 6; i++) {
    const f = document.createElement("div");
    f.className = "dice-face";
    f.textContent = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"][i - 1];
    f.dataset.num = i;
    f.addEventListener("click", () => {
      facesDiv.querySelectorAll(".dice-face").forEach((x) => x.classList.remove("selected"));
      f.classList.add("selected");
      selectedFace = i;
    });
    facesDiv.appendChild(f);
  }
  container.appendChild(facesDiv);

  const playBtn = document.createElement("button");
  playBtn.className = "play-btn";
  playBtn.textContent = "🎲 Tashlash";
  playBtn.addEventListener("click", async () => {
    if (!selectedBet) return showToast("Avval tikish miqdorini tanlang", false);
    if (!selectedFace) return showToast("Son tanlang (1-6)", false);
    playBtn.disabled = true;
    playBtn.textContent = "⏳...";
    try {
      const res = await API.play("dice", { amount: selectedBet, number: selectedFace, initData: initDataStr });
      if (res.ok) {
        balance = res.balance;
        updateBalanceUI();
        showResult(container, res);
      } else {
        showToast(res.error || "Xatolik", false);
      }
    } catch (e) {
      showToast("Server xatosi", false);
    }
    playBtn.disabled = false;
    playBtn.textContent = "🎲 Tashlash";
  });
  container.appendChild(playBtn);
}

// ---------- BATTLE ----------
async function renderBattle(container) {
  container.innerHTML = '<h2>⚔️ UC Battle</h2><p style="color:#888;font-size:13px;">Boshqa o\'yinchi bilan jang qiling!</p>';
  renderBetSelector(container, "battle", [10, 25, 50, 100, 250]);

  const statusDiv = document.createElement("div");
  statusDiv.id = "battle-status";
  statusDiv.style.margin = "10px 0";
  statusDiv.style.fontSize = "14px";
  statusDiv.style.color = "#aaa";
  container.appendChild(statusDiv);

  const createBtn = document.createElement("button");
  createBtn.className = "play-btn";
  createBtn.textContent = "⚔️ Battle yaratish";
  createBtn.addEventListener("click", async () => {
    if (!selectedBet) return showToast("Avval tikish miqdorini tanlang", false);
    createBtn.disabled = true;
    createBtn.textContent = "⏳...";
    try {
      const res = await API.play("battle_create", { amount: selectedBet, initData: initDataStr });
      if (res.ok) {
        statusDiv.innerHTML = `✅ Battle yaratildi! ${res.amount} UC. ID: ${res.battle_id}.<br>Raqib qatnashishi uchun link: <a href="#" id="battle-link" style="color:#ffd700;">/${res.battle_id}</a>`;
        showToast("Battle yaratildi! Raqib kutilmoqda...", true);
      } else {
        showToast(res.error || "Xatolik", false);
      }
    } catch (e) { showToast("Server xatosi", false); }
    createBtn.disabled = false;
    createBtn.textContent = "⚔️ Battle yaratish";
  });
  container.appendChild(createBtn);

  const joinBtn = document.createElement("button");
  joinBtn.className = "play-btn";
  joinBtn.textContent = "🔍 Battlega qo'shilish";
  joinBtn.style.background = "#0f3460";
  joinBtn.addEventListener("click", async () => {
    joinBtn.disabled = true;
    joinBtn.textContent = "⏳...";
    try {
      const res = await API.play("battle_list", { initData: initDataStr });
      if (res.ok && res.battles && res.battles.length > 0) {
        let html = "Mavjud battellar:<br>";
        res.battles.forEach((b) => {
          html += `<button class="bet-btn" onclick="joinBattle(${b.id}, ${b.amount})">${b.creator_name || b.creator_id}: ${b.amount} UC</button> `;
        });
        statusDiv.innerHTML = html;
      } else {
        showToast("Hozircha battel yo'q", false);
      }
    } catch (e) { showToast("Server xatosi", false); }
    joinBtn.disabled = false;
    joinBtn.textContent = "🔍 Battlega qo'shilish";
  });
  container.appendChild(joinBtn);
}

window.joinBattle = async function(battleId, amount) {
  try {
    const res = await API.play("battle_join", { battle_id: battleId, initData: initDataStr });
    if (res.ok) {
      balance = res.balance;
      updateBalanceUI();
      showResult(document.getElementById("game-content"), res);
    } else {
      showToast(res.error || "Xatolik", false);
    }
  } catch (e) { showToast("Server xatosi", false); }
};

// ---------- Result display ----------
function showResult(container, res) {
  const oldResult = container.querySelector(".result");
  if (oldResult) oldResult.remove();

  const div = document.createElement("div");
  div.className = "result " + (res.win > 0 ? "win" : "lose");

  let html = "";
  if (res.game === "baraban") {
    html = `<div class="wheel-display">${res.wheel || ""}</div>`;
  }
  if (res.game === "plinko" && res.board) {
    html = `<div class="plinko-board">${res.board.replace(/\n/g, "<br>")}</div>`;
  }
  if (res.game === "dice") {
    html = `<div style="font-size:40px;margin:8px 0;">${res.dice_face || ""}</div>`;
  }

  if (res.win > 0) {
    html += `🎉 +${res.win} UC (x${res.multiplier})`;
  } else {
    html += `😔 Yutqazdingiz. -${res.amount} UC`;
  }
  html += `<br><span style="font-size:13px;color:#ffd700;">💰 ${res.balance} UC</span>`;

  if (res.game === "upgrade") {
    html = `<br>` + (res.win > 0
      ? `✅ Yangilash muvaffaqiyatli! Daraja: ${res.level}`
      : `❌ Muvaffaqiyatsiz! Daraja 0 ga tushdi.`);
    html += `<br><span style="font-size:13px;color:#ffd700;">💰 ${res.balance} UC</span>`;
  }

  div.innerHTML = html;
  container.appendChild(div);
}

// Init
init();
