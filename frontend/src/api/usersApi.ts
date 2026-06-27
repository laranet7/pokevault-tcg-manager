import { request } from './http';
import type { CreateUserPayload, UpdateSelfPayload, UpdateUserPayload, User, UserOption } from '@/types/user';

export function listUsers(): Promise<User[]> {
    return request<User[]>('/users');
}

export function listUserOptions(): Promise<UserOption[]> {
    return request<UserOption[]>('/users/options');
}

export function createUser(payload: CreateUserPayload): Promise<User> {
    return request<User>('/users', {
        method: 'POST',
        json: payload
    });
}

export function updateUser(userId: number, payload: UpdateUserPayload): Promise<User> {
    return request<User>(`/users/${userId}`, {
        method: 'PATCH',
        json: payload
    });
}

export function updateMe(payload: UpdateSelfPayload): Promise<User> {
    return request<User>('/users/me', {
        method: 'PATCH',
        json: payload
    });
}
