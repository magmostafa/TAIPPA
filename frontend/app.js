/*
 * Shared client‑side logic for the TAIPPA front‑end.
 * This script provides utilities for authentication, API calls and
 * page‑specific initialisation.  It uses the browser's localStorage
 * to persist the JWT access token between pages.
 */

const API_BASE_URL = "http://localhost:8000";

// Retrieve the stored token
function getToken() {
  return localStorage.getItem("access_token");
}

// Store a new token
function setToken(token) {
  localStorage.setItem("access_token", token);
}

// Remove token on logout
function clearToken() {
  localStorage.removeItem("access_token");
}

// Perform an authenticated API request
async function apiRequest(endpoint, options = {}) {
  const token = getToken();
  const headers = options.headers || {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });
}

// Handle login form submission
async function handleLogin(event) {
  event.preventDefault();
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);
  formData.append("grant_type", "");
  formData.append("scope", "");
  formData.append("client_id", "");
  formData.append("client_secret", "");
  const res = await fetch(`${API_BASE_URL}/auth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
  });
  if (res.ok) {
    const data = await res.json();
    setToken(data.access_token);
    window.location.href = "dashboard.html";
  } else {
    const errEl = document.getElementById("error");
    errEl.textContent = "Invalid email or password.";
    errEl.classList.remove("hidden");
  }
}

// Handle user registration form submission
async function handleRegister(event) {
  event.preventDefault();
  const fullName = document.getElementById("reg-full-name").value;
  const email = document.getElementById("reg-email").value;
  const password = document.getElementById("reg-password").value;
  const role = document.getElementById("reg-role").value;
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ full_name: fullName, email, password, role }),
  });
  const errEl = document.getElementById("reg-error");
  if (res.ok) {
    // On success, automatically log in the user
    // Use OAuth2 password grant flow
    const loginData = new URLSearchParams();
    loginData.append("username", email);
    loginData.append("password", password);
    loginData.append("grant_type", "");
    loginData.append("scope", "");
    loginData.append("client_id", "");
    loginData.append("client_secret", "");
    const loginRes = await fetch(`${API_BASE_URL}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: loginData.toString(),
    });
    if (loginRes.ok) {
      const data = await loginRes.json();
      setToken(data.access_token);
      window.location.href = "dashboard.html";
    } else {
      // fallback: go to login page
      window.location.href = "index.html";
    }
  } else {
    const errorData = await res.json().catch(() => ({ detail: "Registration failed" }));
    errEl.textContent = errorData.detail || "Registration failed";
    errEl.classList.remove("hidden");
  }
}

// Fetch current user and update UI
async function loadCurrentUser() {
  const res = await apiRequest("/auth/me");
  if (res.ok) {
    const user = await res.json();
    const nameEl = document.getElementById("user-name");
    if (nameEl) nameEl.textContent = user.full_name || user.email;
  } else {
    // not logged in
    clearToken();
    window.location.href = "index.html";
  }
}

// Logout handler
function handleLogout() {
  clearToken();
  window.location.href = "index.html";
}

/*
 * Appearance and white‑label customisation
 *
 * To support enterprise white‑labelling, tenants can specify a primary colour,
 * secondary colour, site name, tagline and logo URL.  This function
 * retrieves the current tenant's settings and applies them to the page.
 */
async function loadTenantAppearance() {
  try {
    // Use public tenant endpoint when not authenticated.  On pages like the
    // landing or login page there is no token, so the `/me` endpoint would
    // return 401.  In that case, fetch the first tenant via the `/public`
    // endpoint.
    const endpoint = getToken() ? "/tenants/me" : "/tenants/public";
    const res = await apiRequest(endpoint);
    if (!res.ok) return;
    const tenant = await res.json();
    // Set document title to custom site name if provided
    if (tenant.site_name) {
      document.title = tenant.site_name + (document.title.includes(" – ") ? document.title.substring(document.title.indexOf(" – ")) : "");
    }
    // Update site title elements (class="site-title").  These elements
    // represent the primary site name on pages such as login or landing.
    document.querySelectorAll(".site-title").forEach((el) => {
      if (tenant.site_name) {
        el.textContent = tenant.site_name;
      }
    });

    // Update navigation titles.  Elements with class "nav-title" include
    // a data-base attribute which holds the page name (e.g., "Dashboard").
    // We combine the site name with this base string for consistent branding.
    document.querySelectorAll(".nav-title").forEach((el) => {
      const base = el.dataset.base || "";
      const siteName = tenant.site_name || el.textContent.split(" ")[0] || "TAIPPA";
      // Compose new title.  If there is a base descriptor (e.g. Dashboard),
      // separate it with a space.  Otherwise use just the site name.
      el.textContent = base ? `${siteName} ${base}` : siteName;
    });
    // Update tagline elements (class="site-tagline")
    document.querySelectorAll(".site-tagline").forEach((el) => {
      el.textContent = tenant.tagline || el.textContent;
    });
    // Update footer message (class="site-footer")
    document.querySelectorAll(".site-footer").forEach((el) => {
      el.textContent = tenant.footer_message || el.textContent;
    });
    // Update logo images (class="logo-img").  If a tenant logo is set,
    // assign the src and reveal the image; otherwise keep it hidden.
    document.querySelectorAll(".logo-img").forEach((img) => {
      if (tenant.logo_url) {
        img.src = tenant.logo_url;
        img.classList.remove("hidden");
      }
    });
    // Determine colours; fall back to default indigo palette
    const primary = tenant.primary_color || "#4f46e5";
    const secondary = tenant.secondary_color || lightenColor(primary, 20);
    // Apply as CSS variables
    document.documentElement.style.setProperty("--primary-color", primary);
    document.documentElement.style.setProperty("--secondary-color", secondary);
    // Apply to elements with Tailwind utility classes for indigo colours
    applyBrandColours(primary, secondary);
    // Insert custom CSS if provided
    if (tenant.custom_css) {
      let customStyle = document.getElementById("custom-css");
      if (!customStyle) {
        customStyle = document.createElement("style");
        customStyle.id = "custom-css";
        document.head.appendChild(customStyle);
      }
      customStyle.innerHTML = tenant.custom_css;
    }
  } catch (err) {
    console.error("Failed to load tenant appearance", err);
  }
}

// Utility: lighten or darken a colour by a percentage.  Accepts hex (#rrggbb)
// and returns a new hex string.  Positive percentage lightens, negative
// percentage darkens.
function lightenColor(hex, percent) {
  // Remove leading # if present
  hex = hex.replace("#", "");
  if (hex.length === 3) {
    // Expand shorthand (#abc -> #aabbcc)
    hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
  }
  const num = parseInt(hex, 16);
  let r = (num >> 16) + Math.round(2.55 * percent);
  let g = ((num >> 8) & 0x00ff) + Math.round(2.55 * percent);
  let b = (num & 0x0000ff) + Math.round(2.55 * percent);
  r = Math.max(Math.min(255, r), 0);
  g = Math.max(Math.min(255, g), 0);
  b = Math.max(Math.min(255, b), 0);
  return "#" + (0x1000000 + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

// Apply brand colours to commonly used Tailwind utility classes.  This
// function iterates over elements with certain classes and sets their
// inline styles to the specified colours.  It supports background and text
// colours used in navigation bars, buttons and dashboard cards.
function applyBrandColours(primary, secondary) {
  // background colour classes
  const bgClasses = [
    "bg-indigo-600",
    "bg-indigo-500",
    "bg-indigo-400",
  ];
  bgClasses.forEach((cls, idx) => {
    document.querySelectorAll(`.${cls}`).forEach((el) => {
      el.style.backgroundColor = idx === 0 ? primary : secondary;
    });
  });
  // text colour classes
  const textClasses = ["text-indigo-600", "text-indigo-500", "text-indigo-400"];
  textClasses.forEach((cls, idx) => {
    document.querySelectorAll(`.${cls}`).forEach((el) => {
      el.style.color = idx === 0 ? primary : secondary;
    });
  });
  // border colours (optional) could be added similarly
}

/*
 * Tenant settings management for admins
 */
async function loadTenantForm() {
  const res = await apiRequest("/tenants/me");
  if (!res.ok) return;
  const tenant = await res.json();
  // Populate form fields if present on page
  const fields = [
    ["tenant-site-name", tenant.site_name],
    ["tenant-tagline", tenant.tagline],
    ["tenant-footer", tenant.footer_message],
    ["tenant-logo-url", tenant.logo_url],
    ["tenant-primary-color", tenant.primary_color],
    ["tenant-secondary-color", tenant.secondary_color],
    ["tenant-custom-css", tenant.custom_css],
  ];
  fields.forEach(([id, value]) => {
    const el = document.getElementById(id);
    if (el) el.value = value || "";
  });
  // Save tenant ID on form for updates
  const hiddenId = document.getElementById("tenant-id");
  if (hiddenId) hiddenId.value = tenant.id;
}

async function saveTenantSettings(event) {
  event.preventDefault();
  const tenantId = document.getElementById("tenant-id").value;
  const payload = {
    site_name: document.getElementById("tenant-site-name").value || null,
    tagline: document.getElementById("tenant-tagline").value || null,
    footer_message: document.getElementById("tenant-footer").value || null,
    logo_url: document.getElementById("tenant-logo-url").value || null,
    primary_color: document.getElementById("tenant-primary-color").value || null,
    secondary_color: document.getElementById("tenant-secondary-color").value || null,
    custom_css: document.getElementById("tenant-custom-css").value || null,
  };
  const res = await apiRequest(`/tenants/${tenantId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (res.ok) {
    alert("Tenant settings updated successfully");
    await loadTenantAppearance();
  } else {
    alert("Failed to update tenant settings");
  }
}

// Brands page logic
async function loadBrands() {
  const table = document.getElementById("brands-table");
  const res = await apiRequest("/brands");
  if (res.ok) {
    const brands = await res.json();
    table.innerHTML = "";
    brands.forEach((b) => {
      const row = document.createElement("tr");
      row.innerHTML = `<td class="border px-4 py-2">${b.name}</td><td class="border px-4 py-2">${b.industry || ""}</td><td class="border px-4 py-2">${b.budget || ""}</td><td class="border px-4 py-2 text-sm space-x-2"><button class="text-blue-600 hover:underline" onclick="editBrand('${b.id}')">Edit</button><button class="text-red-600 hover:underline" onclick="deleteBrand('${b.id}')">Delete</button></td>`;
      table.appendChild(row);
    });
  }
}

async function handleCreateBrand(event) {
  event.preventDefault();
  const id = document.getElementById("brand-id").value;
  const name = document.getElementById("brand-name").value;
  const description = document.getElementById("brand-description").value;
  const industry = document.getElementById("brand-industry").value;
  const contact = document.getElementById("brand-contact").value;
  const budget = parseFloat(document.getElementById("brand-budget").value || "0");
  const payload = {
    name,
    description,
    industry,
    contact_email: contact,
    budget: isNaN(budget) ? null : budget,
  };
  let res;
  if (id) {
    // update existing brand
    res = await apiRequest(`/brands/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } else {
    // create new brand
    res = await apiRequest("/brands/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
  if (res.ok) {
    document.getElementById("brand-form").reset();
    // reset editing state
    document.getElementById("brand-id").value = "";
    document.getElementById("brand-submit").textContent = "Save";
    document.getElementById("brand-cancel").classList.add("hidden");
    await loadBrands();
  } else {
    alert("Failed to save brand");
  }
}

// Edit brand: populate form with existing data
async function editBrand(id) {
  const res = await apiRequest(`/brands/${id}`);
  if (res.ok) {
    const brand = await res.json();
    document.getElementById("brand-id").value = brand.id;
    document.getElementById("brand-name").value = brand.name;
    document.getElementById("brand-description").value = brand.description || "";
    document.getElementById("brand-industry").value = brand.industry || "";
    document.getElementById("brand-contact").value = brand.contact_email || "";
    document.getElementById("brand-budget").value = brand.budget || "";
    document.getElementById("brand-submit").textContent = "Update";
    document.getElementById("brand-cancel").classList.remove("hidden");
  }
}

// Cancel brand edit: reset form and state
function cancelBrandEdit() {
  document.getElementById("brand-form").reset();
  document.getElementById("brand-id").value = "";
  document.getElementById("brand-submit").textContent = "Save";
  document.getElementById("brand-cancel").classList.add("hidden");
}

// Delete brand
async function deleteBrand(id) {
  const confirmed = confirm("Are you sure you want to delete this brand?");
  if (!confirmed) return;
  const res = await apiRequest(`/brands/${id}`, { method: "DELETE" });
  if (res.ok) {
    await loadBrands();
  } else {
    alert("Failed to delete brand");
  }
}

/*
 * Analytics page logic
 */
async function runClustering(event) {
  if (event) event.preventDefault();
  const select = document.getElementById("cluster-count");
  const k = select ? parseInt(select.value) : 5;
  const res = await apiRequest(`/analytics/segments?k=${k}`);
  if (res.ok) {
    const data = await res.json();
    const tbody = document.getElementById("analytics-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    const clusters = data.clusters || {};
    const labels = Object.keys(clusters).sort((a, b) => Number(a) - Number(b));
    labels.forEach((label) => {
      const cluster = clusters[label];
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap">${label}</td>
        <td class="px-6 py-4 whitespace-nowrap">${cluster.size}</td>
        <td class="px-6 py-4 whitespace-nowrap">${cluster.avg_followers.toFixed(0)}</td>
        <td class="px-6 py-4 whitespace-nowrap">${cluster.avg_engagement_rate.toFixed(2)}%</td>
        <td class="px-6 py-4 whitespace-nowrap">${cluster.avg_avg_likes.toFixed(0)}</td>
        <td class="px-6 py-4 whitespace-nowrap">${cluster.avg_avg_comments.toFixed(0)}</td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    alert("Failed to compute clusters");
  }
}

// Campaigns page logic
async function loadCampaigns() {
  const table = document.getElementById("campaigns-table");
  const res = await apiRequest("/campaigns");
  if (res.ok) {
    const campaigns = await res.json();
    table.innerHTML = "";
    campaigns.forEach((c) => {
      const row = document.createElement("tr");
      const analysisCell = c.analysis
        ? `<button class="text-indigo-600 hover:underline" onclick="viewAnalysis('${c.id}')">View</button>`
        : "<span class='text-gray-500'>N/A</span>";
      row.innerHTML = `
        <td class="border px-4 py-2">${c.title}</td>
        <td class="border px-4 py-2 capitalize">${c.status}</td>
        <td class="border px-4 py-2">${c.budget ?? ""}</td>
        <td class="border px-4 py-2">${analysisCell}</td>
        <td class="border px-4 py-2 space-x-2 text-sm">
          <button class="text-blue-600 hover:underline" onclick="editCampaign('${c.id}')">Edit</button>
          <button class="text-red-600 hover:underline" onclick="deleteCampaign('${c.id}')">Delete</button>
          <button class="text-green-600 hover:underline" onclick="analyseCampaign('${c.id}')">Analyse</button>
        </td>`;
      table.appendChild(row);
    });
  }
}

async function handleCreateCampaign(event) {
  event.preventDefault();
  const id = document.getElementById("campaign-id").value;
  const brandId = document.getElementById("campaign-brand-id").value;
  const title = document.getElementById("campaign-title").value;
  const brief = document.getElementById("campaign-brief").value;
  const status = document.getElementById("campaign-status").value;
  const budgetVal = parseFloat(document.getElementById("campaign-budget").value || "0");
  const startDateVal = document.getElementById("campaign-start-date").value;
  const endDateVal = document.getElementById("campaign-end-date").value;
  const payload = {
    title,
    brief,
    status,
    budget: isNaN(budgetVal) ? null : budgetVal,
    start_date: startDateVal ? new Date(startDateVal).toISOString() : null,
    end_date: endDateVal ? new Date(endDateVal).toISOString() : null,
  };
  let res;
  if (id) {
    // update existing campaign
    res = await apiRequest(`/campaigns/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } else {
    // create new campaign
    res = await apiRequest("/campaigns/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, brand_id: brandId }),
    });
  }
  if (res.ok) {
    document.getElementById("campaign-form").reset();
    document.getElementById("campaign-id").value = "";
    document.getElementById("campaign-submit").textContent = "Save";
    document.getElementById("campaign-cancel").classList.add("hidden");
    await loadCampaigns();
    await loadBrandsSelect();
  } else {
    alert("Failed to save campaign");
  }
}

// Populate brand select for campaign form
async function loadBrandsSelect() {
  const select = document.getElementById("campaign-brand-id");
  if (!select) return;
  const res = await apiRequest("/brands");
  if (res.ok) {
    const brands = await res.json();
    select.innerHTML = "";
    brands.forEach((b) => {
      const option = document.createElement("option");
      option.value = b.id;
      option.textContent = b.name;
      select.appendChild(option);
    });
  }
}

// Edit campaign: populate form with existing data
async function editCampaign(id) {
  const res = await apiRequest(`/campaigns/${id}`);
  if (res.ok) {
    const c = await res.json();
    document.getElementById("campaign-id").value = c.id;
    await loadBrandsSelect();
    document.getElementById("campaign-brand-id").value = c.brand_id;
    document.getElementById("campaign-title").value = c.title;
    document.getElementById("campaign-brief").value = c.brief;
    document.getElementById("campaign-status").value = c.status;
    document.getElementById("campaign-budget").value = c.budget || "";
    document.getElementById("campaign-start-date").value = c.start_date ? c.start_date.substring(0, 10) : "";
    document.getElementById("campaign-end-date").value = c.end_date ? c.end_date.substring(0, 10) : "";
    document.getElementById("campaign-submit").textContent = "Update";
    document.getElementById("campaign-cancel").classList.remove("hidden");
  }
}

function cancelCampaignEdit() {
  document.getElementById("campaign-form").reset();
  document.getElementById("campaign-id").value = "";
  document.getElementById("campaign-submit").textContent = "Save";
  document.getElementById("campaign-cancel").classList.add("hidden");
  loadBrandsSelect();
}

async function deleteCampaign(id) {
  const confirmed = confirm("Are you sure you want to delete this campaign?");
  if (!confirmed) return;
  const res = await apiRequest(`/campaigns/${id}`, { method: "DELETE" });
  if (res.ok) {
    await loadCampaigns();
  } else {
    alert("Failed to delete campaign");
  }
}

// View analysis in modal
async function viewAnalysis(id) {
  const res = await apiRequest(`/campaigns/${id}`);
  if (res.ok) {
    const c = await res.json();
    const modal = document.getElementById("analysis-modal");
    const contentEl = document.getElementById("analysis-content");
    contentEl.textContent = c.analysis || "No analysis available.";
    modal.classList.remove("hidden");
  }
}

function closeAnalysisModal() {
  document.getElementById("analysis-modal").classList.add("hidden");
}

// Leads page logic
async function loadLeads() {
  await loadCurrentUser();
  const res = await apiRequest("/leads/");
  if (res.ok) {
    const leads = await res.json();
    const table = document.getElementById("leads-table");
    if (!table) return;
    table.innerHTML = "";
    leads.forEach((lead) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td class="border px-3 py-2">${lead.name}</td>
        <td class="border px-3 py-2">${lead.email}</td>
        <td class="border px-3 py-2">${lead.company || ""}</td>
        <td class="border px-3 py-2">${lead.message || ""}</td>
        <td class="border px-3 py-2">
          <select id="status-${lead.id}" class="border rounded px-1 py-0.5 text-sm">
            <option value="new" ${lead.status === "new" ? "selected" : ""}>New</option>
            <option value="contacted" ${lead.status === "contacted" ? "selected" : ""}>Contacted</option>
            <option value="qualified" ${lead.status === "qualified" ? "selected" : ""}>Qualified</option>
            <option value="won" ${lead.status === "won" ? "selected" : ""}>Won</option>
            <option value="lost" ${lead.status === "lost" ? "selected" : ""}>Lost</option>
          </select>
        </td>
        <td class="border px-3 py-2">
          <input type="text" id="notes-${lead.id}" value="${lead.notes || ""}" class="border rounded px-1 py-0.5 text-sm w-full" />
        </td>
        <td class="border px-3 py-2 text-sm">
          <button class="text-blue-600 hover:underline" onclick="saveLead('${lead.id}')">Save</button>
        </td>
      `;
      table.appendChild(row);
    });
  }
}

async function saveLead(leadId) {
  const statusSelect = document.getElementById(`status-${leadId}`);
  const notesInput = document.getElementById(`notes-${leadId}`);
  const payload = {
    status: statusSelect.value,
    notes: notesInput.value,
  };
  const res = await apiRequest(`/leads/${leadId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (res.ok) {
    // Optionally show success indicator
    // reload leads list
    loadLeads();
  } else {
    alert("Failed to update lead");
  }
}

// Pricing page logic: load plans and subscription status
async function loadPricing() {
  await loadCurrentUser();
  // Display success or cancellation messages based on query params
  const urlParams = new URLSearchParams(window.location.search);
  const sessionId = urlParams.get("session_id");
  const cancelled = urlParams.get("cancelled");
  const alertContainer = document.getElementById("pricing-alert");
  if (alertContainer) {
    if (sessionId) {
      alertContainer.innerHTML = `<div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">Payment completed successfully. Your subscription will be activated shortly.</div>`;
    } else if (cancelled) {
      alertContainer.innerHTML = `<div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mb-4">Payment cancelled or failed.</div>`;
    } else {
      alertContainer.innerHTML = "";
    }
  }
  // Fetch current subscription
  const subRes = await apiRequest("/subscriptions/me");
  let currentSub = null;
  if (subRes.ok) {
    currentSub = await subRes.json();
  }
  const infoEl = document.getElementById("subscription-info");
  if (infoEl) {
    if (currentSub) {
      infoEl.innerHTML = `<p class="mb-2">Current plan: <strong>${currentSub.plan_id}</strong> (Status: ${currentSub.status})</p><button class="bg-red-500 text-white px-3 py-1 rounded" onclick="cancelSubscription()">Cancel Subscription</button>`;
    } else {
      infoEl.textContent = "You do not have an active subscription.";
    }
  }
  // Fetch available plans
  const plansRes = await apiRequest("/subscriptions/plans");
  if (plansRes.ok) {
    const plans = await plansRes.json();
    const container = document.getElementById("plans-container");
    if (container) {
      container.innerHTML = "";
      plans.forEach((p) => {
        const card = document.createElement("div");
        card.className = "border rounded shadow p-6 flex flex-col";
        const description = p.description || "";
        const price = p.price != null ? `$${p.price.toFixed(2)}/mo` : "";
        // Determine button label and action: if stripe_price_id is set then we need to redirect via checkout
        let buttonHtml;
        if (p.stripe_price_id) {
          buttonHtml = `<button class="mt-auto bg-indigo-600 text-white px-4 py-2 rounded" onclick="checkoutPlan('${p.id}')">Subscribe</button>`;
        } else {
          buttonHtml = `<button class="mt-auto bg-indigo-600 text-white px-4 py-2 rounded" onclick="subscribeToPlan('${p.id}')">Subscribe</button>`;
        }
        card.innerHTML = `
          <h3 class="text-xl font-semibold mb-2">${p.name}</h3>
          <p class="text-gray-600 mb-2">${description}</p>
          <p class="text-2xl font-bold mb-4">${price}</p>
          ${buttonHtml}
        `;
        container.appendChild(card);
      });
    }
  }
}

async function subscribeToPlan(planId) {
  const res = await apiRequest("/subscriptions/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan_id: planId }),
  });
  if (res.ok) {
    alert("Subscription successful");
    loadPricing();
  } else {
    alert("Subscription failed");
  }
}

// Redirect user to payment checkout for a plan.
async function checkoutPlan(planId) {
  // Create a checkout session via the backend.  The backend will
  // return a URL that we should redirect the user to.  Once payment is
  // completed the user will be returned to the pricing page and the
  // webhook will activate their subscription.
  const res = await apiRequest(`/subscriptions/checkout/${planId}`, {
    method: "POST",
  });
  if (res.ok) {
    const data = await res.json();
    if (data && data.url) {
      window.location.href = data.url;
    } else {
      alert("Unable to retrieve checkout URL.");
    }
  } else {
    const err = await res.json().catch(() => null);
    alert(err?.detail || "Failed to initiate checkout");
  }
}

async function cancelSubscription() {
  const confirmed = confirm("Cancel your current subscription?");
  if (!confirmed) return;
  const res = await apiRequest("/subscriptions/cancel", { method: "POST" });
  if (res.ok) {
    alert("Subscription cancelled");
    loadPricing();
  } else {
    alert("Failed to cancel subscription");
  }
}

/*
 * AI influencer matching functions
 */
async function loadMatchBrands() {
  // Populate the match brand selector with the current user's brands
  const sel = document.getElementById("match-brand-id");
  if (!sel) return;
  const res = await apiRequest("/brands");
  if (res.ok) {
    const brands = await res.json();
    sel.innerHTML = "";
    brands.forEach((b) => {
      const opt = document.createElement("option");
      opt.value = b.id;
      opt.textContent = b.name;
      sel.appendChild(opt);
    });
  }
}

async function findInfluencerMatches() {
  const brandId = document.getElementById("match-brand-id").value;
  if (!brandId) return;
  const res = await apiRequest(`/match/brand/${brandId}`);
  if (res.ok) {
    const matches = await res.json();
    const table = document.getElementById("matches-table");
    const wrapper = document.getElementById("match-results");
    table.innerHTML = "";
    matches.forEach((m) => {
      const row = document.createElement("tr");
      row.classList.add("border-b");
      row.innerHTML = `<td class="px-2 py-2">${m.name}</td>
                       <td class="px-2 py-2">${m.platform || ""}</td>
                       <td class="px-2 py-2">${m.followers || ""}</td>
                       <td class="px-2 py-2">${m.engagement_rate || ""}</td>
                       <td class="px-2 py-2 font-semibold">${(m.score * 100).toFixed(1)}%</td>
                       <td class="px-2 py-2 text-xs">${m.explanation}</td>`;
      table.appendChild(row);
    });
    wrapper.classList.remove("hidden");
  } else {
    alert("Failed to load matches");
  }
}

/*
 * Influencer discovery search.  Builds query parameters from search inputs
 * and fetches results from the /influencers/search endpoint.  Displays the
 * results in a table and shows the results container.
 */
async function searchInfluencers() {
  const q = document.getElementById("search-q")?.value.trim();
  const platform = document.getElementById("search-platform")?.value.trim();
  const minFollowers = document.getElementById("search-min-followers")?.value;
  const minEngagement = document.getElementById("search-min-engagement")?.value;
  const country = document.getElementById("search-country")?.value.trim();
  const topic = document.getElementById("search-topic")?.value.trim();
  const sortBy = document.getElementById("search-sort")?.value;
  const params = new URLSearchParams();
  if (q) params.append("q", q);
  if (platform) params.append("platform", platform);
  if (minFollowers) params.append("min_followers", minFollowers);
  if (minEngagement) params.append("min_engagement_rate", minEngagement);
  if (country) params.append("country", country);
  if (topic) params.append("topic", topic);
  if (sortBy) params.append("sort_by", sortBy);
  const res = await apiRequest(`/influencers/search?${params.toString()}`);
  if (res.ok) {
    const influencers = await res.json();
    const table = document.getElementById("search-results-table");
    const container = document.getElementById("search-results");
    table.innerHTML = "";
    influencers.forEach((i) => {
      const row = document.createElement("tr");
      row.classList.add("border-b");
      row.innerHTML = `<td class="px-2 py-2">${i.handle}</td>
                       <td class="px-2 py-2">${i.name}</td>
                       <td class="px-2 py-2 capitalize">${i.platform}</td>
                       <td class="px-2 py-2">${i.followers ?? ""}</td>
                       <td class="px-2 py-2">${i.engagement_rate ?? ""}</td>
                       <td class="px-2 py-2">${i.topics ?? ""}</td>
                       <td class="px-2 py-2">${i.country ?? ""}</td>`;
      table.appendChild(row);
    });
    container.classList.remove("hidden");
  } else {
    alert("Search failed");
  }
}
// Handle lead capture submission
async function handleLeadSubmit(event) {
  event.preventDefault();
  const name = document.getElementById("lead-name").value;
  const email = document.getElementById("lead-email").value;
  const company = document.getElementById("lead-company").value;
  const message = document.getElementById("lead-message").value;
  const res = await apiRequest("/leads/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, company, message }),
  });
  if (res.ok) {
    // hide form and show thank you
    document.getElementById("lead-form").reset();
    document.getElementById("lead-response").classList.remove("hidden");
  } else {
    alert("Failed to submit lead");
  }
}

async function analyseCampaign(id) {
  const confirmed = confirm("Run AI analysis on this campaign's brief?");
  if (!confirmed) return;
  const res = await apiRequest(`/campaigns/${id}/analyse`, { method: "POST" });
  if (res.ok) {
    const c = await res.json();
    // Show analysis in modal
    const modal = document.getElementById("analysis-modal");
    if (modal) {
      document.getElementById("analysis-content").textContent = c.analysis || "No analysis available.";
      modal.classList.remove("hidden");
    } else {
      alert("Analysis completed");
    }
    await loadCampaigns();
  } else {
    alert("Analysis failed");
  }
}

// Dashboard page logic: fetch summary counts and render chart
async function loadDashboard() {
  // Ensure user is logged in and display name
  await loadCurrentUser();
  // Fetch counts
  // Fetch counts concurrently.  Leads list may require admin/team privileges; treat
  // errors as zero leads.
  const [brandsRes, campaignsRes, influencersRes, leadsRes] = await Promise.all([
    apiRequest("/brands"),
    apiRequest("/campaigns"),
    apiRequest("/influencers"),
    apiRequest("/leads/"),
  ]);
  if (brandsRes.ok && campaignsRes.ok && influencersRes.ok) {
    const [brands, campaigns, influencers] = await Promise.all([
      brandsRes.json(),
      campaignsRes.json(),
      influencersRes.json(),
    ]);
    // update counts
    const countBrandsEl = document.getElementById("count-brands");
    if (countBrandsEl) countBrandsEl.textContent = brands.length;
    const countCampaignsEl = document.getElementById("count-campaigns");
    if (countCampaignsEl) countCampaignsEl.textContent = campaigns.length;
    const countInfluencersEl = document.getElementById("count-influencers");
    if (countInfluencersEl) countInfluencersEl.textContent = influencers.length;
    // update leads count if available
    if (leadsRes && leadsRes.ok) {
      const leads = await leadsRes.json();
      const countLeadsEl = document.getElementById("count-leads");
      if (countLeadsEl) countLeadsEl.textContent = leads.length;
    }
    // compute status distribution
    const statusCounts = {};
    campaigns.forEach((c) => {
      statusCounts[c.status] = (statusCounts[c.status] || 0) + 1;
    });
    // Setup chart if element exists
    const ctx = document.getElementById("status-chart");
    if (ctx && typeof Chart !== "undefined") {
      // Destroy existing chart if any
      if (window.statusChart) {
        window.statusChart.destroy();
      }
      const labels = Object.keys(statusCounts);
      const data = Object.values(statusCounts);
      window.statusChart = new Chart(ctx, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [
            {
              label: "Campaigns",
              data: data,
              backgroundColor: "rgba(99, 102, 241, 0.5)",
              borderColor: "rgba(99, 102, 241, 1)",
              borderWidth: 1,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              title: { display: true, text: "Number of campaigns" },
            },
            x: {
              title: { display: true, text: "Status" },
            },
          },
        },
      });
    }
  } else {
    // in case of error, redirect to login
    clearToken();
    window.location.href = "index.html";
  }
}

// Influencers page logic
async function loadInfluencers() {
  const table = document.getElementById("influencers-table");
  const res = await apiRequest("/influencers");
  if (res.ok) {
    const influencers = await res.json();
    table.innerHTML = "";
    influencers.forEach((i) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td class="border px-4 py-2">${i.handle}</td>
        <td class="border px-4 py-2 capitalize">${i.platform}</td>
        <td class="border px-4 py-2">${i.followers ?? ""}</td>
        <td class="border px-4 py-2">${i.engagement_rate ?? ""}</td>
        <td class="border px-4 py-2 text-sm space-x-2">
          <button class="text-blue-600 hover:underline" onclick="editInfluencer('${i.id}')">Edit</button>
          <button class="text-red-600 hover:underline" onclick="deleteInfluencer('${i.id}')">Delete</button>
        </td>`;
      table.appendChild(row);
    });
  }
}

async function editInfluencer(id) {
  const res = await apiRequest(`/influencers/${id}`);
  if (res.ok) {
    const i = await res.json();
    document.getElementById("influencer-id").value = i.id;
    document.getElementById("influencer-handle").value = i.handle;
    document.getElementById("influencer-name").value = i.name;
    document.getElementById("influencer-platform").value = i.platform;
    document.getElementById("influencer-followers").value = i.followers ?? "";
    document.getElementById("influencer-engagement").value = i.engagement_rate ?? "";
    document.getElementById("influencer-submit").textContent = "Update";
    document.getElementById("influencer-cancel").classList.remove("hidden");
  }
}

function cancelInfluencerEdit() {
  document.getElementById("influencer-form").reset();
  document.getElementById("influencer-id").value = "";
  document.getElementById("influencer-submit").textContent = "Save";
  document.getElementById("influencer-cancel").classList.add("hidden");
}

async function deleteInfluencer(id) {
  const confirmed = confirm("Are you sure you want to delete this influencer?");
  if (!confirmed) return;
  const res = await apiRequest(`/influencers/${id}`, { method: "DELETE" });
  if (res.ok) {
    await loadInfluencers();
  } else {
    alert("Failed to delete influencer");
  }
}

async function handleCreateInfluencer(event) {
  event.preventDefault();
  const id = document.getElementById("influencer-id").value;
  const handleVal = document.getElementById("influencer-handle").value;
  const name = document.getElementById("influencer-name").value;
  const platform = document.getElementById("influencer-platform").value;
  const followers = parseInt(document.getElementById("influencer-followers").value || "0", 10);
  const engagement_rate = parseFloat(document.getElementById("influencer-engagement").value || "0");
  const payload = {
    handle: handleVal,
    name,
    platform,
    followers: isNaN(followers) ? null : followers,
    engagement_rate: isNaN(engagement_rate) ? null : engagement_rate,
  };
  let res;
  if (id) {
    res = await apiRequest(`/influencers/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } else {
    res = await apiRequest("/influencers/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
  if (res.ok) {
    document.getElementById("influencer-form").reset();
    document.getElementById("influencer-id").value = "";
    document.getElementById("influencer-submit").textContent = "Save";
    document.getElementById("influencer-cancel").classList.add("hidden");
    await loadInfluencers();
  } else {
    alert("Failed to save influencer");
  }
}

// Initialisation based on page
document.addEventListener("DOMContentLoaded", () => {
  // Attach login handler
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", handleLogin);
  }
  // Attach logout handler
  const logoutBtn = document.getElementById("logout");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", handleLogout);
  }
  // Dashboard page
  if (document.getElementById("status-chart")) {
    loadDashboard();
  } else if (document.getElementById("user-name")) {
    // fallback for pages with user-name but no chart (e.g. simple dashboard)
    loadCurrentUser();
  }
  // Brands page
  if (document.getElementById("brands-table")) {
    loadCurrentUser();
    loadBrands();
    const brandForm = document.getElementById("brand-form");
    brandForm.addEventListener("submit", handleCreateBrand);
  }
  // Campaigns page
  if (document.getElementById("campaigns-table")) {
    loadCurrentUser();
    loadCampaigns();
    loadBrandsSelect();
    const campaignForm = document.getElementById("campaign-form");
    campaignForm.addEventListener("submit", handleCreateCampaign);
  }
  // Influencers page
  if (document.getElementById("influencers-table")) {
    loadCurrentUser();
    loadInfluencers();
    const infForm = document.getElementById("influencer-form");
    infForm.addEventListener("submit", handleCreateInfluencer);
  }

  // Pricing page
  if (document.getElementById("plans-container")) {
    loadPricing();
  }

  // Leads management page
  if (document.getElementById("leads-table")) {
    loadLeads();
  }
});