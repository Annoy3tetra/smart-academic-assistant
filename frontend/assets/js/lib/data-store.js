import { apiRequest } from "./backend-client.js";

function isIsoDateString(value) {
    if (typeof value !== "string") return false;
    const date = new Date(value);
    return Number.isFinite(date.getTime()) && value.includes("T");
}

function shouldWrapAsTimestamp(key, value) {
    if (!isIsoDateString(value)) return false;
    const normalized = String(key || "");
    return /(_at|At)$/i.test(normalized);
}

function makeTimestamp(value) {
    const date = new Date(value);
    return {
        toDate: () => new Date(date.getTime()),
        toMillis: () => date.getTime(),
        toString: () => date.toISOString(),
        toJSON: () => date.toISOString(),
    };
}

function normalizeReadValue(value, keyHint = "") {
    if (Array.isArray(value)) {
        return value.map((item) => normalizeReadValue(item, keyHint));
    }
    if (value && typeof value === "object") {
        const out = {};
        Object.entries(value).forEach(([key, nested]) => {
            out[key] = normalizeReadValue(nested, key);
        });
        return out;
    }
    if (shouldWrapAsTimestamp(keyHint, value)) {
        return makeTimestamp(value);
    }
    return value;
}

function normalizeWriteValue(value) {
    if (Array.isArray(value)) {
        return value.map((item) => normalizeWriteValue(item));
    }

    if (value && typeof value === "object") {
        if (value.__server_timestamp__ === true && Object.keys(value).length === 1) {
            return value;
        }

        if (typeof value.toDate === "function") {
            const date = value.toDate();
            return Number.isFinite(date?.getTime?.()) ? date.toISOString() : null;
        }

        const out = {};
        Object.entries(value).forEach(([key, nested]) => {
            out[key] = normalizeWriteValue(nested);
        });
        return out;
    }

    if (value instanceof Date) {
        return value.toISOString();
    }

    return value;
}

class AppDocSnapshot {
    constructor(id, data, exists) {
        this.id = id;
        this._data = data ?? {};
        this._exists = Boolean(exists);
    }

    exists() {
        return this._exists;
    }

    data() {
        return normalizeReadValue(this._data);
    }
}

class AppQuerySnapshot {
    constructor(documents) {
        this.docs = documents;
        this.empty = documents.length === 0;
    }

    forEach(callback) {
        this.docs.forEach((docSnap) => callback(docSnap));
    }
}

function buildCollectionPath(collectionRef) {
    return `/data/collections/${encodeURIComponent(collectionRef.collection)}`;
}

function buildDocPath(docRef) {
    return `/data/docs/${encodeURIComponent(docRef.collection)}/${encodeURIComponent(docRef.id)}`;
}

export function getDataStore() {
    return {};
}

export function collection(db, collectionName) {
    return {
        type: "collection",
        collection: String(collectionName),
    };
}

export function doc(db, collectionName, id) {
    return {
        type: "doc",
        collection: String(collectionName),
        id: String(id),
    };
}

export function where(fieldPath, opStr, value) {
    return {
        type: "where",
        fieldPath: String(fieldPath),
        opStr: String(opStr),
        value: String(value),
    };
}

export function query(collectionRef, ...constraints) {
    return {
        type: "query",
        collection: String(collectionRef.collection),
        constraints,
    };
}

export async function getDoc(docRef) {
    const response = await apiRequest(buildDocPath(docRef), { method: "GET", auth: true });
    return new AppDocSnapshot(docRef.id, response?.data ?? {}, response?.exists);
}

export async function setDoc(docRef, data, options = {}) {
    const payload = {
        data: normalizeWriteValue(data ?? {}),
        merge: Boolean(options?.merge),
    };
    return apiRequest(buildDocPath(docRef), {
        method: "PUT",
        auth: true,
        body: payload,
    });
}

export async function addDoc(collectionRef, data) {
    const response = await apiRequest(buildCollectionPath(collectionRef), {
        method: "POST",
        auth: true,
        body: { data: normalizeWriteValue(data ?? {}) },
    });
    return { id: response?.id };
}

export async function getDocs(ref) {
    let path = "";
    if (ref?.type === "collection") {
        path = buildCollectionPath(ref);
    } else if (ref?.type === "query") {
        const whereConstraint = (ref.constraints || []).find((item) => item?.type === "where");
        const params = new URLSearchParams();
        if (whereConstraint) {
            params.set("where_field", whereConstraint.fieldPath);
            params.set("where_op", whereConstraint.opStr);
            params.set("where_value", whereConstraint.value);
        }
        const suffix = params.toString();
        path = `${buildCollectionPath(ref)}${suffix ? `?${suffix}` : ""}`;
    } else {
        throw new Error("Unsupported getDocs reference");
    }

    const response = await apiRequest(path, { method: "GET", auth: true });
    const docs = Array.isArray(response?.documents) ? response.documents : [];
    return new AppQuerySnapshot(
        docs.map((item) => new AppDocSnapshot(item.id, item.data ?? {}, true))
    );
}

export async function deleteDoc(docRef) {
    return apiRequest(buildDocPath(docRef), {
        method: "DELETE",
        auth: true,
    });
}

export function serverTimestamp() {
    return { __server_timestamp__: true };
}

export function onSnapshot(docRef, onNext, onError) {
    let stopped = false;
    let lastSerialized = null;

    const tick = async () => {
        try {
            const response = await apiRequest(buildDocPath(docRef), { method: "GET", auth: true });
            const serialized = JSON.stringify(response?.data ?? null);
            if (serialized !== lastSerialized) {
                lastSerialized = serialized;
                onNext(new AppDocSnapshot(docRef.id, response?.data ?? {}, response?.exists));
            }
        } catch (error) {
            if (typeof onError === "function") {
                onError(error);
            }
        }
    };

    tick();
    const timer = window.setInterval(() => {
        if (!stopped) tick();
    }, 4000);

    return () => {
        stopped = true;
        window.clearInterval(timer);
    };
}
