import { request } from './http';
import type {
    Collection,
    CollectionCollaborator,
    CreateCollectionPayload,
    TransferCollectionOwnershipPayload,
    UpdateCollectionPayload,
    UpsertCollectionCollaboratorPayload
} from '@/types/collection';
import type { CollectionPriceVariation, RefreshCollectionPricesResponse } from '@/types/pricing';

export function listCollections(permission: 'view' | 'edit' | 'manage' = 'view'): Promise<Collection[]> {
    const params = new URLSearchParams({ permission });
    return request<Collection[]>(`/collections?${params.toString()}`);
}

export function getCollection(id: number): Promise<Collection> {
    return request<Collection>(`/collections/${id}`);
}

export function createCollection(payload: CreateCollectionPayload): Promise<Collection> {
    return request<Collection>('/collections', {
        method: 'POST',
        json: payload
    });
}

export function updateCollection(id: number, payload: UpdateCollectionPayload): Promise<Collection> {
    return request<Collection>(`/collections/${id}`, {
        method: 'PATCH',
        json: payload
    });
}

export function deleteCollection(collectionId: number): Promise<void> {
    return request<void>(`/collections/${collectionId}`, {
        method: 'DELETE'
    });
}

export function refreshCollectionPrices(collectionId: number): Promise<RefreshCollectionPricesResponse> {
    return request<RefreshCollectionPricesResponse>(`/collections/${collectionId}/refresh-prices`, {
        method: 'POST'
    });
}

export function getCollectionPriceVariation(collectionId: number): Promise<CollectionPriceVariation> {
    return request<CollectionPriceVariation>(`/collections/${collectionId}/price-variation`);
}

export function listCollectionCollaborators(collectionId: number): Promise<CollectionCollaborator[]> {
    return request<CollectionCollaborator[]>(`/collections/${collectionId}/collaborators`);
}

export function upsertCollectionCollaborator(
    collectionId: number,
    payload: UpsertCollectionCollaboratorPayload
): Promise<CollectionCollaborator> {
    return request<CollectionCollaborator>(`/collections/${collectionId}/collaborators`, {
        method: 'POST',
        json: payload
    });
}

export function deleteCollectionCollaborator(collectionId: number, userId: number): Promise<void> {
    return request<void>(`/collections/${collectionId}/collaborators/${userId}`, {
        method: 'DELETE'
    });
}

export function transferCollectionOwnership(
    collectionId: number,
    payload: TransferCollectionOwnershipPayload
): Promise<Collection> {
    return request<Collection>(`/collections/${collectionId}/transfer-ownership`, {
        method: 'POST',
        json: payload
    });
}
