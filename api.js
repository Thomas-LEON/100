// ============================================================
// frontend/api.js — Backend API Client
// Connects the HTML frontend to the FastAPI backend
// Include this in all HTML pages: <script src="api.js"></script>
// ============================================================

const API_BASE = "http://localhost:8000";

// ── Token Management ────────────────────────────────────────────────────
const Auth = {
  setToken: (token) => localStorage.setItem("anp_token", token),
  getToken: () => localStorage.getItem("anp_token"),
  removeToken: () => localStorage.removeItem("anp_token"),
  setUser: (user) => localStorage.setItem("anp_user", JSON.stringify(user)),
  getUser: () => {
    const u = localStorage.getItem("anp_user");
    return u ? JSON.parse(u) : null;
  },
  removeUser: () => localStorage.removeItem("anp_user"),
  isLoggedIn: () => !!localStorage.getItem("anp_token"),
  logout: () => {
    Auth.removeToken();
    Auth.removeUser();
    window.location.href = "/login.html";
  },
};

// ── Core HTTP Fetch Wrapper ─────────────────────────────────────────────
async function apiFetch(endpoint, options = {}) {
  const token = Auth.getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    Auth.logout();
    return;
  }

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.detail || `HTTP error ${res.status}`);
  }

  return data;
}

// ── AUTH API ────────────────────────────────────────────────────────────
const AuthAPI = {
  async login(username, password) {
    const data = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    Auth.setToken(data.access_token);
    Auth.setUser(data.user);
    return data;
  },

  async loginSSO() {
    const data = await apiFetch("/api/auth/sso", { method: "POST" });
    Auth.setToken(data.access_token);
    Auth.setUser(data.user);
    return data;
  },

  async register(payload) {
    return apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async me() {
    return apiFetch("/api/auth/me");
  },
};

// ── REPORTS API ─────────────────────────────────────────────────────────
const ReportsAPI = {
  async check(companyName, domain = null) {
    return apiFetch("/api/reports/check", {
      method: "POST",
      body: JSON.stringify({ company_name: companyName, domain }),
    });
  },

  async generate(companyName, domain = null, forceRegenerate = false) {
    return apiFetch("/api/reports/generate", {
      method: "POST",
      body: JSON.stringify({
        company_name: companyName,
        domain,
        force_regenerate: forceRegenerate,
      }),
    });
  },

  async list({ page = 1, pageSize = 10, status = null, risk = null } = {}) {
    const params = new URLSearchParams({ page, page_size: pageSize });
    if (status) params.append("status", status);
    if (risk) params.append("risk", risk);
    return apiFetch(`/api/reports/?${params}`);
  },

  async get(reportId) {
    return apiFetch(`/api/reports/${reportId}`);
  },

  pdfUrl(reportId) {
    return `${API_BASE}/api/reports/${reportId}/pdf?token=${Auth.getToken()}`;
  },

  async downloadPdf(reportId, filename) {
    const token = Auth.getToken();
    const res = await fetch(`${API_BASE}/api/reports/${reportId}/pdf`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("PDF download failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || `ANP_Report_${reportId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  },
};

// ── DASHBOARD API ────────────────────────────────────────────────────────
const DashboardAPI = {
  async getStats() {
    return apiFetch("/api/dashboard/stats");
  },
};

// ── USERS API ────────────────────────────────────────────────────────────
const UsersAPI = {
  async getProfile() {
    return apiFetch("/api/users/me");
  },

  async updateProfile(payload) {
    return apiFetch("/api/users/me", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async getCredits() {
    return apiFetch("/api/users/me/credits");
  },

  async getTransactions() {
    return apiFetch("/api/users/me/transactions");
  },

  async requestCredits(amountRequested, justification) {
    return apiFetch("/api/users/me/credit-requests", {
      method: "POST",
      body: JSON.stringify({ amount_requested: amountRequested, justification }),
    });
  },

  async getMyCreditRequests() {
    return apiFetch("/api/users/me/credit-requests");
  },
};

// ── ADMIN API ────────────────────────────────────────────────────────────
const AdminAPI = {
  async listUsers() {
    return apiFetch("/api/admin/users");
  },

  async updateUser(userId, payload) {
    return apiFetch(`/api/admin/users/${userId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async approveUser(userId) {
    return AdminAPI.updateUser(userId, { is_approved: true });
  },

  async listCreditRequests() {
    return apiFetch("/api/admin/credit-requests");
  },

  async reviewCreditRequest(requestId, approved, adminNote = "") {
    return apiFetch(`/api/admin/credit-requests/${requestId}`, {
      method: "PUT",
      body: JSON.stringify({ approved, admin_note: adminNote }),
    });
  },

  async getAuditTrail(page = 1, pageSize = 10) {
    const params = new URLSearchParams({ page, page_size: pageSize });
    return apiFetch(`/api/admin/audit-trail?${params}`);
  },
};

// ── UI Helpers ────────────────────────────────────────────────────────────
const UI = {
  // Update credits chip in topbar
  updateCreditsChip(credits) {
    const chip = document.getElementById("credits-display");
    const count = document.getElementById("credits-count");
    if (!chip || !count) return;
    count.textContent = credits;
    chip.className = "credits-chip";
    if (credits === 0) chip.classList.add("empty");
    else if (credits < 20) chip.classList.add("low");
  },

  // Populate user avatar / name
  populateUserInfo(user) {
    if (!user) return;
    const initials = `${user.first_name[0]}${user.last_name[0]}`.toUpperCase();
    document.querySelectorAll(".user-avatar, .sidebar-user-avatar").forEach((el) => {
      el.textContent = initials;
    });
    document.querySelectorAll(".sidebar-user-name").forEach((el) => {
      el.textContent = `${user.first_name} ${user.last_name}`;
    });
    document.querySelectorAll(".sidebar-user-role").forEach((el) => {
      el.textContent = `${user.job_title || "User"} · ${user.business_unit?.split(" ")[0] || ""}`;
    });
    UI.updateCreditsChip(user.credits);
  },

  showToast(message, type = "success") {
    const toast = document.getElementById("save-toast") || _createToast();
    toast.textContent = (type === "success" ? "✓ " : "⚠ ") + message;
    toast.style.display = "block";
    toast.style.background = type === "success" ? "#2D2D2D" : "#D32F2F";
    setTimeout(() => { toast.style.display = "none"; }, 4000);
  },

  showError(message) {
    UI.showToast(message, "error");
  },

  getRiskBadgeHTML(score, riskLevel) {
    const classes = { HIGH: "high", MEDIUM: "medium", LOW: "low" };
    const cls = classes[riskLevel?.toUpperCase()] || "pending";
    return `<span class="vuln-badge ${cls}"><span class="vuln-dot"></span>${riskLevel?.toUpperCase() || "—"} · ${score ?? "—"}</span>`;
  },

  getStatusBadgeHTML(status) {
    const classes = {
      completed: "completed",
      pending: "pending",
      processing: "processing",
      failed: "failed",
    };
    const cls = classes[status?.toLowerCase()] || "pending";
    const label = status?.charAt(0).toUpperCase() + status?.slice(1) || "Unknown";
    return `<span class="status-badge ${cls}"><span class="status-pulse"></span>${label}</span>`;
  },
};

function _createToast() {
  const el = document.createElement("div");
  el.id = "save-toast";
  el.style.cssText =
    "position:fixed;bottom:24px;right:24px;background:#2D2D2D;color:white;" +
    "padding:12px 20px;border-radius:10px;font-size:0.875rem;font-weight:500;" +
    "box-shadow:0 8px 40px rgba(0,0,0,0.14);z-index:9999;display:none;" +
    "font-family:'Outfit',sans-serif;";
  document.body.appendChild(el);
  return el;
}

// ── Auto-init: protect pages + populate user info ────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  const publicPages = ["login.html", "register.html", "/", ""];
  const currentPage = window.location.pathname.split("/").pop();

  if (!publicPages.includes(currentPage)) {
    if (!Auth.isLoggedIn()) {
      window.location.href = "/login.html";
      return;
    }
    // Populate UI from cached user
    const cached = Auth.getUser();
    if (cached) UI.populateUserInfo(cached);

    // Refresh from API in background
    AuthAPI.me()
      .then((user) => {
        Auth.setUser(user);
        UI.populateUserInfo(user);
      })
      .catch(() => Auth.logout());
  }
});

// ── Expose globals ────────────────────────────────────────────────────────
window.ANP = { Auth, AuthAPI, ReportsAPI, DashboardAPI, UsersAPI, AdminAPI, UI };
