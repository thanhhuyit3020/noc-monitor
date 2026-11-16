(() => {
  const messages = {
    vi: {language: "Ngôn ngữ", networkOperations: "VẬN HÀNH MẠNG", loginTitle: "Đăng nhập NOC Monitor", loginSubtitle: "Dùng tài khoản NOC để mở dashboard giám sát.", firstUse: "Lần đầu sử dụng", firstUseDescription: "Tạo Global Admin đầu tiên bằng PowerShell trong thư mục dự án:", username: "Tài khoản", password: "Mật khẩu", signIn: "Đăng nhập", loginFootnote: "Quyền truy cập do quản trị viên NOC quản lý.", apiNetworkError: "Không thể kết nối đến máy chủ NOC.", apiLoginFailed: "Đăng nhập thất bại.", apiUnableSignIn: "Không thể đăng nhập."},
    en: {language: "Language", networkOperations: "NETWORK OPERATIONS", loginTitle: "Sign in to NOC Monitor", loginSubtitle: "Use your NOC account to open the monitoring dashboard.", firstUse: "First use", firstUseDescription: "Create the first Global Admin from PowerShell in the project folder:", username: "Username", password: "Password", signIn: "Sign in", loginFootnote: "Access is managed by your NOC administrator.", apiNetworkError: "Unable to reach the NOC server.", apiLoginFailed: "Sign in failed.", apiUnableSignIn: "Unable to sign in."}
  };
  let language = localStorage.getItem("noc-language") || "vi";
  const t = key => messages[language][key] || messages.en[key] || key;
  const applyLanguage = () => {
    document.documentElement.lang = language;
    document.querySelectorAll("[data-i18n]").forEach(node => { node.textContent = t(node.dataset.i18n); });
    document.querySelectorAll("[data-i18n-aria-label]").forEach(node => node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel)));
    ["vi", "en"].forEach(code => { const button = document.querySelector("#lang-" + code); button.classList.toggle("active", code === language); button.setAttribute("aria-pressed", String(code === language)); });
  };
  ["vi", "en"].forEach(code => document.querySelector("#lang-" + code).addEventListener("click", () => { language = code; localStorage.setItem("noc-language", language); applyLanguage(); }));
  applyLanguage();
  const form = document.querySelector("#login-form");
  const error = document.querySelector("#auth-error");
  const setup = document.querySelector("#setup-notice");
  const submit = form.querySelector('button[type="submit"]');

  fetch("/api/auth/status", {credentials: "same-origin"})
    .then(response => response.json())
    .then(status => {
      if (status.bootstrap_required) {
        setup.hidden = false;
        form.hidden = true;
      }
    })
    .catch(() => { error.textContent = t("apiNetworkError"); error.hidden = false; });

  form.addEventListener("submit", async event => {
    event.preventDefault();
    error.hidden = true;
    submit.disabled = true;
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "same-origin",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username: form.elements.username.value, password: form.elements.password.value})
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || t("apiLoginFailed"));
      location.replace("/");
    } catch (failure) {
      error.textContent = failure.message || t("apiUnableSignIn");
      error.hidden = false;
      form.elements.password.value = "";
      form.elements.password.focus();
    } finally {
      submit.disabled = false;
    }
  });
})();
