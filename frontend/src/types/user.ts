export interface User {
    id: number;
    username: string;
    full_name: string | null;
    email: string | null;
    is_admin: boolean;
    is_active: boolean;
    must_change_password: boolean;
    terms_accepted_at: string | null;
    terms_version: string | null;
    created_at: string;
    updated_at: string | null;
}

export interface UserOption {
    id: number;
    username: string;
    full_name: string | null;
}

export interface LoginPayload {
    username: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
    user: User;
}

export interface ChangePasswordPayload {
    current_password: string;
    new_password: string;
}

export interface CreateUserPayload {
    username: string;
    full_name?: string | null;
    email?: string | null;
    password: string;
    is_admin?: boolean;
    is_active?: boolean;
}

export interface UpdateUserPayload {
    username?: string | null;
    full_name?: string | null;
    email?: string | null;
    password?: string | null;
    is_admin?: boolean;
    is_active?: boolean;
    must_change_password?: boolean;
}

export interface UpdateSelfPayload {
    username?: string | null;
    full_name?: string | null;
    email?: string | null;
}
