import { request } from './http';
import type {
    CollectionItem,
    CreateCollectionItemPayload,
    CreateCollectionItemWithImagePayload,
    CreateManualCollectionItemPayload,
    InventorySearchResult,
    MoveCollectionItemsPayload,
    MoveCollectionItemsResponse,
    UpdateCollectionItemPayload
} from '@/types/collectionItem';
import type { PriceHistoryEntry } from '@/types/pricing';

export function listCollectionItems(collectionId: number): Promise<CollectionItem[]> {
    return request<CollectionItem[]>(`/collections/${collectionId}/items`);
}

export function createCollectionItem(collectionId: number, payload: CreateCollectionItemPayload): Promise<CollectionItem> {
    return request<CollectionItem>(`/collections/${collectionId}/items`, {
        method: 'POST',
        json: payload
    });
}

export function createCollectionItemWithImage(collectionId: number, payload: CreateCollectionItemWithImagePayload): Promise<CollectionItem> {
    const formData = new FormData();

    appendFormValue(formData, 'external_id', payload.card.external_id);
    appendFormValue(formData, 'api_source', payload.card.api_source);
    appendFormValue(formData, 'name', payload.card.name);
    appendFormValue(formData, 'number', payload.card.number);
    appendFormValue(formData, 'set_id', payload.card.set_id);
    appendFormValue(formData, 'set_name', payload.card.set_name);
    appendFormValue(formData, 'printed_total', payload.card.printed_total);
    appendFormValue(formData, 'supertype', payload.card.supertype);
    appendFormValue(formData, 'pokedex_number', payload.card.pokedex_number);
    appendFormValue(formData, 'rarity', payload.card.rarity);
    appendFormValue(formData, 'image_small', payload.card.image_small);
    appendFormValue(formData, 'image_large', payload.card.image_large);
    appendFormValue(formData, 'quantity', payload.quantity);
    appendFormValue(formData, 'language', payload.language);
    appendFormValue(formData, 'condition', payload.condition);
    appendFormValue(formData, 'finish', payload.finish);
    appendFormValue(formData, 'pattern_variant', payload.pattern_variant);
    appendFormValue(formData, 'is_for_sale', payload.is_for_sale ?? false);
    appendFormValue(formData, 'base_price', payload.base_price);
    appendFormValue(formData, 'base_price_currency', payload.base_price_currency ?? 'USD');
    appendFormValue(formData, 'sale_margin_percent', payload.sale_margin_percent);
    appendFormValue(formData, 'sale_price', payload.sale_price);
    appendFormValue(formData, 'sale_status', payload.sale_status ?? 'not_available');
    appendFormValue(formData, 'notes', payload.notes);

    if (payload.image) {
        formData.append('image', payload.image);
    }

    return request<CollectionItem>(`/collections/${collectionId}/items/import`, {
        method: 'POST',
        body: formData
    });
}

function appendFormValue(formData: FormData, key: string, value: string | number | boolean | null | undefined): void {
    if (value === null || value === undefined || value === '') {
        return;
    }

    formData.append(key, String(value));
}

export function createManualCollectionItem(collectionId: number, payload: CreateManualCollectionItemPayload): Promise<CollectionItem> {
    const formData = new FormData();

    appendFormValue(formData, 'name', payload.card.name);
    appendFormValue(formData, 'number', payload.card.number);
    appendFormValue(formData, 'set_id', payload.card.set_id);
    appendFormValue(formData, 'set_name', payload.card.set_name);
    appendFormValue(formData, 'printed_total', payload.card.printed_total);
    appendFormValue(formData, 'supertype', payload.card.supertype);
    appendFormValue(formData, 'pokedex_number', payload.card.pokedex_number);
    appendFormValue(formData, 'rarity', payload.card.rarity);
    appendFormValue(formData, 'quantity', payload.quantity);
    appendFormValue(formData, 'language', payload.language);
    appendFormValue(formData, 'condition', payload.condition);
    appendFormValue(formData, 'finish', payload.finish);
    appendFormValue(formData, 'pattern_variant', payload.pattern_variant);
    appendFormValue(formData, 'is_for_sale', payload.is_for_sale ?? false);
    appendFormValue(formData, 'base_price', payload.base_price);
    appendFormValue(formData, 'base_price_currency', payload.base_price_currency ?? 'USD');
    appendFormValue(formData, 'sale_margin_percent', payload.sale_margin_percent);
    appendFormValue(formData, 'sale_price', payload.sale_price);
    appendFormValue(formData, 'sale_status', payload.sale_status ?? 'not_available');
    appendFormValue(formData, 'notes', payload.notes);

    if (payload.image) {
        formData.append('image', payload.image);
    }

    return request<CollectionItem>(`/collections/${collectionId}/items/manual`, {
        method: 'POST',
        body: formData
    });
}

export function updateCollectionItem(itemId: number, payload: UpdateCollectionItemPayload): Promise<CollectionItem> {
    return request<CollectionItem>(`/collection-items/${itemId}`, {
        method: 'PATCH',
        json: payload
    });
}

export function deleteCollectionItem(itemId: number): Promise<void> {
    return request<void>(`/collection-items/${itemId}`, {
        method: 'DELETE'
    });
}

export function moveCollectionItems(payload: MoveCollectionItemsPayload): Promise<MoveCollectionItemsResponse> {
    return request<MoveCollectionItemsResponse>('/collection-items/move', {
        method: 'POST',
        json: payload
    });
}

export function getCollectionItemPriceHistory(collectionItemId: number): Promise<PriceHistoryEntry[]> {
    return request<PriceHistoryEntry[]>(`/collection-items/${collectionItemId}/price-history`);
}

export function searchInventoryCards(query: string): Promise<InventorySearchResult[]> {
    const params = new URLSearchParams({ query });
    return request<InventorySearchResult[]>(`/collection-items/search?${params.toString()}`);
}
