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
  return fetch(url, options);
};
