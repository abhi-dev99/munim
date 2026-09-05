import "fake-indexeddb/auto";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { queueUpload, getQueuedUploads, removeQueuedUpload } from "./offlineQueue.js";

const DB_NAME = "munim-offline-queue";

// Each test starts from an empty queue — fake-indexeddb's global `indexedDB`
// instance persists across tests in the same module, so drop the database
// between tests rather than relying on ordering.
function resetDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.deleteDatabase(DB_NAME);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
    request.onblocked = () => resolve();
  });
}

beforeEach(resetDatabase);
afterEach(resetDatabase);

function makeFile(content, name, type) {
  const blob = new Blob([content], { type });
  return new File([blob], name, { type });
}

async function blobText(blob) {
  const buf = await blob.arrayBuffer();
  return Buffer.from(buf).toString("utf-8");
}

describe("getQueuedUploads", () => {
  it("returns an empty array when nothing is queued", async () => {
    expect(await getQueuedUploads()).toEqual([]);
  });
});

describe("queueUpload", () => {
  it("stores a file and metadata, retrievable via getQueuedUploads", async () => {
    const file = makeFile("invoice-bytes", "invoice.jpg", "image/jpeg");
    await queueUpload(file, { trader_id: "trader-1" });

    const queued = await getQueuedUploads();
    expect(queued).toHaveLength(1);
    expect(queued[0].metadata).toEqual({ trader_id: "trader-1" });
    expect(queued[0].fileName).toBe("invoice.jpg");
    expect(queued[0].file.type).toBe("image/jpeg");
    expect(await blobText(queued[0].file)).toBe("invoice-bytes");
  });

  it("assigns each queued item its own id", async () => {
    const idA = await queueUpload(makeFile("a", "a.jpg", "image/jpeg"), { trader_id: "t1" });
    const idB = await queueUpload(makeFile("b", "b.jpg", "image/jpeg"), { trader_id: "t1" });
    expect(idA).not.toBe(idB);
  });

  it("returns multiple queued uploads oldest-first", async () => {
    await queueUpload(makeFile("first", "1.jpg", "image/jpeg"), { trader_id: "t1" });
    await queueUpload(makeFile("second", "2.jpg", "image/jpeg"), { trader_id: "t1" });
    await queueUpload(makeFile("third", "3.jpg", "image/jpeg"), { trader_id: "t1" });

    const queued = await getQueuedUploads();
    expect(queued.map((q) => q.fileName)).toEqual(["1.jpg", "2.jpg", "3.jpg"]);
  });
});

describe("removeQueuedUpload", () => {
  it("removes only the specified item, leaving the rest queued", async () => {
    const idA = await queueUpload(makeFile("a", "a.jpg", "image/jpeg"), { trader_id: "t1" });
    const idB = await queueUpload(makeFile("b", "b.jpg", "image/jpeg"), { trader_id: "t1" });

    await removeQueuedUpload(idA);

    const queued = await getQueuedUploads();
    expect(queued).toHaveLength(1);
    expect(queued[0].id).toBe(idB);
  });

  it("is a no-op when the id does not exist", async () => {
    await expect(removeQueuedUpload(999)).resolves.toBeUndefined();
    expect(await getQueuedUploads()).toEqual([]);
  });
});
