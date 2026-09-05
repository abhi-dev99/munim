// The backend's /api/v1/admin/* router requires this header (see
// ADMIN_API_KEY in backend/.env) since it has no per-user login of its
// own -- it's a shared dev/ops surface (Gemini key pool, system status,
// admin invoice delete), not something a trader or CA authenticates into.
// Exposed as NEXT_PUBLIC_* so it ships in the client bundle -- acceptable
// here since /dev is already an unauthenticated internal tool by design,
// not a boundary meant to hide this value from someone who can already
// reach the page.
export const adminHeaders = () => {
  const key = process.env.NEXT_PUBLIC_ADMIN_API_KEY;
  return key ? { "X-Admin-Key": key } : {};
};

export const authFetch = async (url, options = {}) => {
  options.cache = 'no-store';
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('munim_auth_token');
    if (token) {
      options.headers = {
        ...options.headers,
        Authorization: `Bearer ${token}`,
      };
    }
  }
  const res = await fetch(url, options);
  
  if (res.status === 401 && typeof window !== 'undefined') {
    // Prevent redirect loop if already on login page or dev portal
    if (window.location.pathname !== "/" && window.location.pathname !== "/dev") {
      localStorage.removeItem('munim_auth_token');
      localStorage.removeItem('munim_auth_trader');
      window.location.href = "/";
    }
  }
  
  return res;
};
