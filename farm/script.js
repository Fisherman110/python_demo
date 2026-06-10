const crops = {
  carrot: {
    name: "胡萝卜",
    seedName: "胡萝卜种子",
    seedPrice: 5,
    sellPrice: 12,
    growSeconds: 8,
    mainColor: "#f47a25",
    deepColor: "#c4511d",
  },
  wheat: {
    name: "小麦",
    seedName: "小麦种子",
    seedPrice: 8,
    sellPrice: 22,
    growSeconds: 14,
    mainColor: "#f2c14e",
    deepColor: "#c8892d",
  },
  tomato: {
    name: "番茄",
    seedName: "番茄种子",
    seedPrice: 12,
    sellPrice: 36,
    growSeconds: 22,
    mainColor: "#f94144",
    deepColor: "#b91f2b",
  },
};

const state = {
  money: 50,
  selectedSeed: "carrot",
  inventory: {},
  plots: Array.from({ length: 16 }, () => ({
    cropKey: null,
    plantedAt: 0,
    readyAt: 0,
  })),
};

const moneyEl = document.querySelector("#money");
const plotsEl = document.querySelector("#plots");
const shopEl = document.querySelector("#shop");
const inventoryEl = document.querySelector("#inventory");
const selectedSeedEl = document.querySelector("#selectedSeed");
const selectedHintEl = document.querySelector("#selectedHint");
const statusEl = document.querySelector("#status");
const sellAllEl = document.querySelector("#sellAll");
const resetGameEl = document.querySelector("#resetGame");

function seedKey(cropKey) {
  return `seed:${cropKey}`;
}

function cropKey(cropKey) {
  return `crop:${cropKey}`;
}

function initInventory() {
  Object.keys(crops).forEach((key) => {
    state.inventory[seedKey(key)] = 0;
    state.inventory[cropKey(key)] = 0;
  });
}

function setStatus(text) {
  statusEl.textContent = text;
}

function buySeed(key) {
  const crop = crops[key];
  if (state.money < crop.seedPrice) {
    setStatus(`金币不足，购买 ${crop.seedName} 需要 $${crop.seedPrice}。`);
    return;
  }

  state.money -= crop.seedPrice;
  state.inventory[seedKey(key)] += 1;
  state.selectedSeed = key;
  setStatus(`购买成功：${crop.seedName} +1。`);
  render();
}

function selectSeed(key) {
  state.selectedSeed = key;
  setStatus(`已选择 ${crops[key].seedName}，点击空农田即可播种。`);
  render();
}

function handlePlotClick(index) {
  const plot = state.plots[index];
  const now = Date.now();

  if (plot.cropKey && now >= plot.readyAt) {
    harvestPlot(plot);
    return;
  }

  if (plot.cropKey) {
    const remaining = Math.max(1, Math.ceil((plot.readyAt - now) / 1000));
    setStatus(`${crops[plot.cropKey].name} 还在生长，约 ${remaining} 秒后成熟。`);
    return;
  }

  plantPlot(plot);
}

function plantPlot(plot) {
  const key = state.selectedSeed;
  const crop = crops[key];
  const seedItem = seedKey(key);

  if (state.inventory[seedItem] <= 0) {
    setStatus(`背包里没有 ${crop.seedName}，请先在商店购买。`);
    return;
  }

  const now = Date.now();
  state.inventory[seedItem] -= 1;
  plot.cropKey = key;
  plot.plantedAt = now;
  plot.readyAt = now + crop.growSeconds * 1000;
  setStatus(`已播种 ${crop.name}，等待 ${crop.growSeconds} 秒成熟。`);
  render();
}

function harvestPlot(plot) {
  const key = plot.cropKey;
  state.inventory[cropKey(key)] += 1;
  plot.cropKey = null;
  plot.plantedAt = 0;
  plot.readyAt = 0;
  setStatus(`收获成功：${crops[key].name} +1，已放入背包。`);
  render();
}

function sellAllCrops() {
  let total = 0;
  const sold = [];

  Object.entries(crops).forEach(([key, crop]) => {
    const itemKey = cropKey(key);
    const count = state.inventory[itemKey];
    if (count > 0) {
      total += count * crop.sellPrice;
      sold.push(`${crop.name} x${count}`);
      state.inventory[itemKey] = 0;
    }
  });

  if (total === 0) {
    setStatus("背包里没有可以出售的作物。");
    return;
  }

  state.money += total;
  setStatus(`出售 ${sold.join("、")}，获得 $${total}。`);
  render();
}

function resetGame() {
  const shouldReset = window.confirm("确定要清空当前进度并重新开始吗？");
  if (!shouldReset) {
    return;
  }

  state.money = 50;
  state.selectedSeed = "carrot";
  Object.keys(state.inventory).forEach((key) => {
    state.inventory[key] = 0;
  });
  state.plots.forEach((plot) => {
    plot.cropKey = null;
    plot.plantedAt = 0;
    plot.readyAt = 0;
  });
  setStatus("农场已重置。");
  render();
}

function getProgress(plot) {
  if (!plot.cropKey) {
    return 0;
  }
  const duration = Math.max(plot.readyAt - plot.plantedAt, 1);
  return Math.min(1, Math.max(0, (Date.now() - plot.plantedAt) / duration));
}

function renderShop() {
  shopEl.innerHTML = Object.entries(crops)
    .map(([key, crop]) => {
      const disabled = state.money < crop.seedPrice ? "disabled" : "";
      const selected = state.selectedSeed === key ? "selected" : "";
      return `
        <article class="shop-item ${selected}">
          <span class="seed-dot" style="--dot-color: ${crop.mainColor}"></span>
          <div>
            <p class="item-name">${crop.seedName}</p>
            <p class="item-meta">$${crop.seedPrice} · ${crop.growSeconds}s成熟 · 售价$${crop.sellPrice}</p>
          </div>
          <div class="shop-actions">
            <button class="select-button" data-select="${key}">选择</button>
            <button ${disabled} data-buy="${key}">购买</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderInventory() {
  const items = [];

  Object.entries(crops).forEach(([key, crop]) => {
    items.push({
      name: crop.seedName,
      count: state.inventory[seedKey(key)],
      color: crop.mainColor,
      meta: "种子",
    });
  });

  Object.entries(crops).forEach(([key, crop]) => {
    items.push({
      name: crop.name,
      count: state.inventory[cropKey(key)],
      color: crop.deepColor,
      meta: `作物 · 售价 $${crop.sellPrice}`,
    });
  });

  const visibleItems = items.filter((item) => item.count > 0);
  if (visibleItems.length === 0) {
    inventoryEl.innerHTML = `<p class="bag-empty">背包还是空的。去商店买一些种子，开始经营农场吧。</p>`;
    return;
  }

  inventoryEl.innerHTML = visibleItems
    .map(
      (item) => `
        <article class="bag-item">
          <span class="bag-dot" style="--dot-color: ${item.color}"></span>
          <div>
            <p class="item-name">${item.name}</p>
            <p class="item-meta">${item.meta}</p>
          </div>
          <strong>x${item.count}</strong>
        </article>
      `,
    )
    .join("");
}

function renderSelectedSeed() {
  const crop = crops[state.selectedSeed];
  const count = state.inventory[seedKey(state.selectedSeed)];
  selectedSeedEl.textContent = crop.seedName;
  selectedHintEl.textContent = `背包里有 ${count} 个。购买或选择种子后，点击空农田播种。`;
}

function cropMarkup(cropKeyValue, progress, ready) {
  const crop = crops[cropKeyValue];
  const scale = 0.32 + progress * 0.68;
  const readyClass = ready ? "ready" : "";
  const percent = Math.floor(progress * 100);
  const label = ready ? `${crop.name} 可收获` : `${crop.name} ${percent}%`;

  return `
    <div
      class="crop ${cropKeyValue} ${readyClass}"
      style="--crop-main: ${crop.mainColor}; --crop-deep: ${crop.deepColor}; --scale: ${scale}"
      aria-hidden="true"
    >
      <span class="stem"></span>
      <span class="leaf leaf-a"></span>
      <span class="leaf leaf-b"></span>
      <span class="leaf leaf-c"></span>
      <span class="fruit"></span>
    </div>
    <span class="plot-label">${label}</span>
    <div class="progress-track" aria-hidden="true">
      <span class="progress-bar" style="width: ${percent}%"></span>
    </div>
  `;
}

function renderPlots() {
  plotsEl.innerHTML = state.plots
    .map((plot, index) => {
      const progress = getProgress(plot);
      const ready = plot.cropKey && progress >= 1;
      const emptyClass = plot.cropKey ? "" : "empty";
      const readyClass = ready ? "ready" : "";
      const label = plot.cropKey ? crops[plot.cropKey].name : "空地";
      const content = plot.cropKey ? cropMarkup(plot.cropKey, progress, ready) : "";

      return `
        <button class="plot ${emptyClass} ${readyClass}" data-plot="${index}" aria-label="${label}">
          ${content}
        </button>
      `;
    })
    .join("");
}

function render() {
  moneyEl.textContent = `$${state.money}`;
  renderSelectedSeed();
  renderShop();
  renderInventory();
  renderPlots();
}

function bindEvents() {
  shopEl.addEventListener("click", (event) => {
    const selectButton = event.target.closest("[data-select]");
    if (selectButton) {
      selectSeed(selectButton.dataset.select);
      return;
    }

    const button = event.target.closest("[data-buy]");
    if (button) {
      buySeed(button.dataset.buy);
    }
  });

  plotsEl.addEventListener("click", (event) => {
    const button = event.target.closest("[data-plot]");
    if (button) {
      handlePlotClick(Number(button.dataset.plot));
    }
  });

  selectedSeedEl.addEventListener("click", () => {
    selectSeed(state.selectedSeed);
  });

  sellAllEl.addEventListener("click", sellAllCrops);
  resetGameEl.addEventListener("click", resetGame);

  document.addEventListener("keydown", (event) => {
    const cropKeys = Object.keys(crops);
    const index = Number(event.key) - 1;
    if (cropKeys[index]) {
      selectSeed(cropKeys[index]);
    }
  });
}

initInventory();
bindEvents();
render();
window.setInterval(renderPlots, 500);
