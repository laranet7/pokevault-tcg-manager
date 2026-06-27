export interface CardPrice {
    source: string;
    currency: string;
    label: string;
    amount: number | string;
}

export interface CardSearchResult {
    external_id: string;
    api_source: string;
    name: string;
    number: string;
    set_id: string | null;
    set_name: string | null;
    printed_total: number | null;
    supertype: string | null;
    pokedex_number: number | null;
    rarity: string | null;
    image_small: string | null;
    image_large: string | null;
    prices: CardPrice[];
    raw_prices: Record<string, unknown>;
}

export interface CardSearchResponse {
    query: string;
    count: number;
    results: CardSearchResult[];
}

export interface CardRead {
    id: number;
    external_id: string;
    name: string;
    number: string;
    set_id: string | null;
    set_name: string | null;
    printed_total: number | null;
    supertype: string | null;
    pokedex_number: number | null;
    rarity: string | null;
    image_small: string | null;
    image_large: string | null;
    api_source: string;
    created_at: string;
    updated_at: string | null;
}

export interface CardUpsertPayload {
    external_id: string;
    name: string;
    number: string;
    set_id: string | null;
    set_name: string | null;
    printed_total: number | null;
    supertype: string | null;
    pokedex_number: number | null;
    rarity: string | null;
    image_small: string | null;
    image_large: string | null;
    api_source: string;
}
