import type { CardRead, CardUpsertPayload } from './card';

export interface CollectionItem {
    id: number;
    collection_id: number;
    card_id: number;
    quantity: number;
    language: string | null;
    condition: string | null;
    finish: string | null;
    is_pokeball: boolean;
    is_for_sale: boolean;
    base_price: number | string | null;
    base_price_currency: string;
    tcgplayer_price: number | string | null;
    tcgplayer_currency: string | null;
    tcgplayer_price_label: string | null;
    cardmarket_price: number | string | null;
    cardmarket_currency: string | null;
    cardmarket_price_label: string | null;
    sale_margin_percent: number | string | null;
    sale_price: number | string | null;
    sale_status: string | null;
    notes: string | null;
    created_at: string;
    updated_at: string | null;
    card: CardRead;
}

export interface CollectionItemPayload {
    quantity: number;
    language?: string | null;
    condition?: string | null;
    finish?: string | null;
    is_pokeball?: boolean;
    is_for_sale?: boolean;
    base_price?: number | null;
    base_price_currency?: string;
    sale_margin_percent?: number | null;
    sale_price?: number | null;
    sale_status?: string | null;
    notes?: string | null;
}

export interface CreateCollectionItemPayload extends CollectionItemPayload {
    card: CardUpsertPayload;
}

export interface CreateCollectionItemWithImagePayload extends CollectionItemPayload {
    card: CardUpsertPayload;
    image?: File | null;
}

export interface InventorySearchResult {
    item_id: number;
    collection_id: number;
    collection_name: string;
    quantity: number;
    language: string | null;
    condition: string | null;
    finish: string | null;
    is_pokeball: boolean;
    is_for_sale: boolean;
    base_price: number | string | null;
    base_price_currency: string;
    sale_price: number | string | null;
    sale_status: string | null;
    notes: string | null;
    card: CardRead;
}

export interface ManualCardPayload {
    name: string;
    number: string;
    set_id?: string | null;
    set_name?: string | null;
    printed_total?: number | null;
    supertype?: string | null;
    pokedex_number?: number | null;
    rarity?: string | null;
}

export interface CreateManualCollectionItemPayload extends CollectionItemPayload {
    card: ManualCardPayload;
    image?: File | null;
}

export interface UpdateCollectionItemPayload extends Partial<CollectionItemPayload> {}

export interface MoveCollectionItemsPayload {
    item_ids: number[];
    target_collection_id: number;
}

export interface MoveCollectionItemsResponse {
    moved_items: number;
    merged_items: number;
    target_collection_id: number;
}
