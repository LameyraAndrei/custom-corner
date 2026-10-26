/* Custom Corner — Product Design Studio
 * A design is represented purely as data: an array of text/image elements
 * (position, size, rotation, styling) per print side. The canvas is just a
 * renderer for that state, so the exact same state object is what gets
 * persisted to (and reconstructed from) the server.
 */
(function () {
  "use strict";

  const CFG = window.CC_CONFIG;
  const canvas = document.getElementById("design-canvas");
  const ctx = canvas.getContext("2d");
  const CW = canvas.width, CH = canvas.height;

  const PRINT_AREAS = {
    tshirt: { x: 190, y: 185, w: 180, h: 230 },
    mug: { x: 205, y: 195, w: 150, h: 170 },
    tote: { x: 175, y: 260, w: 210, h: 200 },
    keychain: { x: 200, y: 205, w: 160, h: 200 },
    sticker: { x: 150, y: 170, w: 260, h: 260 },
    phonecase: { x: 195, y: 145, w: 170, h: 300 },
  };

  // ---------------------------------------------------------------- state
  let state = {
    color: CFG.initialColorName,
    colorHex: CFG.initialColorHex,
    size: CFG.initialSize,
    quantity: 1,
    side: "front",
    elements: { front: [], back: [] },
    selectedId: null,
    designId: CFG.existingDesignId || null,
    designName: CFG.existingDesignName || "",
  };

  if (CFG.existingDesignData) {
    try {
      const parsed = typeof CFG.existingDesignData === "string" ? JSON.parse(CFG.existingDesignData) : CFG.existingDesignData;
      state.elements.front = parsed.front || [];
      state.elements.back = parsed.back || [];
    } catch (e) { /* ignore malformed saved data */ }
  }

  let history = [];
  let historyIndex = -1;
  let dragMode = null; // 'move' | 'resize' | 'rotate'
  let dragData = null;
  const imageCache = {};

  // ----------------------------------------------------------- utilities
  function uid() { return "el_" + Math.random().toString(36).slice(2, 10); }

  function deepCloneElements() {
    return JSON.parse(JSON.stringify(state.elements));
  }

  function pushHistory() {
    history = history.slice(0, historyIndex + 1);
    history.push(deepCloneElements());
    if (history.length > 60) history.shift();
    historyIndex = history.length - 1;
    updateUndoRedoButtons();
  }

  function undo() {
    if (historyIndex <= 0) return;
    historyIndex--;
    state.elements = JSON.parse(JSON.stringify(history[historyIndex]));
    state.selectedId = null;
    render(); updateElementPanel(); updatePriceSummary(); updateUndoRedoButtons();
  }

  function redo() {
    if (historyIndex >= history.length - 1) return;
    historyIndex++;
    state.elements = JSON.parse(JSON.stringify(history[historyIndex]));
    state.selectedId = null;
    render(); updateElementPanel(); updatePriceSummary(); updateUndoRedoButtons();
  }

  function updateUndoRedoButtons() {
    document.getElementById("btn-undo").disabled = historyIndex <= 0;
    document.getElementById("btn-redo").disabled = historyIndex >= history.length - 1;
    document.getElementById("btn-undo").style.opacity = historyIndex <= 0 ? 0.4 : 1;
    document.getElementById("btn-redo").style.opacity = historyIndex >= history.length - 1 ? 0.4 : 1;
  }

  function currentElements() { return state.elements[state.side]; }

  function findElement(id) { return currentElements().find((e) => e.id === id); }

  function selectedElement() { return state.selectedId ? findElement(state.selectedId) : null; }

  function pesoFormat(n) {
    n = Math.round(n * 100) / 100;
    const s = n.toLocaleString("en-PH", { minimumFractionDigits: n % 1 === 0 ? 0 : 2, maximumFractionDigits: 2 });
    return "₱" + s;
  }

  function toast(msg) {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.style.opacity = 1;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { el.style.opacity = 0; }, 2600);
  }

  function roundRectPath(c, x, y, w, h, r) {
    if (c.roundRect) { c.beginPath(); c.roundRect(x, y, w, h, r); return; }
    c.beginPath();
    c.moveTo(x + r, y);
    c.arcTo(x + w, y, x + w, y + h, r);
    c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r);
    c.arcTo(x, y, x + w, y, r);
    c.closePath();
  }

  // ------------------------------------------------------- mockup shapes
  const MOCKUPS = {
    tshirt(c, color) {
      c.save();
      c.beginPath();
      c.moveTo(230, 120);
      c.quadraticCurveTo(280, 155, 330, 120);
      c.lineTo(392, 142);
      c.lineTo(452, 208);
      c.lineTo(400, 252);
      c.lineTo(410, 470);
      c.quadraticCurveTo(410, 492, 388, 492);
      c.lineTo(172, 492);
      c.quadraticCurveTo(150, 492, 150, 470);
      c.lineTo(160, 252);
      c.lineTo(108, 208);
      c.lineTo(168, 142);
      c.closePath();
      c.fillStyle = color; c.fill();
      c.lineWidth = 2; c.strokeStyle = "rgba(32,27,20,0.18)"; c.stroke();
      c.beginPath();
      c.moveTo(252, 123); c.quadraticCurveTo(280, 148, 308, 123);
      c.lineWidth = 3; c.strokeStyle = "rgba(32,27,20,0.22)"; c.stroke();
      c.restore();
    },
    mug(c, color) {
      c.save();
      c.beginPath();
      c.moveTo(170, 160); c.lineTo(390, 160); c.lineTo(375, 430);
      c.quadraticCurveTo(375, 452, 353, 452); c.lineTo(207, 452);
      c.quadraticCurveTo(185, 452, 185, 430); c.closePath();
      c.fillStyle = color; c.fill();
      c.lineWidth = 2; c.strokeStyle = "rgba(32,27,20,0.18)"; c.stroke();
      c.beginPath();
      c.moveTo(392, 220); c.bezierCurveTo(472, 222, 472, 360, 392, 368);
      c.lineWidth = 24; c.strokeStyle = color; c.lineCap = "round"; c.stroke();
      c.lineWidth = 2; c.strokeStyle = "rgba(32,27,20,0.18)"; c.stroke();
      c.beginPath();
      c.ellipse(280, 160, 110, 14, 0, 0, Math.PI * 2);
      c.fillStyle = "rgba(32,27,20,0.06)"; c.fill();
      c.strokeStyle = "rgba(32,27,20,0.18)"; c.stroke();
      c.restore();
    },
    tote(c, color) {
      c.save();
      c.beginPath();
      c.moveTo(160, 220); c.lineTo(400, 220); c.lineTo(420, 480);
      c.quadraticCurveTo(420, 502, 398, 502); c.lineTo(162, 502);
      c.quadraticCurveTo(140, 502, 140, 480); c.closePath();
      c.fillStyle = color; c.fill();
      c.lineWidth = 2; c.strokeStyle = "rgba(32,27,20,0.18)"; c.stroke();
      c.beginPath();
      c.moveTo(210, 222); c.bezierCurveTo(210, 128, 242, 96, 280, 96);
      c.bezierCurveTo(318, 96, 350, 128, 350, 222);
      c.lineWidth = 15; c.strokeStyle = "rgba(32,27,20,0.22)"; c.stroke();
      c.lineWidth = 10; c.strokeStyle = color; c.stroke();
      c.restore();
    },
    keychain(c, color) {
      c.save();
      c.beginPath(); c.arc(280, 178, 22, 0, Math.PI * 2);
      c.lineWidth = 7; c.strokeStyle = "rgba(120,88,58,0.85)"; c.stroke();
      roundRectPath(c, 190, 200, 180, 250, 26);
      c.fillStyle = color; c.fill();
      c.lineWidth = 2; c.strokeStyle = "rgba(32,27,20,0.18)"; c.stroke();
      c.beginPath(); c.arc(280, 230, 13, 0, Math.PI * 2);
      c.fillStyle = "#ffffff"; c.fill();
      c.strokeStyle = "rgba(32,27,20,0.25)"; c.stroke();
      c.restore();
    },
    sticker(c, color) {
      c.save();
      c.beginPath(); c.arc(280, 300, 185, 0, Math.PI * 2);
      c.fillStyle = "#ffffff"; c.fill();
      c.lineWidth = 3; c.strokeStyle = "rgba(32,27,20,0.12)"; c.stroke();
      c.beginPath(); c.arc(280, 300, 172, 0, Math.PI * 2);
      c.setLineDash([7, 7]); c.strokeStyle = "rgba(32,27,20,0.22)"; c.stroke();
      c.setLineDash([]);
      c.restore();
    },
    phonecase(c, color) {
      c.save();
      roundRectPath(c, 190, 100, 180, 380, 42);
      c.fillStyle = color; c.fill();
      c.lineWidth = 2; c.strokeStyle = "rgba(32,27,20,0.18)"; c.stroke();
      roundRectPath(c, 205, 122, 66, 86, 16);
      c.fillStyle = "rgba(32,27,20,0.28)"; c.fill();
      c.beginPath(); c.arc(224, 146, 13, 0, Math.PI * 2); c.fillStyle = "rgba(32,27,20,0.45)"; c.fill();
      c.beginPath(); c.arc(252, 165, 9, 0, Math.PI * 2); c.fill();
      c.restore();
    },
  };

  function drawMockup() {
    ctx.clearRect(0, 0, CW, CH);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, CW, CH);
    const fn = MOCKUPS[CFG.product.mockupShape] || MOCKUPS.tshirt;
    fn(ctx, state.colorHex);
    // subtle print-area guide
    const area = PRINT_AREAS[CFG.product.mockupShape] || PRINT_AREAS.tshirt;
    ctx.save();
    ctx.strokeStyle = "rgba(120,88,58,0.28)";
    ctx.setLineDash([5, 5]);
    ctx.lineWidth = 1;
    ctx.strokeRect(area.x, area.y, area.w, area.h);
    ctx.setLineDash([]);
    ctx.restore();
  }

  function getImage(src) {
    if (imageCache[src] && imageCache[src].complete) return imageCache[src];
    if (!imageCache[src]) {
      const img = new Image();
      img.onload = () => render();
      img.src = src;
      imageCache[src] = img;
    }
    return imageCache[src].complete ? imageCache[src] : null;
  }

  function drawElement(el) {
    const cx = el.x + el.w / 2, cy = el.y + el.h / 2;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((el.rotation || 0) * Math.PI / 180);

    if (el.type === "text") {
      let fontStr = "";
      if (el.italic) fontStr += "italic ";
      if (el.bold) fontStr += "700 "; else fontStr += "500 ";
      fontStr += (el.size || 32) + "px \"" + (el.font || "Plus Jakarta Sans") + "\", sans-serif";
      ctx.font = fontStr;
      ctx.fillStyle = el.color || "#2B2623";
      ctx.textBaseline = "middle";
      ctx.textAlign = el.align || "center";
      let drawX = 0;
      if (el.align === "left") drawX = -el.w / 2;
      else if (el.align === "right") drawX = el.w / 2;
      ctx.fillText(el.text || "", drawX, 0);
    } else if (el.type === "image") {
      const img = getImage(el.src);
      if (img) {
        ctx.drawImage(img, -el.w / 2, -el.h / 2, el.w, el.h);
      } else {
        ctx.fillStyle = "rgba(0,0,0,0.08)";
        ctx.fillRect(-el.w / 2, -el.h / 2, el.w, el.h);
      }
    }
    ctx.restore();

    if (el.id === state.selectedId) drawSelection(el);
  }

  function localToCanvas(el, lx, ly) {
    const cx = el.x + el.w / 2, cy = el.y + el.h / 2;
    const rad = (el.rotation || 0) * Math.PI / 180;
    const cosr = Math.cos(rad), sinr = Math.sin(rad);
    return { x: cx + lx * cosr - ly * sinr, y: cy + lx * sinr + ly * cosr };
  }

  function drawSelection(el) {
    const cx = el.x + el.w / 2, cy = el.y + el.h / 2;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((el.rotation || 0) * Math.PI / 180);
    ctx.strokeStyle = "#78583a";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 3]);
    ctx.strokeRect(-el.w / 2, -el.h / 2, el.w, el.h);
    ctx.setLineDash([]);
    ctx.restore();

    // resize handle (bottom-right)
    const rh = localToCanvas(el, el.w / 2, el.h / 2);
    drawHandle(rh.x, rh.y, "#2B2623");
    // rotate handle (above top-center)
    const rot = localToCanvas(el, 0, -el.h / 2 - 26);
    drawHandle(rot.x, rot.y, "#78583a");
    ctx.save();
    ctx.strokeStyle = "rgba(120,88,58,0.6)";
    ctx.lineWidth = 1;
    const top = localToCanvas(el, 0, -el.h / 2);
    ctx.beginPath(); ctx.moveTo(top.x, top.y); ctx.lineTo(rot.x, rot.y); ctx.stroke();
    ctx.restore();
  }

  function drawHandle(x, y, color) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, 7, 0, Math.PI * 2);
    ctx.fillStyle = "#fff";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = color;
    ctx.stroke();
    ctx.restore();
  }

  function render() {
    drawMockup();
    currentElements().forEach(drawElement);
  }

  // -------------------------------------------------------- pointer math
  function getPos(evt) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = CW / rect.width, scaleY = CH / rect.height;
    const clientX = evt.touches ? evt.touches[0].clientX : evt.clientX;
    const clientY = evt.touches ? evt.touches[0].clientY : evt.clientY;
    return { x: (clientX - rect.left) * scaleX, y: (clientY - rect.top) * scaleY };
  }

  function pointInElement(el, px, py) {
    const cx = el.x + el.w / 2, cy = el.y + el.h / 2;
    const rad = -(el.rotation || 0) * Math.PI / 180;
    const dx = px - cx, dy = py - cy;
    const lx = dx * Math.cos(rad) - dy * Math.sin(rad);
    const ly = dx * Math.sin(rad) + dy * Math.cos(rad);
    return Math.abs(lx) <= el.w / 2 && Math.abs(ly) <= el.h / 2;
  }

  function dist(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }

  function onPointerDown(evt) {
    evt.preventDefault();
    const pos = getPos(evt);
    const sel = selectedElement();

    if (sel) {
      const rh = localToCanvas(sel, sel.w / 2, sel.h / 2);
      const rot = localToCanvas(sel, 0, -sel.h / 2 - 26);
      if (dist(pos, rh) <= 14) {
        dragMode = "resize"; dragData = { startPos: pos, startEl: { ...sel } };
        return;
      }
      if (dist(pos, rot) <= 14) {
        dragMode = "rotate"; dragData = { startEl: { ...sel } };
        return;
      }
    }

    const els = currentElements();
    for (let i = els.length - 1; i >= 0; i--) {
      if (pointInElement(els[i], pos.x, pos.y)) {
        state.selectedId = els[i].id;
        dragMode = "move";
        dragData = { offsetX: pos.x - els[i].x, offsetY: pos.y - els[i].y };
        render(); updateElementPanel();
        return;
      }
    }
    state.selectedId = null;
    render(); updateElementPanel();
  }

  function onPointerMove(evt) {
    if (!dragMode) return;
    evt.preventDefault();
    const pos = getPos(evt);
    const el = selectedElement();
    if (!el) return;

    if (dragMode === "move") {
      el.x = pos.x - dragData.offsetX;
      el.y = pos.y - dragData.offsetY;
    } else if (dragMode === "resize") {
      const cx = el.x + el.w / 2, cy = el.y + el.h / 2;
      const rad = -(el.rotation || 0) * Math.PI / 180;
      const dx = pos.x - cx, dy = pos.y - cy;
      const lx = dx * Math.cos(rad) - dy * Math.sin(rad);
      const ly = dx * Math.sin(rad) + dy * Math.cos(rad);
      const newW = Math.max(24, Math.abs(lx) * 2);
      const newH = Math.max(24, Math.abs(ly) * 2);
      el.x = cx - newW / 2; el.y = cy - newH / 2;
      el.w = newW; el.h = newH;
    } else if (dragMode === "rotate") {
      const cx = el.x + el.w / 2, cy = el.y + el.h / 2;
      let angle = Math.atan2(pos.y - cy, pos.x - cx) * 180 / Math.PI + 90;
      el.rotation = Math.round(angle);
      document.getElementById("prop-rotation").value = ((el.rotation + 180) % 360) - 180;
      document.getElementById("prop-rotation-val").textContent = document.getElementById("prop-rotation").value;
    }
    render();
  }

  function onPointerUp() {
    if (dragMode) { pushHistory(); updatePriceSummary(); }
    dragMode = null; dragData = null;
  }

  canvas.addEventListener("mousedown", onPointerDown);
  window.addEventListener("mousemove", onPointerMove);
  window.addEventListener("mouseup", onPointerUp);
  canvas.addEventListener("touchstart", onPointerDown, { passive: false });
  window.addEventListener("touchmove", onPointerMove, { passive: false });
  window.addEventListener("touchend", onPointerUp);

  // ------------------------------------------------------------ side tabs
  document.querySelectorAll(".side-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.side = btn.dataset.sideTab;
      state.selectedId = null;
      document.querySelectorAll(".side-tab").forEach((b) => {
        b.classList.toggle("bg-primary", b === btn);
        b.classList.toggle("text-on-primary", b === btn);
        b.classList.toggle("text-on-surface-variant", b !== btn);
      });
      render(); updateElementPanel();
    });
  });

  // --------------------------------------------------------- color/size
  document.querySelectorAll(".color-swatch").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.colorHex = btn.dataset.colorHex;
      state.color = btn.dataset.colorName;
      document.querySelectorAll(".color-swatch").forEach((b) => {
        b.classList.toggle("border-primary", b === btn);
        b.classList.toggle("border-outline-variant", b !== btn);
      });
      document.getElementById("selected-color-name").textContent = state.color;
      render();
    });
  });

  document.querySelectorAll(".size-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.size = btn.dataset.size;
      document.querySelectorAll(".size-chip").forEach((b) => {
        const active = b === btn;
        b.classList.toggle("border-primary", active);
        b.classList.toggle("bg-surface", active);
        b.classList.toggle("text-primary", active);
        b.classList.toggle("font-bold", active);
        b.classList.toggle("border-outline-variant", !active);
        b.classList.toggle("text-on-surface", !active);
      });
    });
  });

  const qtyInput = document.getElementById("qty-input");
  document.getElementById("qty-minus").addEventListener("click", () => {
    qtyInput.value = Math.max(1, parseInt(qtyInput.value || "1", 10) - 1);
    state.quantity = parseInt(qtyInput.value, 10); updatePriceSummary();
  });
  document.getElementById("qty-plus").addEventListener("click", () => {
    qtyInput.value = Math.min(99, parseInt(qtyInput.value || "1", 10) + 1);
    state.quantity = parseInt(qtyInput.value, 10); updatePriceSummary();
  });
  qtyInput.addEventListener("input", () => {
    let v = parseInt(qtyInput.value || "1", 10);
    if (isNaN(v) || v < 1) v = 1; if (v > 99) v = 99;
    state.quantity = v; updatePriceSummary();
  });

  // ------------------------------------------------------------ add text
  document.getElementById("btn-add-text").addEventListener("click", () => {
    const area = PRINT_AREAS[CFG.product.mockupShape] || PRINT_AREAS.tshirt;
    const el = {
      id: uid(), type: "text", text: "Your Text",
      x: area.x + area.w / 2 - 90, y: area.y + area.h / 2 - 20,
      w: 180, h: 40, rotation: 0,
      font: "Playfair Display", size: 32, color: "#2B2623",
      bold: false, italic: false, align: "center",
    };
    currentElements().push(el);
    state.selectedId = el.id;
    pushHistory(); render(); updateElementPanel(); updatePriceSummary();
    document.getElementById("prop-text").focus();
  });

  // ----------------------------------------------------------- add image
  const fileInput = document.getElementById("image-file-input");
  document.getElementById("btn-add-image").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", async () => {
    const errEl = document.getElementById("upload-error");
    errEl.classList.add("hidden");
    const file = fileInput.files[0];
    if (!file) return;
    if (file.size > 6 * 1024 * 1024) {
      errEl.textContent = "Image is too large (max 6MB).";
      errEl.classList.remove("hidden");
      return;
    }
    const fd = new FormData();
    fd.append("image", file);
    try {
      const res = await fetch(CFG.uploadImageUrl, { method: "POST", body: fd });
      const data = await res.json();
      if (!data.ok) {
        errEl.textContent = data.error || "Upload failed.";
        errEl.classList.remove("hidden");
        return;
      }
      const img = new Image();
      img.onload = () => {
        const area = PRINT_AREAS[CFG.product.mockupShape] || PRINT_AREAS.tshirt;
        let w = img.naturalWidth, h = img.naturalHeight;
        const maxDim = Math.min(area.w, area.h) * 0.8;
        const scale = Math.min(1, maxDim / Math.max(w, h));
        w *= scale; h *= scale;
        const el = {
          id: uid(), type: "image", src: data.data_url,
          x: area.x + area.w / 2 - w / 2, y: area.y + area.h / 2 - h / 2,
          w, h, rotation: 0,
        };
        imageCache[data.data_url] = img;
        currentElements().push(el);
        state.selectedId = el.id;
        pushHistory(); render(); updateElementPanel(); updatePriceSummary();
      };
      img.src = data.data_url;
    } catch (e) {
      errEl.textContent = "Upload failed. Please try again.";
      errEl.classList.remove("hidden");
    }
    fileInput.value = "";
  });

  // -------------------------------------------------------- element panel
  const panel = document.getElementById("element-panel");
  const textProps = document.getElementById("text-props");
  const imageProps = document.getElementById("image-props");

  function updateElementPanel() {
    const el = selectedElement();
    if (!el) { panel.classList.add("hidden"); return; }
    panel.classList.remove("hidden");
    document.getElementById("prop-rotation").value = ((el.rotation + 180) % 360 + 360) % 360 - 180;
    document.getElementById("prop-rotation-val").textContent = Math.round(el.rotation % 360);

    if (el.type === "text") {
      textProps.classList.remove("hidden");
      imageProps.classList.add("hidden");
      document.getElementById("prop-text").value = el.text;
      document.getElementById("prop-font").value = el.font;
      document.getElementById("prop-color").value = el.color;
      document.getElementById("prop-size").value = el.size;
      document.getElementById("prop-size-val").textContent = el.size;
      document.getElementById("prop-bold").classList.toggle("active", !!el.bold);
      document.getElementById("prop-italic").classList.toggle("active", !!el.italic);
      document.querySelectorAll(".align-toggle").forEach((b) => b.classList.toggle("active", b.dataset.align === el.align));
    } else {
      textProps.classList.add("hidden");
      imageProps.classList.remove("hidden");
    }
  }

  document.getElementById("prop-text").addEventListener("input", (e) => {
    const el = selectedElement(); if (!el) return;
    el.text = e.target.value; render();
  });
  document.getElementById("prop-text").addEventListener("change", () => pushHistory());
  document.getElementById("prop-font").addEventListener("change", (e) => {
    const el = selectedElement(); if (!el) return;
    el.font = e.target.value; render(); pushHistory();
  });
  document.getElementById("prop-color").addEventListener("input", (e) => {
    const el = selectedElement(); if (!el) return;
    el.color = e.target.value; render();
  });
  document.getElementById("prop-color").addEventListener("change", () => pushHistory());
  document.getElementById("prop-size").addEventListener("input", (e) => {
    const el = selectedElement(); if (!el) return;
    el.size = parseInt(e.target.value, 10);
    document.getElementById("prop-size-val").textContent = el.size;
    render();
  });
  document.getElementById("prop-size").addEventListener("change", () => pushHistory());
  document.getElementById("prop-rotation").addEventListener("input", (e) => {
    const el = selectedElement(); if (!el) return;
    el.rotation = parseInt(e.target.value, 10);
    document.getElementById("prop-rotation-val").textContent = el.rotation;
    render();
  });
  document.getElementById("prop-rotation").addEventListener("change", () => pushHistory());
  document.getElementById("prop-bold").addEventListener("click", (e) => {
    const el = selectedElement(); if (!el) return;
    el.bold = !el.bold; e.currentTarget.classList.toggle("active", el.bold);
    render(); pushHistory();
  });
  document.getElementById("prop-italic").addEventListener("click", (e) => {
    const el = selectedElement(); if (!el) return;
    el.italic = !el.italic; e.currentTarget.classList.toggle("active", el.italic);
    render(); pushHistory();
  });
  document.querySelectorAll(".align-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const el = selectedElement(); if (!el) return;
      el.align = btn.dataset.align;
      document.querySelectorAll(".align-toggle").forEach((b) => b.classList.toggle("active", b === btn));
      render(); pushHistory();
    });
  });

  function deleteSelected() {
    if (!state.selectedId) return;
    const arr = currentElements();
    const idx = arr.findIndex((e) => e.id === state.selectedId);
    if (idx >= 0) arr.splice(idx, 1);
    state.selectedId = null;
    render(); updateElementPanel(); updatePriceSummary(); pushHistory();
  }
  document.getElementById("btn-delete-element").addEventListener("click", deleteSelected);
  document.getElementById("btn-delete-selected").addEventListener("click", deleteSelected);

  document.getElementById("btn-undo").addEventListener("click", undo);
  document.getElementById("btn-redo").addEventListener("click", redo);
  document.getElementById("btn-reset").addEventListener("click", () => {
    if (!confirm("Reset this design? All elements on both sides will be removed. This cannot be undone.")) return;
    state.elements = { front: [], back: [] };
    state.selectedId = null;
    render(); updateElementPanel(); updatePriceSummary(); pushHistory();
  });

  // ------------------------------------------------------- price summary
  function computeCustomizationFee() {
    let fee = 0;
    ["front", "back"].forEach((side) => {
      state.elements[side].forEach((el) => {
        fee += el.type === "text" ? 30 : 70;
      });
    });
    return fee;
  }

  function updatePriceSummary() {
    const fee = computeCustomizationFee();
    const perUnit = CFG.product.basePrice + fee;
    document.getElementById("price-base").textContent = pesoFormat(CFG.product.basePrice);
    document.getElementById("price-custom").textContent = pesoFormat(fee);
    document.getElementById("price-qty").textContent = "× " + state.quantity;
    document.getElementById("price-total").textContent = pesoFormat(perUnit * state.quantity);
  }

  // ------------------------------------------------------------ save/cart
  function buildDesignPayload() {
    return {
      design_id: state.designId,
      product_id: CFG.product.id,
      name: state.designName || (CFG.product.name + " — Custom Design"),
      color: state.color,
      size: state.size,
      design_data: state.elements,
      preview_image: canvas.toDataURL("image/png"),
    };
  }

  async function saveDesign(showToastMsg) {
    if (!CFG.isLoggedIn) {
      window.location.href = CFG.loginUrl + "?next=" + encodeURIComponent(window.location.pathname + window.location.search);
      return null;
    }
    const payload = buildDesignPayload();
    const res = await fetch(CFG.saveDesignUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.ok) {
      state.designId = data.design_id;
      if (showToastMsg) toast("Design saved!");
    } else {
      toast(data.error || "Could not save design.");
    }
    return data;
  }

  document.getElementById("btn-save-design").addEventListener("click", () => saveDesign(true));

  document.getElementById("btn-add-to-cart").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    if (!CFG.isLoggedIn) {
      window.location.href = CFG.loginUrl + "?next=" + encodeURIComponent(window.location.pathname + window.location.search);
      return;
    }
    btn.disabled = true;
    btn.textContent = "Adding...";
    const saved = await saveDesign(false);
    if (!saved || !saved.ok) {
      btn.disabled = false;
      btn.innerHTML = '<span class="material-symbols-outlined text-[17px]">shopping_bag</span> Add to Cart';
      return;
    }
    const res = await fetch(CFG.addToCartUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_id: CFG.product.id,
        design_id: saved.design_id,
        color: state.color,
        size: state.size,
        quantity: state.quantity,
        preview_image: saved.preview_image,
      }),
    });
    const data = await res.json();
    if (data.ok) {
      toast("Added to cart!");
      setTimeout(() => { window.location.href = CFG.cartUrl; }, 500);
    } else {
      toast(data.error || "Could not add to cart.");
      btn.disabled = false;
      btn.innerHTML = '<span class="material-symbols-outlined text-[17px]">shopping_bag</span> Add to Cart';
    }
  });

  // --------------------------------------------------------------- init
  (function init() {
    // preload any images from an existing saved design
    ["front", "back"].forEach((side) => {
      state.elements[side].forEach((el) => { if (el.type === "image") getImage(el.src); });
    });
    render();
    updateElementPanel();
    updatePriceSummary();
    pushHistory();
  })();
})();
