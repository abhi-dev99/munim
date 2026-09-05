// The backend returns a ready-made wa.me deep link
// (https://wa.me/<number>?text=JOIN-<short_code>) -- this just pulls the
// human-typeable short_code back out of it, for a fallback display next to
// the QR code when scanning isn't an option.
const JOIN_CODE_IN_LINK = /[?&]text=JOIN-([A-Za-z0-9]+)/i;

export function extractJoinCode(deepLink) {
  if (!deepLink) return null;
  const match = deepLink.match(JOIN_CODE_IN_LINK);
  return match ? match[1].toUpperCase() : null;
}
