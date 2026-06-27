export interface CollectionValuation {
    collection_id: number;
    collection_name: string;
    total_items: number;
    total_quantity: number;
    base_value: number | string;
    sale_value: number | string;
    currency: string;
    last_price_update: string | null;
    base_difference: number | string | null;
    base_difference_percent: number | string | null;
}

export interface DashboardPriceMover {
    collection_item_id: number;
    collection_id: number;
    collection_name: string;
    card_id: number;
    card_name: string;
    card_number: string;
    set_name: string | null;
    image_small: string | null;
    image_large: string | null;
    previous_price: number | string;
    current_price: number | string;
    difference: number | string;
    difference_percent: number | string;
    currency: string;
    from_captured_at: string;
    to_captured_at: string;
    trend: 'up' | 'down';
}

export interface DashboardPriceMovers {
    period_days: number;
    top_gainers: DashboardPriceMover[];
    top_losers: DashboardPriceMover[];
}

export interface RefreshCollectionPricesResponse {
    collection_id: number;
    collection_name: string;
    processed_items: number;
    updated_items: number;
    items_without_price: number;
    items_failed: number;
    base_value: number | string;
    sale_value: number | string;
    currency: string;
    captured_at: string;
}

export interface PriceHistoryEntry {
    captured_at: string;
    base_price: number | string | null;
    sale_price: number | string | null;
    currency: string;
}

export interface CollectionItemVariation {
    collection_item_id: number;
    card_name: string;
    previous_price: number | string | null;
    current_price: number | string | null;
    difference: number | string | null;
    difference_percent: number | string | null;
    previous_total: number | string | null;
    current_total: number | string | null;
    currency: string;
    trend: 'up' | 'down' | 'equal' | 'no_history';
}

export interface CollectionPriceVariation {
    collection_id: number;
    collection_name: string;
    total_items: number;
    items_up: number;
    items_down: number;
    items_equal: number;
    items_without_history: number;
    total_previous_base_value: number | string;
    total_current_base_value: number | string;
    total_difference: number | string;
    total_difference_percent: number | string | null;
    top_increases: CollectionItemVariation[];
    top_decreases: CollectionItemVariation[];
    item_variations: CollectionItemVariation[];
}
