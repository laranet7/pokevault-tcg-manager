import { request } from './http';
import type { ChangePasswordPayload, LoginPayload, LoginResponse, User } from '@/types/user';

export function login(payload: LoginPayload): Promise<LoginResponse> {
    return request<LoginResponse>('/auth/login', {
        method: 'POST',
        json: payload
    });
}

export function getMe(): Promise<User> {
    return request<User>('/auth/me');
}

export function changePassword(payload: ChangePasswordPayload): Promise<User> {
    return request<User>('/auth/change-password', {
        method: 'POST',
        json: payload
    });
}
