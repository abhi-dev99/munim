# On-device PWA features — moved to a separate branch

The trader PWA (`/trader`) used to carry a bundle of on-device, browser-only
capabilities on top of the core WhatsApp/dashboard product: a photo
quality gate (blur/glare detection before upload), an offline upload
queue, on-device text-to-speech readout of the diagnosis, haptic feedback
on scan results, and on-device semantic HSN code matching.

That functionality has been moved off `main` and lives on the
`pwa/on-device-features` branch, preserved in full (code, tests, and this
doc's original version). It isn't part of the core product line going
forward — `main` is the WhatsApp-first GST compliance product; the
on-device PWA layer is a separate, optional extension.

To bring any of it back, check out `pwa/on-device-features` and
cherry-pick or diff against `main` from there.
