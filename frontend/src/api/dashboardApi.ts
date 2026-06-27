import { request } from './http';
import type { CollectionValuation, DashboardPriceMovers } from '@/types/pricing';

export function getCollectionsValuation(): Promise<CollectionValuation[]> {
    return request<CollectionValuation[]>('/dashboard/collections-valuation');
}

export function getDashboardPriceMovers(days = 30): Promise<DashboardPriceMovers> {
    const params = new URLSearchParams({ days: String(days) });
    return request<DashboardPriceMovers>(`/dashboard/price-movers?${params.toString()}`);
}
