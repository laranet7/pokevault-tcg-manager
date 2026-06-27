import type { UserOption } from './user';

export interface Collection {
    id: number;
    name: string;
    description: string | null;
    type: string | null;
    is_public: boolean;
    sort_by_pokedex: boolean;
    owner_user_id: number | null;
    owner: UserOption | null;
    created_at: string;
    updated_at: string | null;
    items_count: number;
    total_quantity: number;
    current_user_role: 'owner' | 'viewer' | 'editor' | null;
    can_edit: boolean;
    can_manage: boolean;
}

export interface CreateCollectionPayload {
    name: string;
    description?: string | null;
    type?: string | null;
    is_public?: boolean;
    sort_by_pokedex?: boolean;
}

export interface UpdateCollectionPayload {
    name?: string | null;
    description?: string | null;
    type?: string | null;
    is_public?: boolean;
    sort_by_pokedex?: boolean;
}

export interface CollectionCollaborator {
    user_id: number;
    role: 'viewer' | 'editor';
    created_at: string;
    updated_at: string | null;
    user: UserOption;
}

export interface UpsertCollectionCollaboratorPayload {
    user_id: number;
    role: 'viewer' | 'editor';
}

export interface TransferCollectionOwnershipPayload {
    user_id: number;
}
