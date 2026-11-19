export function fmtNum(val) {
  if (val === null || val === undefined || val === "") return "-";
  const n = Number(val);
  if (Number.isNaN(n)) return String(val);
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, "");
}

export function fmtArea(val) {
  if (val === null || val === undefined || val === "") return "0";
  const n = Number(val);
  if (Number.isNaN(n)) return String(val);
  return n.toFixed(2).replace(/\.?0+$/, "");
}

export function getTodayIso() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
