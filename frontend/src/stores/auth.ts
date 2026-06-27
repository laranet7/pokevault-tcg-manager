import { computed, reactive } from 'vue';
import { changePassword, getMe, login } from '@/api/authApi';
import type { ChangePasswordPayload, LoginPayload, User } from '@/types/user';
import { applyLayoutPreferencesForUser } from '@/layout/composables/layout';

export const AUTH_STORAGE_KEY = 'pokevault:auth-session';

type AuthSession = {
    accessToken: string;
    user: User;
};

const state = reactive<{
    initialized: boolean;
    accessToken: string | null;
    user: User | null;
}>({
    initialized: false,
    accessToken: null,
    user: null
});

let initializePromise: Promise<void> | null = null;

function readStoredSession(): AuthSession | null {
    if (typeof window === 'undefined') {
        return null;
    }

    const rawValue = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (!rawValue) {
        return null;
    }

    try {
        return JSON.parse(rawValue) as AuthSession;
    } catch {
        window.localStorage.removeItem(AUTH_STORAGE_KEY);
        return null;
    }
}

function persistSession(): void {
    if (typeof window === 'undefined') {
        return;
    }

    if (!state.accessToken || !state.user) {
        window.localStorage.removeItem(AUTH_STORAGE_KEY);
        return;
    }

    window.localStorage.setItem(
        AUTH_STORAGE_KEY,
        JSON.stringify({
            accessToken: state.accessToken,
            user: state.user
        })
    );
}

function setSession(session: AuthSession | null): void {
    state.accessToken = session?.accessToken ?? null;
    state.user = session?.user ?? null;
    persistSession();
    applyLayoutPreferencesForUser(state.user?.id ?? null);
}

async function refreshUser(): Promise<void> {
    if (!state.accessToken) {
        state.user = null;
        return;
    }

    try {
        const user = await getMe();
        state.user = user;
        persistSession();
        applyLayoutPreferencesForUser(user.id);
    } catch {
        setSession(null);
    }
}

export async function refreshCurrentUser(): Promise<void> {
    await refreshUser();
}

export async function ensureAuthReady(): Promise<void> {
    if (state.initialized) {
        return;
    }

    if (initializePromise) {
        return initializePromise;
    }

    initializePromise = (async () => {
        const session = readStoredSession();
        if (session) {
            state.accessToken = session.accessToken;
            state.user = session.user;
            await refreshUser();
        } else {
            applyLayoutPreferencesForUser(null);
        }

        state.initialized = true;
        initializePromise = null;
    })();

    return initializePromise;
}

export async function loginWithCredentials(payload: LoginPayload): Promise<User> {
    const response = await login(payload);
    setSession({
        accessToken: response.access_token,
        user: response.user
    });
    return response.user;
}

export async function changeCurrentPassword(payload: ChangePasswordPayload): Promise<User> {
    const user = await changePassword(payload);
    state.user = user;
    persistSession();
    applyLayoutPreferencesForUser(user.id);
    return user;
}

export function replaceCurrentUser(user: User): void {
    state.user = user;
    persistSession();
    applyLayoutPreferencesForUser(user.id);
}

export function logout(): void {
    setSession(null);
}

export function useAuth() {
    return {
        state,
        isAuthenticated: computed(() => Boolean(state.accessToken && state.user)),
        isAdmin: computed(() => Boolean(state.user?.is_admin)),
        mustChangePassword: computed(() => Boolean(state.user?.must_change_password))
    };
}
