// Calls go to /api/* on the same host (the gateway / ALB routes them).
const Api = {
  token: () => localStorage.getItem("token"),
  user: () => JSON.parse(localStorage.getItem("user") || "null"),

  saveSession(data) {
    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify({ email: data.email, name: data.name }));
  },

  logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "index.html";
  },

  async call(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    if (Api.token()) headers.Authorization = `Bearer ${Api.token()}`;
    const resp = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
    let data = {};
    try { data = await resp.json(); } catch (e) { /* empty body */ }
    if (resp.status === 401 && Api.token() && !path.startsWith("/api/auth")) {
      Api.logout(); // token expired
    }
    if (!resp.ok) throw new Error(data.error || `Request failed (${resp.status})`);
    return data;
  },
};

function showMsg(el, text, type) { el.textContent = text; el.className = `msg show ${type}`; }
function hideMsg(el) { el.className = "msg"; }
const gbp = (n) => new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(n);