import { request } from './http';
import type { CardSearchResponse } from '@/types/card';

export function searchCards(filters: { general?: string; code?: string; name?: string; promo_code?: string; promo_name?: string }): Promise<CardSearchResponse> {
    const params = new URLSearchParams();
    if (filters.general) {
        params.set('general', filters.general);
    }
    if (filters.code) {
        params.set('code', filters.code);
    }
    if (filters.name) {
        params.set('name', filters.name);
    }
    if (filters.promo_code) {
        params.set('promo_code', filters.promo_code);
    }
    if (filters.promo_name) {
        params.set('promo_name', filters.promo_name);
    }
    return request<CardSearchResponse>(`/cards/search?${params.toString()}`);
}
