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
