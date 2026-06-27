export class ApiError extends Error {
    status: number;

    constructor(message: string, status: number) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
    }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const AUTH_STORAGE_KEY = 'pokevault:auth-session';

type JsonBody = Record<string, unknown> | Array<unknown>;

function buildHeaders(init: RequestInit = {}, accept = 'application/json'): Headers {
    const headers = new Headers(init.headers);
    headers.set('Accept', accept);

    if (typeof window !== 'undefined') {
        const rawSession = window.localStorage.getItem(AUTH_STORAGE_KEY);
        if (rawSession) {
            try {
                const session = JSON.parse(rawSession);
                if (session?.accessToken && !headers.has('Authorization')) {
                    headers.set('Authorization', `Bearer ${session.accessToken}`);
                }
            } catch {
                window.localStorage.removeItem(AUTH_STORAGE_KEY);
            }
        }
    }

    return headers;
}

function formatApiDetail(detail: unknown): string {
    if (typeof detail === 'string') {
        return detail;
    }

    if (Array.isArray(detail)) {
        const parts = detail
            .map((entry) => {
                if (!entry || typeof entry !== 'object') {
                    return String(entry);
                }

                const location = Array.isArray((entry as { loc?: unknown }).loc) ? (entry as { loc: unknown[] }).loc.join('.') : '';
                const message = 'msg' in entry ? String((entry as { msg?: unknown }).msg ?? '') : String(entry);
                return location ? `${location}: ${message}` : message;
            })
            .filter(Boolean);

        return parts.join(' | ') || 'La solicitud no paso la validacion.';
    }

    if (detail && typeof detail === 'object') {
        return JSON.stringify(detail);
    }

    return 'Request failed';
}

export async function request<T>(path: string, init: RequestInit & { json?: JsonBody } = {}): Promise<T> {
    const headers = buildHeaders(init);
    let body = init.body;
    if (init.json !== undefined) {
        if (!headers.has('Content-Type')) {
            headers.set('Content-Type', 'application/json');
        }
        body = JSON.stringify(init.json);
    }

    let response: Response;
    try {
        response = await fetch(`${API_BASE_URL}${path}`, {
            ...init,
            headers,
            body
        });
    } catch {
        throw new ApiError('No fue posible conectar con el servidor.', 0);
    }

    if (response.status === 204) {
        return undefined as T;
    }

    const payload = await response.json().catch(() => null);

    if (!response.ok) {
        const detail =
            (payload && typeof payload === 'object' && 'detail' in payload && formatApiDetail(payload.detail)) ||
            `Request failed with status ${response.status}`;
        throw new ApiError(detail, response.status);
    }

    return payload as T;
}

export async function requestBlob(path: string, init: RequestInit = {}): Promise<Blob> {
    const headers = buildHeaders(init, 'image/*');
    let response: Response;
    try {
        response = await fetch(`${API_BASE_URL}${path}`, {
            ...init,
            headers
        });
    } catch {
        throw new ApiError('No fue posible conectar con el servidor.', 0);
    }

    if (!response.ok) {
        let detail = `Request failed with status ${response.status}`;
        try {
            const payload = await response.json();
            if (payload && typeof payload === 'object' && 'detail' in payload) {
                detail = formatApiDetail(payload.detail);
            }
        } catch {
            // Ignored on purpose; keep generic detail for binary endpoints.
        }
        throw new ApiError(detail, response.status);
    }

    return await response.blob();
}
