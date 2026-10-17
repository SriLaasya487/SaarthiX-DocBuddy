// DB-034: count tablets and guess their colours from a photo, entirely on the phone. Simple and honest:
// it finds blobs that differ from the background. Results are CHECKED against the schedule on the server, never trusted blindly.
const PALETTE = { white: [235, 235, 235], yellow: [235, 210, 60], pink: [235, 150, 170], red: [200, 40, 40], orange: [235, 130, 40],
  blue: [60, 100, 200], green: [60, 160, 80], brown: [130, 85, 50] };
const nearest = ([r, g, b]) => Object.entries(PALETTE).sort((a, c) => d2(a[1], [r, g, b]) - d2(c[1], [r, g, b]))[0][0];
const d2 = (a, b) => (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2;

export async function analyse(file) {
  const bmp = await createImageBitmap(file);
  const W = 200, H = Math.round((200 * bmp.height) / bmp.width);
  const cv = document.createElement("canvas"); cv.width = W; cv.height = H;
  const ctx = cv.getContext("2d", { willReadFrequently: true }); ctx.drawImage(bmp, 0, 0, W, H);
  const px = ctx.getImageData(0, 0, W, H).data;
  const at = (x, y) => { const i = (y * W + x) * 4; return [px[i], px[i + 1], px[i + 2]]; };
  const border = []; for (let x = 0; x < W; x += 4) { border.push(at(x, 0), at(x, H - 1)); } for (let y = 0; y < H; y += 4) { border.push(at(0, y), at(W - 1, y)); }
  const med = [0, 1, 2].map((k) => border.map((p) => p[k]).sort((a, b) => a - b)[border.length >> 1]);
  const fg = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) fg[y * W + x] = d2(at(x, y), med) > 55 * 55 ? 1 : 0;
  const seen = new Uint8Array(W * H), counts = {}; let total = 0;
  for (let s = 0; s < W * H; s++) {
    if (!fg[s] || seen[s]) continue;
    const st = [s]; seen[s] = 1; let n = 0, r = 0, g = 0, b = 0;
    while (st.length) {
      const p = st.pop(); n++; const [pr, pg, pb] = at(p % W, (p / W) | 0); r += pr; g += pg; b += pb;
      for (const q of [p - 1, p + 1, p - W, p + W]) if (q >= 0 && q < W * H && fg[q] && !seen[q]) { seen[q] = 1; st.push(q); }
    }
    if (n >= 25 && n <= W * H * 0.2) { const c = nearest([r / n, g / n, b / n]); counts[c] = (counts[c] || 0) + 1; total++; }
  }
  return { counts, total };
}
