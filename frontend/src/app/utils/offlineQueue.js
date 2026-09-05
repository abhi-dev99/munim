/**
 * IndexedDB-backed queue for invoice uploads captured with no connectivity.
 *
 * Why this exists: `handleInvoiceUpload` in trader/page.js posts a photo
 * straight to the backend. On a patchy connection (the exact condition this
 * product is built for — see CLAUDE.md's positioning section) that POST
 * throws and, before this module, the captured photo was just gone; the
 * trader had to remember to retake and resend it later. Queuing the raw
 * bytes + upload metadata locally means a captured invoice survives a lost
 * connection and drains automatically once it returns.
 *
 * IndexedDB (not localStorage) because the payload is an image Blob —
 * localStorage's string-only, ~5MB-quota API isn't a fit for that, and
 * IndexedDB is natively supported with no added dependency. Every function
 * here is a plain async function over the native `indexedDB` API — no
 * wrapper library — so the module is trivial to unit test (via
 * fake-indexeddb in Node) and to reason about.
 */

const DB_NAME = "munim-offline-queue";
const DB_VERSION = 1;
const STORE_NAME = "uploads";

function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id", autoIncrement: true });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Queue a file for later upload. Stored as raw bytes (ArrayBuffer) rather
 * than the File/Blob object directly — IndexedDB's structured-clone support
 * for Blob varies across browser versions, while ArrayBuffer is universally
 * safe to persist and is trivially wrapped back into a Blob on read.
 * @param {File|Blob} file
 * @param {object} metadata - whatever handleInvoiceUpload sends alongside the file (e.g. { trader_id })
 * @returns {Promise<number>} the queued record's id
 */
export async function queueUpload(file, metadata) {
  const fileData = await file.arrayBuffer();
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const request = tx.objectStore(STORE_NAME).add({
      fileData,
      fileName: file.name || "invoice",
      fileType: file.type || "application/octet-stream",
      metadata,
      queuedAt: Date.now(),
    });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    tx.oncomplete = () => db.close();
  });
}

/**
 * All queued uploads, oldest first (the order they should be retried in).
 * @returns {Promise<Array<{id: number, file: Blob, fileName: string, metadata: object, queuedAt: number}>>}
 */
export async function getQueuedUploads() {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const request = tx.objectStore(STORE_NAME).getAll();
    request.onsuccess = () => {
      const records = request.result
        .map((record) => ({
          id: record.id,
          file: new Blob([record.fileData], { type: record.fileType }),
          fileName: record.fileName,
          metadata: record.metadata,
          queuedAt: record.queuedAt,
        }))
        .sort((a, b) => a.queuedAt - b.queuedAt);
      resolve(records);
    };
    request.onerror = () => reject(request.error);
    tx.oncomplete = () => db.close();
  });
}

/**
 * Remove one queued upload, e.g. after it has successfully drained.
 * @param {number} id
 * @returns {Promise<void>}
 */
export async function removeQueuedUpload(id) {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).delete(id);
    tx.oncomplete = () => {
      db.close();
      resolve();
    };
    tx.onerror = () => reject(tx.error);
  });
}
