const API_BASE = "https://staff-tracker-api-656000417392.asia-south1.run.app";

// Dashboard filters
let dashboardStartDate = "";
let dashboardEndDate = "";

let authToken = null;

// Pagination state - Calls
let callsPage = 1;
let callsPageSize = 5;
let callsTotalPages = 1;
let callsStartDate = "";
let callsEndDate = "";

// Pagination state - Payments
let paymentsPage = 1;
let paymentsPageSize = 5;
let paymentsTotalPages = 1;
let paymentsStartDate = "";
let paymentsEndDate = "";

// Pagination state - Incentives
let incPage = 1;
let incPageSize = 5;
let incTotalPages = 1;
let incStartDate = "";
let incEndDate = "";

// Pagination & filters - Manager tab
let managerPage = 1;
let managerPageSize = 5;
let managerTotalPages = 1;
let managerFilterEmployeeId = ""; // email
let managerFilterStartDate = "";
let managerFilterEndDate = "";
let managerEmployees = [];

// Pagination & filters - Manager Incentives tab
let managerIncPage = 1;
let managerIncPageSize = 5;
let managerIncTotalPages = 1;
let managerIncFilterEmployeeId = ""; // email
let managerIncFilterStartDate = "";
let managerIncFilterEndDate = "";

// ----------- UTILITIES ----------- //

function setToken(token) {
  authToken = token;
  localStorage.setItem("staffTrackerToken", token);
}

function getToken() {
  if (authToken) return authToken;
  const stored = localStorage.getItem("staffTrackerToken");
  if (stored) authToken = stored;
  return authToken;
}

async function apiRequest(path, options = {}) {
  const token = getToken();
  const headers = options.headers || {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  headers["Content-Type"] = "application/json";

  const resp = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (resp.status === 401 || resp.status === 403) {
    handleLogout(true);
    throw new Error("Not authenticated");
  }

  const text = await resp.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (e) {
    throw new Error(`Server returned invalid response (status ${resp.status}).`);
  }

  if (!resp.ok) {
    let msg = "";
    if (typeof data.detail === "string") {
      msg = data.detail;
    } else if (Array.isArray(data.detail)) {
      msg = data.detail.map((d) => d.msg || d.message || "").join("; ");
    } else if (data.message) {
      msg = data.message;
    }
    if (!msg) {
      msg = `Request failed with status ${resp.status}`;
    }
    throw new Error(msg);
  }

  return data;
}

function formatCurrency(amount) {
  if (amount == null) return "₹0";
  return (
    "₹" +
    Number(amount).toLocaleString("en-IN", { maximumFractionDigits: 2 })
  );
}

function setDefaultDashboardDates() {
  const now = new Date();
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
  const endOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0);

  const startYear = startOfMonth.getFullYear();
  const startMonth = String(startOfMonth.getMonth() + 1).padStart(2, "0");
  const startDay = String(startOfMonth.getDate()).padStart(2, "0");
  dashboardStartDate = `${startYear}-${startMonth}-${startDay}`;

  const endYear = endOfMonth.getFullYear();
  const endMonth = String(endOfMonth.getMonth() + 1).padStart(2, "0");
  const endDay = String(endOfMonth.getDate()).padStart(2, "0");
  dashboardEndDate = `${endYear}-${endMonth}-${endDay}`;

  const startInput = document.getElementById("dash-start-date");
  const endInput = document.getElementById("dash-end-date");
  if (startInput) startInput.value = dashboardStartDate;
  if (endInput) endInput.value = dashboardEndDate;
}

function setDefaultPaymentsDates() {
  const now = new Date();
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
  const endOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0);

  const startYear = startOfMonth.getFullYear();
  const startMonth = String(startOfMonth.getMonth() + 1).padStart(2, "0");
  const startDay = String(startOfMonth.getDate()).padStart(2, "0");
  paymentsStartDate = `${startYear}-${startMonth}-${startDay}`;

  const endYear = endOfMonth.getFullYear();
  const endMonth = String(endOfMonth.getMonth() + 1).padStart(2, "0");
  const endDay = String(endOfMonth.getDate()).padStart(2, "0");
  paymentsEndDate = `${endYear}-${endMonth}-${endDay}`;

  const startInput = document.getElementById("payments-start-date");
  const endInput = document.getElementById("payments-end-date");
  if (startInput) startInput.value = paymentsStartDate;
  if (endInput) endInput.value = paymentsEndDate;
}

/**
 * Update the top-right employee name/email, DOJ, and welcome text.
 * No designation/role displayed under Welcome Back.
 */
function updateEmployeeHeader(emp) {
  if (!emp) return;

  const name =
    emp.name || emp.employee_name || emp.full_name || emp.username || "";
  const email =
    emp.email || emp.employee_email || emp.employeeEmail || emp.user_email || "";
  const doj = emp.date_of_joining || emp.doj || "";

  const nameEl = document.getElementById("emp-name");
  if (nameEl) nameEl.textContent = name || "Employee Name";

  const emailEl = document.getElementById("emp-email");
  if (emailEl) emailEl.textContent = email ? `• ${email}` : "";

  const dojEl = document.getElementById("emp-doj");
  if (dojEl) dojEl.textContent = doj ? `Joined: ${doj}` : "";

  const welcomeTitleEl = document.getElementById("welcome-title");
  if (welcomeTitleEl) {
    const firstName = name ? name.split(" ")[0] : "there";
    welcomeTitleEl.textContent = `Welcome back, ${firstName}`;
  }

  // We don't show designation/role under Welcome Back – keep subtitle blank
  const welcomeSubtitleEl = document.getElementById("welcome-subtitle");
  if (welcomeSubtitleEl) {
    welcomeSubtitleEl.textContent = "";
  }
}

/**
 * Proper logout handler – clears token, switches view, and resets header.
 * fromAuthError = true when called from apiRequest due to 401/403.
 */
function handleLogout(fromAuthError = false) {
  authToken = null;
  localStorage.removeItem("staffTrackerToken");

  const portalView = document.getElementById("portal-view");
  const loginView = document.getElementById("login-view");

  if (portalView) {
    portalView.classList.remove("active");
    portalView.style.display = "none";
  }

  if (loginView) {
    loginView.style.display = "block";
    loginView.classList.add("active");
  }

  // Reset header so old data is not shown after logout
  updateEmployeeHeader({
    name: "Employee Name",
    email: "",
    date_of_joining: "",
  });

  if (!fromAuthError) {
    console.log("Logged out");
  }
}

// ----------- LOGIN / LOGOUT ----------- //

async function handleLogin(event) {
  event.preventDefault();
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const errorEl = document.getElementById("login-error");
  errorEl.textContent = "";

  try {
    const data = await apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    if (!data.token) {
      errorEl.textContent =
        data.message || "Login failed. Please check your credentials.";
      return;
    }

    setToken(data.token);

    if (data.user) {
      updateEmployeeHeader(data.user);
    }

    showPortalView();
    await loadDashboard();
    await loadCalls();
    await loadPayments();
    await loadIncentives();
  } catch (err) {
    console.error(err);
    errorEl.textContent = `Unable to login. Please try again. (${err.message})`;
  }
}

// ----------- VIEW SWITCHING ----------- //

function showPortalView() {
  const loginView = document.getElementById("login-view");
  const portalView = document.getElementById("portal-view");

  if (loginView) {
    loginView.classList.remove("active");
    loginView.style.display = "none";
  }

  if (portalView) {
    portalView.classList.add("active");
    portalView.style.display = "block";
  }
}

function switchTab(tabId) {
  document
    .querySelectorAll(".tab-content")
    .forEach((el) => el.classList.remove("active"));
  document
    .querySelectorAll(".tab-button")
    .forEach((el) => el.classList.remove("active"));

  const tab = document.getElementById(tabId);
  if (tab) {
    tab.classList.add("active");
  }
  const btn = document.querySelector(`.tab-button[data-tab="${tabId}"]`);
  if (btn) {
    btn.classList.add("active");
  }
}

// ----------- DASHBOARD LOADING ----------- //

async function loadDashboard() {
  try {
    // Build URL - only add filters if present
    let url = "/dashboard/my";
    const params = new URLSearchParams();
    if (dashboardStartDate) params.set("start_date", dashboardStartDate);
    if (dashboardEndDate) params.set("end_date", dashboardEndDate);
    if ([...params].length > 0) {
      url += `?${params.toString()}`;
    }

    const data = await apiRequest(url);

    const periodEl = document.getElementById("dashboard-period");
    if (periodEl) periodEl.textContent = data.period || "";

    // Employee object from backend
    const emp = data.employee || data.user || {};
    updateEmployeeHeader(emp);

    console.log("EMPLOYEE OBJ (for manager check):", emp);

    // Motivational quote
    const quotes = [
      "Every call today builds your pipeline for tomorrow.",
      "Consistent follow-ups turn prospects into customers.",
      "Small efforts daily create big monthly numbers.",
      "You don't have to be extreme, just consistent.",
      "Each demo is one step closer to a closed deal.",
    ];
    const randomQuote = quotes[Math.floor(Math.random() * quotes.length)];
    const quoteEl = document.getElementById("welcome-quote");
    if (quoteEl) quoteEl.textContent = randomQuote;

    // ---- DASHBOARD CARDS ---- //
    const calls = data.calls || {};

    const elTotalCalls = document.getElementById("dash-total-calls");
    if (elTotalCalls) elTotalCalls.textContent = calls.total_calls ?? 0;

    const elAnswered = document.getElementById("dash-answered-calls");
    if (elAnswered) elAnswered.textContent = calls.total_answered ?? 0;

    const elDemos = document.getElementById("dash-total-demos");
    if (elDemos) elDemos.textContent = calls.total_demos ?? 0;

    const elTotalTime = document.getElementById("dash-total-time");
    if (elTotalTime) elTotalTime.textContent = calls.total_time_min ?? 0;

    const pays = data.payments || {};

    const elTotalRev = document.getElementById("dash-total-revenue");
    if (elTotalRev)
      elTotalRev.textContent = formatCurrency(pays.total_revenue);

    const elNewRev = document.getElementById("dash-new-revenue");
    if (elNewRev)
      elNewRev.textContent = formatCurrency(pays.total_new_revenue);

    const elRepeatRev = document.getElementById("dash-repeat-revenue");
    if (elRepeatRev)
      elRepeatRev.textContent = formatCurrency(pays.total_repeat_revenue);

    const elPayCount = document.getElementById("dash-total-payments");
    if (elPayCount)
      elPayCount.textContent = pays.total_payments_count ?? 0;

    const conv = data.conversion || {};

    const elAnsRate = document.getElementById("dash-answered-rate");
    if (elAnsRate)
      elAnsRate.textContent = `${conv.answered_rate_pct ?? 0}%`;

    const elDemoRate = document.getElementById("dash-demo-rate");
    if (elDemoRate)
      elDemoRate.textContent = `${conv.demo_to_answered_pct ?? 0}%`;

    const elPayRate = document.getElementById("dash-payment-rate");
    if (elPayRate)
      elPayRate.textContent = `${conv.payment_to_demo_pct ?? 0}%`;

    const elRevPerCall = document.getElementById("dash-revenue-per-call");
    if (elRevPerCall)
      elRevPerCall.textContent = formatCurrency(
        conv.revenue_per_call ?? 0
      );

    const inc = data.incentive || {};
    const elIncEarned = document.getElementById("dash-incentive-earned");
    if (elIncEarned)
      elIncEarned.textContent = formatCurrency(
        inc.incentive_amount ?? 0
      );

    // ---- MANAGER TAB VISIBILITY ---- //

    // Try multiple fields for role
    const rawRole =
      emp.role ||
      emp.user_role ||
      emp.designation ||
      emp.position ||
      emp.title ||
      "";

    const roleStr = String(rawRole).toLowerCase().trim();

    const isManagerLike =
      roleStr.includes("manager") ||
      roleStr.includes("team lead") ||
      roleStr === "admin" ||
      emp.is_manager === true ||
      emp.is_admin === true;

    if (isManagerLike) {
      // The tab button for the manager panel has data-tab="manager-panel-content"
      // as per the event listener for tab switching.
      const managerTabButton = document.querySelector('.tab-button[data-tab="manager-panel-content"]');

      console.log("Manager tab button element:", managerTabButton);

      if (managerTabButton) {
        managerTabButton.style.display = "";
        managerTabButton.classList.remove("hidden");
      }

      const now = new Date();
      const incStartInput = document.getElementById(
        "manager-inc-filter-start-date"
      );
      const incEndInput = document.getElementById(
        "manager-inc-filter-end-date"
      );

      if (incStartInput)
        incStartInput.value = new Date(
          now.getFullYear(),
          now.getMonth(),
          1
        )
          .toISOString()
          .split("T")[0];
      if (incEndInput)
        incEndInput.value = new Date(
          now.getFullYear(),
          now.getMonth() + 1,
          0
        )
          .toISOString()
          .split("T")[0];

      try {
        await loadManagerTeam();
      } catch (e) {
        console.error("Manager team preload failed", e);
      }
    } else {
      console.log("Not treated as manager/admin. rawRole =", rawRole);
    }
  } catch (err) {
    console.error("Dashboard load failed", err);
  }

  // --- Render Target Panels (static) ---
  const targetContainer = document.getElementById("target-panels-container");
  if (targetContainer) {
    targetContainer.innerHTML = `
      <div class="card target-card">
        <div class="target-title">Minimum Call time Target(min)</div>
        <div class="target-value">1,000</div>
      </div>
      <div class="card target-card">
        <div class="target-title">Minimum Demo Target</div>
        <div class="target-value">15</div>
      </div>
      <div class="card target-card">
        <div class="target-title">Minimum Payment Target(Rs.)</div>
        <div class="target-value">50,000</div>
      </div>
    `;
  }
}

// ----------- CALLS TAB ----------- //

async function loadCalls() {
  try {
    const params = new URLSearchParams({
      page: String(callsPage),
      page_size: String(callsPageSize),
    });

    if (callsStartDate) params.set("start_date", callsStartDate);
    if (callsEndDate) params.set("end_date", callsEndDate);

    const data = await apiRequest(`/calls/my-entries?${params.toString()}`);

    callsTotalPages = data.total_pages || 1;

    const tbody = document.getElementById("calls-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!data.entries || data.entries.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="11" class="muted">No entries found.</td></tr>';
      const pageInfo = document.getElementById("calls-page-info");
      if (pageInfo)
        pageInfo.textContent = `Page ${callsPage} of ${callsTotalPages}`;
      return;
    }

    data.entries.forEach((entry) => {
      const demoCards = (entry.demo_cards || [])
        .map((url) => `<a href="${url}" target="_blank">Link</a>`)
        .join(", ");

      const meetLinks = (entry.google_meet_links || [])
        .map((url) => `<a href="${url}" target="_blank">Meet</a>`)
        .join(", ");

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${entry.date || ""}</td>
        <td>${entry.answered_calls ?? 0}</td>
        <td>${entry.unanswered_calls ?? 0}</td>
        <td>${entry.total_calls ?? 0}</td>
        <td>${entry.call_time_min ?? 0}</td>
        <td>${entry.demo_time_min ?? 0}</td>
        <td>${entry.total_time_min ?? 0}</td>
        <td>${entry.demos_conducted ?? 0}</td>
        <td>${demoCards || "-"}</td>
        <td>${meetLinks || "-"}</td>
        <td>${entry.notes ? entry.notes : "-"}</td>
      `;
      tbody.appendChild(tr);
    });

    const pageInfo = document.getElementById("calls-page-info");
    if (pageInfo)
      pageInfo.textContent = `Page ${callsPage} of ${callsTotalPages}`;
  } catch (err) {
    console.error("Calls load failed", err);
  }
}

function recalcCallTotals() {
  const answered = Number(
    document.getElementById("answered-calls")?.value || 0
  );
  const unanswered = Number(
    document.getElementById("unanswered-calls")?.value || 0
  );
  const callTime = Number(
    document.getElementById("call-time-min")?.value || 0
  );
  const demoTime = Number(
    document.getElementById("demo-time-min")?.value || 0
  );

  const totalCallsEl = document.getElementById("total-calls");
  if (totalCallsEl) totalCallsEl.value = answered + unanswered;

  const totalTimeEl = document.getElementById("total-time-min");
  if (totalTimeEl) totalTimeEl.value = callTime + demoTime;
}

async function handleCallsFormSubmit(event) {
  event.preventDefault();

  const errorEl = document.getElementById("calls-form-error");
  if (errorEl) errorEl.textContent = "";

  const dateVal = document.getElementById("call-date").value;
  const answered = Number(
    document.getElementById("answered-calls").value || 0
  );
  const unanswered = Number(
    document.getElementById("unanswered-calls").value || 0
  );
  const totalCalls = answered + unanswered;
  const callTime = Number(document.getElementById("call-time-min").value || 0);
  const demos = Number(
    document.getElementById("demos-conducted").value || 0
  );
  const demoTime = Number(document.getElementById("demo-time-min").value || 0);
  const totalTime = callTime + demoTime;
  const notes = document.getElementById("call-notes").value || "";

  if (!dateVal) {
    errorEl.textContent = "Please select a date.";
    return;
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const dateParts = dateVal.split("-");
  const selectedDate = new Date(
    dateParts[0],
    dateParts[1] - 1,
    dateParts[2]
  );

  if (selectedDate > today) {
    errorEl.textContent = "Cannot submit entries for a future date.";
    return;
  }

  if (totalCalls === 0 && callTime === 0 && demos === 0 && demoTime === 0) {
    errorEl.textContent = "Please enter at least some call activity.";
    return;
  }

  if (answered > 0 && callTime === 0) {
    errorEl.textContent =
      "Call time (in minutes) is required when there are answered calls.";
    return;
  }

  if (demos > 0 && demoTime === 0) {
    errorEl.textContent =
      "Demo time (in minutes) is required when demos are conducted.";
    return;
  }

  if (demoTime > 0 && demos === 0) {
    errorEl.textContent =
      "Number of demos conducted is required when demo time is entered.";
    return;
  }

  const demoCardInputs = Array.from(
    document.querySelectorAll(".demo-card-input")
  );
  const meetLinkInputs = Array.from(
    document.querySelectorAll(".meet-link-input")
  );

  const demoCards = demoCardInputs
    .map((i) => i.value.trim())
    .filter((v) => v.length > 0);
  const meetLinks = meetLinkInputs
    .map((i) => i.value.trim())
    .filter((v) => v.length > 0);

  if (demos > 0 && demoCards.length === 0) {
    errorEl.textContent =
      "Please enter at least one CRM link for demo customers.";
    return;
  }

  if (demos > 0 && demoCards.length !== demos) {
    errorEl.textContent = `Number of CRM links (${demoCards.length}) must match demos conducted (${demos}).`;
    return;
  }

  if (meetLinks.length > demos && demos > 0) {
    errorEl.textContent = `You can add at most ${demos} Google Meet links for ${demos} demos.`;
    return;
  }

  if (demoTime > 0 && demos === 0) {
    errorEl.textContent =
      "Number of demos conducted is required when demo time is entered.";
    return;
  }

  if (meetLinks.length > 0 && demos === 0) {
    errorEl.textContent =
      "Demos conducted must be entered if you are adding Google Meet links.";
    return;
  }

  if (demoCards.length > 0 && demos === 0) {
    errorEl.textContent =
      "Demos conducted must be entered if you are adding CRM links.";
    return;
  }

  const payload = {
    date: dateVal,
    answered_calls: answered,
    unanswered_calls: unanswered,
    call_time_min: callTime,
    demos_conducted: demos,
    demo_cards: demoCards,
    demo_time_min: demoTime,
    google_meet_links: meetLinks,
    notes: notes,
  };

  try {
    const data = await apiRequest("/calls/", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (!data.success) {
      errorEl.textContent =
        data.detail || data.message || "Unable to save entry.";
      return;
    }

    alert("Call entry saved successfully.");

    document.getElementById("answered-calls").value = 0;
    document.getElementById("unanswered-calls").value = 0;
    document.getElementById("total-calls").value = 0;
    document.getElementById("call-time-min").value = 0;
    document.getElementById("demos-conducted").value = 0;
    document.getElementById("demo-time-min").value = 0;
    document.getElementById("total-time-min").value = 0;
    document.getElementById("call-notes").value = "";

    document.getElementById("demo-cards-wrapper").innerHTML = `
      <div class="dynamic-input-row">
        <input
          type="url"
          class="demo-card-input"
          placeholder="https://antcrm.com/demo/card-123"
        />
        <button
          type="button"
          class="btn small-btn add-demo-card"
        >
          Add
        </button>
        <button
          type="button"
          class="btn small-btn danger-btn remove-demo-card"
        >
          Remove
        </button>
      </div>`;
    document.getElementById("meet-links-wrapper").innerHTML = `
      <div class="dynamic-input-row">
        <input
          type="url"
          class="meet-link-input"
          placeholder="https://meet.google.com/abc-defg-hij"
        />
        <button
          type="button"
          class="btn small-btn add-meet-link"
        >
          Add
        </button>
        <button
          type="button"
          class="btn small-btn danger-btn remove-meet-link"
        >
          Remove
        </button>
      </div>`;

    callsPage = 1;
    await loadCalls();
  } catch (err) {
    console.error(err);
    errorEl.textContent = `Unable to save entry: ${err.message}`;
  }
}

// ----------- PAYMENTS TAB ----------- //

async function loadPayments() {
  try {
    const params = new URLSearchParams({
      page: String(paymentsPage),
      page_size: String(paymentsPageSize),
    });

    if (paymentsStartDate) {
      params.set("start_date", paymentsStartDate);
    }
    if (paymentsEndDate) {
      params.set("end_date", paymentsEndDate);
    }

    const data = await apiRequest(`/payments/my?${params.toString()}`);

    paymentsTotalPages = data.total_pages || 1;

    const tbody = document.getElementById("payments-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!data.entries || data.entries.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6" class="muted">No payments found.</td></tr>';
      const pageInfo = document.getElementById("payments-page-info");
      if (pageInfo)
        pageInfo.textContent = `Page ${paymentsPage} of ${paymentsTotalPages}`;
      return;
    }

    data.entries.forEach((payment) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${payment.date || ""}</td>
        <td>${payment.customer || ""}</td>
        <td>${payment.customer_type || ""}</td>
        <td>${payment.service_type || ""}</td>
        <td>${formatCurrency(payment.amount_paid ?? 0)}</td>
        <td>${
          payment.crm_link
            ? `<a href="${payment.crm_link}" target="_blank">View</a>`
            : "-"
        }</td>
      `;
      tbody.appendChild(tr);
    });

    const pageInfo = document.getElementById("payments-page-info");
    if (pageInfo)
      pageInfo.textContent = `Page ${paymentsPage} of ${paymentsTotalPages}`;
  } catch (err) {
    console.error("Payments load failed", err);
  }
}

// ----------- INCENTIVES TAB ----------- //

async function loadIncentives() {
  try {
    const params = new URLSearchParams({
      page: String(incPage),
      page_size: String(incPageSize),
    });

    if (incStartDate) params.set("start_date", incStartDate);
    if (incEndDate) params.set("end_date", incEndDate);

    const data = await apiRequest(
      `/payments/my-incentives?${params.toString()}`
    );

    incTotalPages = data.total_pages || 1;

    const curPeriodEl = document.getElementById("inc-current-period");
    if (curPeriodEl)
      curPeriodEl.textContent = `${data.current_month_start} to ${data.current_month_end}`;

    const curTotalEl = document.getElementById("inc-current-total");
    if (curTotalEl)
      curTotalEl.textContent = formatCurrency(
        data.current_month_total_incentive ?? 0
      );

    const rangePeriodEl = document.getElementById("inc-range-period");
    if (rangePeriodEl)
      rangePeriodEl.textContent = `${data.range_start} to ${data.range_end}`;

    const rangeTotalEl = document.getElementById("inc-range-total");
    if (rangeTotalEl)
      rangeTotalEl.textContent = formatCurrency(
        data.range_total_incentive ?? 0
      );

    const tbody = document.getElementById("inc-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!data.entries || data.entries.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="8" class="muted">No incentive entries found.</td></tr>';
      const pageInfo = document.getElementById("inc-page-info");
      if (pageInfo)
        pageInfo.textContent = `Page ${incPage} of ${incTotalPages}`;
      return;
    }

    data.entries.forEach((entry) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${entry.date || ""}</td>
        <td>${entry.customer || ""}</td>
        <td>${entry.customer_type || ""}</td>
        <td>${entry.service_type || ""}</td>
        <td>${formatCurrency(entry.amount_paid ?? 0)}</td>
        <td>${formatCurrency(entry.base_amount ?? 0)}</td>
        <td>${entry.incentive_rate_pct ?? 0}%</td>
        <td>${formatCurrency(entry.incentive_amount ?? 0)}</td>
      `;
      tbody.appendChild(tr);
    });

    const pageInfo = document.getElementById("inc-page-info");
    if (pageInfo)
      pageInfo.textContent = `Page ${incPage} of ${incTotalPages}`;
  } catch (err) {
    console.error("Incentives load failed", err);
  }
}

// ----------- MANAGER TAB (TEAM PAYMENTS) ----------- //

async function loadManagerTeam() {
  const addSelect = document.getElementById("manager-employee-select");
  const filterSelect = document.getElementById("manager-filter-employee");
  const incFilterSelect = document.getElementById(
    "manager-inc-filter-employee"
  );

  if (!addSelect && !filterSelect && !incFilterSelect) return;

  try {
    const data = await apiRequest("/manager/team");
    const employees = data.employees || data.team || [];
    managerEmployees = employees;

    [addSelect, filterSelect, incFilterSelect].forEach((sel) => {
      if (sel) sel.innerHTML = "";
    });

    if (addSelect)
      addSelect.innerHTML = '<option value="">Select employee</option>';

    if (filterSelect) filterSelect.innerHTML = "";
    if (incFilterSelect) incFilterSelect.innerHTML = "";

    employees.forEach((emp) => {
      const empId = emp.employeeId || emp.id || "";
      const name = emp.name || emp.employee_name || "";
      const email =
        emp.email || emp.employee_email || emp.employeeEmail || "";

      if (addSelect) {
        const opt = document.createElement("option");
        opt.value = email;
        opt.textContent = `${empId} - ${name} (${email})`;
        addSelect.appendChild(opt);
      }

      const filterOpt = document.createElement("option");
      filterOpt.value = email;
      filterOpt.textContent = `${empId} - ${name}`;

      if (filterSelect) {
        filterSelect.appendChild(filterOpt.cloneNode(true));
      }
      if (incFilterSelect) {
        incFilterSelect.appendChild(filterOpt.cloneNode(true));
      }
    });
  } catch (err) {
    console.error("Manager team load failed", err);
  }
}

async function loadManagerPayments(resetPage = false) {
  const tbody = document.getElementById("manager-payments-body");
  const pageInfo = document.getElementById("manager-page-info");
  if (!tbody || !pageInfo) return;

  if (resetPage) {
    managerPage = 1;
  }

  try {
    const params = new URLSearchParams({
      page: String(managerPage),
      page_size: String(managerPageSize),
    });

    if (managerFilterEmployeeId) {
      params.set("employee_email", managerFilterEmployeeId);
    }
    if (managerFilterStartDate) {
      params.set("start_date", managerFilterStartDate);
    }
    if (managerFilterEndDate) {
      params.set("end_date", managerFilterEndDate);
    }

    const data = await apiRequest(
      `/manager/team-data?data_type=payments&${params.toString()}`
    );

    managerTotalPages = data.total_pages || 1;

    tbody.innerHTML = "";

    if (!data.entries || data.entries.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="7" class="muted">No payments found for this period.</td></tr>';
      pageInfo.textContent = `Page ${managerPage} of ${managerTotalPages}`;
      return;
    }

    data.entries.forEach((p) => {
      const tr = document.createElement("tr");
      const empName = p.employee_name || p.employeeName || "N/A";
      const amountPaid = p.amount_paid ?? 0;
      const crmLink = p.crm_link;

      tr.innerHTML = `
        <td>${p.date || ""}</td>
        <td>${empName}</td>
        <td>${p.customer || ""}</td>
        <td>${p.customer_type || ""}</td>
        <td>${p.service_type || ""}</td>
        <td>${formatCurrency(amountPaid)}</td>
        <td>${
          crmLink
            ? `<a href="${crmLink}" target="_blank">View</a>`
            : "-"
        }</td>
      `;
      tbody.appendChild(tr);
    });

    pageInfo.textContent = `Page ${managerPage} of ${managerTotalPages}`;
  } catch (err) {
    console.error("Manager payments load failed", err);
    tbody.innerHTML = `<tr><td colspan="7" class="muted">Error loading payments: ${err.message}</td></tr>`;
  }
}

async function loadManagerIncentives(resetPage = false) {
  const tbody = document.getElementById("manager-incentives-body");
  const pageInfo = document.getElementById("manager-inc-page-info");
  if (!tbody || !pageInfo) return;

  if (resetPage) {
    managerIncPage = 1;
  }

  try {
    const params = new URLSearchParams({
      page: String(managerIncPage),
      page_size: String(managerIncPageSize),
    });

    if (managerIncFilterEmployeeId) {
      params.set("employee_email", managerIncFilterEmployeeId);
    }
    if (managerIncFilterStartDate) {
      params.set("start_date", managerIncFilterStartDate);
    }
    if (managerIncFilterEndDate) {
      params.set("end_date", managerIncFilterEndDate);
    }

    const data = await apiRequest(
      `/manager/team-data?data_type=incentives&${params.toString()}`
    );

    managerIncTotalPages = data.total_pages || 1;
    tbody.innerHTML = "";

    if (!data.entries || data.entries.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="9" class="muted">No incentives found for this period.</td></tr>';
      pageInfo.textContent = `Page ${managerIncPage} of ${managerIncTotalPages}`;
      return;
    }

    data.entries.forEach((p) => {
      const tr = document.createElement("tr");
      const empName = p.employee_name || p.employeeName || "N/A";
      const amountPaid = p.amount_paid ?? 0;
      const baseAmount = p.base_amount ?? 0;
      const rate = p.incentive_rate_pct ?? 0;
      const incentive = p.incentive_amount ?? 0;

      tr.innerHTML = `
        <td>${p.date || ""}</td>
        <td>${empName}</td>
        <td>${p.customer || ""}</td>
        <td>${p.customer_type || ""}</td>
        <td>${p.service_type || ""}</td> 
        <td>${formatCurrency(amountPaid)}</td>
        <td>${formatCurrency(baseAmount)}</td>
        <td>${rate}%</td>
        <td>${formatCurrency(incentive)}</td>
      `;
      tbody.appendChild(tr);
    });

    pageInfo.textContent = `Page ${managerIncPage} of ${managerIncTotalPages}`;
  } catch (err) {
    console.error("Manager incentives load failed", err);
    tbody.innerHTML = `<tr><td colspan="9" class="muted">Error loading incentives: ${err.message}</td></tr>`;
  }
}

async function handleManagerAddPayment(event) {
  event.preventDefault();
  const form = event.target;
  const msgEl = document.getElementById("manager-add-payment-message");
  if (msgEl) msgEl.textContent = "";

  const empSelect = document.getElementById("manager-employee-select");
  const dateInput = document.getElementById("manager-payment-date");
  const customerInput = document.getElementById("manager-customer");
  const customerTypeSelect = document.getElementById(
    "manager-customer-type"
  );
  const serviceTypeSelect = document.getElementById(
    "manager-service-type"
  );
  const amountInput = document.getElementById("manager-amount-paid");
  const crmInput = document.getElementById("manager-crm-link");

  const employee_email = empSelect.value;
  const dateVal = dateInput.value;
  const customer = customerInput.value.trim();
  const customer_type = customerTypeSelect.value;
  const service_type = serviceTypeSelect.value;
  const amountStr = amountInput.value;
  const crm_link = crmInput ? crmInput.value.trim() : "";

  if (!employee_email) {
    msgEl.textContent = "Please select an employee.";
    return;
  }
  if (!dateVal) {
    msgEl.textContent = "Please select a date.";
    return;
  }
  if (!customer) {
    msgEl.textContent = "Please enter customer name.";
    return;
  }
  if (!customer_type) {
    msgEl.textContent = "Please select customer type.";
    return;
  }
  if (!service_type) {
    msgEl.textContent = "Please select service.";
    return;
  }
  const amountPaid = parseFloat(amountStr || "0");
  if (!(amountPaid > 0)) {
    msgEl.textContent = "Please enter a valid amount.";
    return;
  }

  const payload = {
    date: dateVal,
    employee_email,
    customer,
    customer_type,
    service_type,
    amount_paid: amountPaid,
    crm_link: crm_link || null,
  };

  try {
    const data = await apiRequest("/manager/payments/add", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (!data.success) {
      msgEl.textContent =
        data.detail || data.message || "Unable to save payment.";
      return;
    }

    msgEl.textContent = "Payment saved successfully.";
    form.reset();

    const filterSelect = document.getElementById("manager-filter-employee");
    if (filterSelect) {
      const addedEmployee = managerEmployees.find(
        (emp) =>
          emp.email === employee_email ||
          emp.employee_email === employee_email ||
          emp.employeeEmail === employee_email
      );
      if (addedEmployee) {
        filterSelect.value = employee_email;
        managerFilterEmployeeId = employee_email;
      }
    }

    await loadManagerPayments(true);
  } catch (err) {
    console.error("Manager add payment failed", err);
    msgEl.textContent = `Unable to save payment: ${err.message}`;
  }
}

// ----------- EVENT BINDINGS ----------- //

document.addEventListener("DOMContentLoaded", () => {
  // --- Style Overrides ---
  const style = document.createElement("style");
  style.innerHTML = `
    #manager-add-payment-form .form-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
    }

    #manager-add-payment-form .form-group.full-width {
      grid-column: 1 / -1;
    }

    @media (max-width: 768px) {
      #manager-add-payment-form .form-grid {
        grid-template-columns: 1fr;
      }
    }

    #manager-add-payment-message {
      grid-column: 1 / -1;
      margin-top: 0.5rem;
      min-height: 1.2em;
    }

    #logout-btn:hover {
      background-color: black !important;
      color: white !important;
    }

    .target-panels-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
      margin-bottom: 1rem;
    }
    .target-card {
      background-color: white;
      padding: 1.5rem;
      text-align: center;
    }
    .target-title {
      font-size: 0.9rem;
      color: #555;
      margin-bottom: 0.5rem;
    }
    .target-value {
      font-size: 2rem;
      font-weight: bold;
      color: #333;
    }
  `;
  document.head.appendChild(style);

  // Login
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", handleLogin);
  }

  // Password eye toggle
  const toggleBtn = document.getElementById("toggle-password");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const pwdInput = document.getElementById("login-password");
      if (!pwdInput) return;
      const isPassword = pwdInput.type === "password";
      pwdInput.type = isPassword ? "text" : "password";
      toggleBtn.classList.toggle("visible", isPassword);
    });
  }

  // Logout
  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => handleLogout(false));
  }

  // Change password
  const changePwdBtn = document.getElementById("change-password-btn");
  if (changePwdBtn) {
    changePwdBtn.addEventListener("click", () => {
      alert(
        "Change password feature is not enabled yet. Please contact your manager or admin."
      );
    });
  }

  // Dashboard filter
  const dashFilterBtn = document.getElementById("dash-apply-filter");
  if (dashFilterBtn) {
    dashFilterBtn.addEventListener("click", () => {
      dashboardStartDate =
        document.getElementById("dash-start-date")?.value || "";
      dashboardEndDate =
        document.getElementById("dash-end-date")?.value || "";
      loadDashboard();
    });
  }

  // Tabs
  document.querySelectorAll(".tab-button").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      switchTab(tabId);

      if (tabId === "dashboard-tab") {
        loadDashboard();
      } else if (tabId === "calls-tab") {
        loadCalls();
      } else if (tabId === "payments-tab") {
        loadPayments();
      } else if (tabId === "incentives-tab") {
        loadIncentives();
      } else if (tabId === "manager-panel-content") {
        loadManagerTeam().then(() => {
          loadManagerPayments(true);
          loadManagerIncentives(true);
        });
      }
    });
  });

  // Calls pagination & page size
  const callsPageSizeEl = document.getElementById("calls-page-size");
  if (callsPageSizeEl) {
    callsPageSizeEl.addEventListener("change", (e) => {
      callsPageSize = Number(e.target.value);
      callsPage = 1;
      loadCalls();
    });
  }

  const callsPrevBtn = document.getElementById("calls-prev-page");
  if (callsPrevBtn) {
    callsPrevBtn.addEventListener("click", () => {
      if (callsPage > 1) {
        callsPage--;
        loadCalls();
      }
    });
  }

  const callsNextBtn = document.getElementById("calls-next-page");
  if (callsNextBtn) {
    callsNextBtn.addEventListener("click", () => {
      if (callsPage < callsTotalPages) {
        callsPage++;
        loadCalls();
      }
    });
  }

  const callsFilterBtn = document.getElementById("calls-apply-filter");
  if (callsFilterBtn) {
    callsFilterBtn.addEventListener("click", () => {
      callsStartDate =
        document.getElementById("calls-start-date")?.value || "";
      callsEndDate =
        document.getElementById("calls-end-date")?.value || "";
      callsPage = 1;
      loadCalls();
    });
  }

  // Payments filter
  const paymentsFilterBtn = document.getElementById(
    "payments-apply-filter"
  );
  if (paymentsFilterBtn) {
    paymentsFilterBtn.addEventListener("click", () => {
      paymentsStartDate =
        document.getElementById("payments-start-date")?.value || "";
      paymentsEndDate =
        document.getElementById("payments-end-date")?.value || "";
      paymentsPage = 1;
      loadPayments();
    });
  }

  // Payments pagination & page size
  const payPageSizeEl = document.getElementById("payments-page-size");
  if (payPageSizeEl) {
    payPageSizeEl.addEventListener("change", (e) => {
      paymentsPageSize = Number(e.target.value);
      paymentsPage = 1;
      loadPayments();
    });
  }

  const payPrevBtn = document.getElementById("payments-prev-page");
  if (payPrevBtn) {
    payPrevBtn.addEventListener("click", () => {
      if (paymentsPage > 1) {
        paymentsPage--;
        loadPayments();
      }
    });
  }

  const payNextBtn = document.getElementById("payments-next-page");
  if (payNextBtn) {
    payNextBtn.addEventListener("click", () => {
      if (paymentsPage < paymentsTotalPages) {
        paymentsPage++;
        loadPayments();
      }
    });
  }

  // Incentives filters & pagination
  const incPageSizeEl = document.getElementById("inc-page-size");
  if (incPageSizeEl) {
    incPageSizeEl.addEventListener("change", (e) => {
      incPageSize = Number(e.target.value);
      incPage = 1;
      loadIncentives();
    });
  }

  const incPrevBtn = document.getElementById("inc-prev-page");
  if (incPrevBtn) {
    incPrevBtn.addEventListener("click", () => {
      if (incPage > 1) {
        incPage--;
        loadIncentives();
      }
    });
  }

  const incNextBtn = document.getElementById("inc-next-page");
  if (incNextBtn) {
    incNextBtn.addEventListener("click", () => {
      if (incPage < incTotalPages) {
        incPage++;
        loadIncentives();
      }
    });
  }

  const incFilterBtn = document.getElementById("inc-apply-filter");
  if (incFilterBtn) {
    incFilterBtn.addEventListener("click", () => {
      incStartDate =
        document.getElementById("inc-start-date")?.value || "";
      incEndDate = document.getElementById("inc-end-date")?.value || "";
      incPage = 1;
      loadIncentives();
    });
  }

  // Manager tab events
  const managerFilterBtn = document.getElementById("manager-filter-btn");
  if (managerFilterBtn) {
    managerFilterBtn.addEventListener("click", () => {
      const empFilterSelect = document.getElementById(
        "manager-filter-employee"
      );
      managerFilterEmployeeId = empFilterSelect?.value || "";
      managerFilterStartDate = document.getElementById(
        "manager-filter-start-date"
      )?.value;
      managerFilterEndDate = document.getElementById(
        "manager-filter-end-date"
      )?.value;

      loadManagerPayments(true);
    });
  }

  const managerPrevBtn = document.getElementById("manager-prev-page");
  if (managerPrevBtn) {
    managerPrevBtn.addEventListener("click", () => {
      if (managerPage > 1) {
        managerPage--;
        loadManagerPayments(false);
      }
    });
  }

  const managerNextBtn = document.getElementById("manager-next-page");
  if (managerNextBtn) {
    managerNextBtn.addEventListener("click", () => {
      if (managerPage < managerTotalPages) {
        managerPage++;
        loadManagerPayments(false);
      }
    });
  }

  // Manager Incentives tab events
  const managerIncFilterBtn = document.getElementById(
    "manager-inc-filter-btn"
  );
  if (managerIncFilterBtn) {
    managerIncFilterBtn.addEventListener("click", () => {
      const empIncFilterSelect = document.getElementById(
        "manager-inc-filter-employee"
      );
      managerIncFilterEmployeeId = empIncFilterSelect?.value || "";
      managerIncFilterStartDate = document.getElementById(
        "manager-inc-filter-start-date"
      )?.value;
      managerIncFilterEndDate = document.getElementById(
        "manager-inc-filter-end-date"
      )?.value;
      loadManagerIncentives(true);
    });
  }

  const managerIncPrevBtn = document.getElementById(
    "manager-inc-prev-page"
  );
  if (managerIncPrevBtn) {
    managerIncPrevBtn.addEventListener("click", () => {
      if (managerIncPage > 1) {
        managerIncPage--;
        loadManagerIncentives(false);
      }
    });
  }

  const managerIncNextBtn = document.getElementById(
    "manager-inc-next-page"
  );
  if (managerIncNextBtn) {
    managerIncNextBtn.addEventListener("click", () => {
      if (managerIncPage < managerIncTotalPages) {
        managerIncPage++;
        loadManagerIncentives(false);
      }
    });
  }

  const managerIncPageSizeEl = document.getElementById(
    "manager-inc-page-size"
  );
  if (managerIncPageSizeEl) {
    managerIncPageSizeEl.addEventListener("change", (e) => {
      managerIncPageSize = Number(e.target.value);
      managerIncPage = 1;
      loadManagerIncentives(true);
    });
  }

  // Auto-calc totals
  ["answered-calls", "unanswered-calls", "call-time-min", "demo-time-min"].forEach(
    (id) => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener("input", () => {
          recalcCallTotals();
        });
      }
    }
  );

  // Demo cards dynamic rows
  const demoWrapper = document.getElementById("demo-cards-wrapper");
  if (demoWrapper) {
    demoWrapper.addEventListener("click", (e) => {
      if (e.target.classList.contains("remove-demo-card")) {
        const row = e.target.closest(".dynamic-input-row");
        if (row) {
          row.remove();
          const wrapper = document.getElementById("demo-cards-wrapper");
          if (wrapper.querySelectorAll(".dynamic-input-row").length === 0) {
            const div = document.createElement("div");
            div.className = "dynamic-input-row";
            div.innerHTML = `
              <input
                type="url"
                class="demo-card-input"
                placeholder="https://antcrm.com/demo/card-123"
              />
              <button
                type="button"
                class="btn small-btn add-demo-card"
              >
                Add
              </button>
              <button
                type="button"
                class="btn small-btn danger-btn remove-demo-card"
              >
                Remove
              </button>
            `;
            wrapper.appendChild(div);
          }
        }
      } else if (e.target.classList.contains("add-demo-card")) {
        const wrapper = document.getElementById("demo-cards-wrapper");
        const div = document.createElement("div");
        div.className = "dynamic-input-row";
        div.innerHTML = `
          <input
            type="url"
            class="demo-card-input"
            placeholder="https://antcrm.com/demo/card-123"
          />
          <button
            type="button"
            class="btn small-btn add-demo-card"
          >
            Add
          </button>
          <button
            type="button"
            class="btn small-btn danger-btn remove-demo-card"
          >
            Remove
          </button>`;
        wrapper.appendChild(div);
      }
    });
  }

  // Meet links dynamic rows
  const meetWrapper = document.getElementById("meet-links-wrapper");
  if (meetWrapper) {
    meetWrapper.addEventListener("click", (e) => {
      if (e.target.classList.contains("remove-meet-link")) {
        const row = e.target.closest(".dynamic-input-row");
        if (row) {
          row.remove();
          const wrapper = document.getElementById("meet-links-wrapper");
          if (wrapper.querySelectorAll(".dynamic-input-row").length === 0) {
            const div = document.createElement("div");
            div.className = "dynamic-input-row";
            div.innerHTML = `
              <input
                type="url"
                class="meet-link-input"
                placeholder="https://meet.google.com/abc-defg-hij"
              />
              <button
                type="button"
                class="btn small-btn add-meet-link"
              >
                Add
              </button>
              <button
                type="button"
                class="btn small-btn danger-btn remove-meet-link"
              >
                Remove
              </button>
            `;
            wrapper.appendChild(div);
          }
        }
      } else if (e.target.classList.contains("add-meet-link")) {
        const wrapper = document.getElementById("meet-links-wrapper");
        const div = document.createElement("div");
        div.className = "dynamic-input-row";
        div.innerHTML = `
          <input
            type="url"
            class="meet-link-input"
            placeholder="https://meet.google.com/abc-defg-hij"
          />
          <button
            type="button"
            class="btn small-btn add-meet-link"
          >
            Add
          </button>
          <button
            type="button"
            class="btn small-btn danger-btn remove-meet-link"
          >
            Remove
          </button>`;
        wrapper.appendChild(div);
      }
    });
  }

  // Calls form submit
  const callsForm = document.getElementById("calls-form");
  if (callsForm) {
    callsForm.addEventListener("submit", handleCallsFormSubmit);
  }

  const managerAddForm = document.getElementById("manager-add-payment-form");
  if (managerAddForm) {
    managerAddForm.addEventListener("submit", handleManagerAddPayment);
  }

  // Initial state
  setDefaultDashboardDates();
  setDefaultPaymentsDates();
  recalcCallTotals();

  // Auto-login if token exists
  const token = getToken();
  if (token) {
    showPortalView();
    setDefaultDashboardDates();
    setDefaultPaymentsDates();
    loadDashboard();
    loadCalls();
    loadPayments();
    loadIncentives();
  }
});
