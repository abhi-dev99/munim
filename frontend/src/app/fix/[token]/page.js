import VendorFix from "./VendorFix";

export const metadata = {
  title: "An invoice needs your attention — Munim.ai",
  description: "Your customer cannot claim credit on one of your invoices until it is reported.",
  // This page is a capability URL handed to one supplier. It should never end
  // up in a search index, and a referrer leaking the token to whatever the
  // supplier taps next would defeat the point of expiring it.
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

/**
 * The supplier's page. No login, no account, one invoice.
 *
 * A Server Component only so that `params` — a Promise in Next 16 — is
 * awaited in the place designed for it. Everything interactive lives in
 * VendorFix, which is the client half.
 */
export default async function VendorFixPage({ params }) {
  const { token } = await params;
  return <VendorFix token={token} />;
}
