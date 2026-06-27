<script setup lang="ts">
import type { Collection, CreateCollectionPayload, UpdateCollectionPayload } from '@/types/collection';
import { computed, reactive, watch } from 'vue';

const props = withDefaults(
    defineProps<{
        visible: boolean;
        collection?: Collection | null;
        mode?: 'create' | 'edit';
        saving?: boolean;
        canManageCollaborators?: boolean;
    }>(),
    {
        collection: null,
        mode: 'create',
        saving: false,
        canManageCollaborators: false
    }
);

const emit = defineEmits<{
    'update:visible': [value: boolean];
    save: [payload: CreateCollectionPayload | UpdateCollectionPayload];
    'manage-collaborators': [];
}>();

const dialogTitle = computed(() => (props.mode === 'edit' ? 'Configurar coleccion' : 'Nueva coleccion'));
const actionLabel = computed(() => (props.mode === 'edit' ? 'Guardar cambios' : 'Crear coleccion'));

const form = reactive<CreateCollectionPayload>({
    name: '',
    description: '',
    type: 'personal',
    is_public: false,
    sort_by_pokedex: false
});

function syncForm(): void {
    form.name = props.collection?.name ?? '';
    form.description = props.collection?.description ?? '';
    form.type = props.collection?.type ?? 'personal';
    form.is_public = props.collection?.is_public ?? false;
    form.sort_by_pokedex = props.collection?.sort_by_pokedex ?? false;
}

function closeDialog(): void {
    emit('update:visible', false);
}

function submit(): void {
    emit('save', {
        name: form.name.trim(),
        description: form.description?.trim() || null,
        type: form.type?.trim() || null,
        is_public: form.is_public ?? false,
        sort_by_pokedex: form.sort_by_pokedex ?? false
    });
}

watch(
    () => [props.visible, props.collection, props.mode],
    ([visible]) => {
        if (visible) {
            syncForm();
        }
    },
    { immediate: true }
);
</script>

<template>
    <Dialog :visible="props.visible" modal :header="dialogTitle" :style="{ width: '40rem' }" @update:visible="emit('update:visible', $event)">
        <div class="grid grid-cols-12 gap-4">
            <div class="col-span-12">
                <label class="block text-sm mb-2">Nombre</label>
                <InputText v-model="form.name" class="w-full" placeholder="Ej: General" />
            </div>
            <div class="col-span-12">
                <label class="block text-sm mb-2">Descripcion</label>
                <Textarea v-model="form.description" rows="4" class="w-full" />
            </div>
            <div class="col-span-12 md:col-span-6">
                <label class="block text-sm mb-2">Tipo</label>
                <InputText v-model="form.type" class="w-full" placeholder="personal, default, intercambio..." />
            </div>
            <div class="col-span-12 md:col-span-6">
                <div class="flex items-center gap-3 min-h-12 px-3 rounded-xl border border-surface-200 dark:border-surface-700 mt-6">
                    <ToggleSwitch v-model="form.is_public" />
                    <span>{{ form.is_public ? 'Coleccion publica' : 'Coleccion privada' }}</span>
                </div>
            </div>
            <div class="col-span-12">
                <div class="flex items-center gap-3 min-h-12 px-3 rounded-xl border border-surface-200 dark:border-surface-700">
                    <ToggleSwitch v-model="form.sort_by_pokedex" />
                    <div>
                        <div class="font-medium">Ordenar Pokemon por numero de Pokedex</div>
                        <div class="text-sm text-surface-500">Las cartas Pokemon se ordenan por Pokedex y las no Pokemon quedan al final.</div>
                    </div>
                </div>
            </div>
        </div>

        <template #footer>
            <div class="flex flex-col-reverse sm:flex-row sm:justify-between gap-3">
                <Button
                    v-if="props.mode === 'edit' && props.canManageCollaborators"
                    label="Colaboradores"
                    icon="pi pi-users"
                    severity="secondary"
                    outlined
                    @click="emit('manage-collaborators')"
                />
                <div class="flex justify-end gap-3">
                <Button label="Cancelar" severity="secondary" outlined @click="closeDialog" />
                <Button :label="actionLabel" icon="pi pi-save" :loading="props.saving" @click="submit" />
                </div>
            </div>
        </template>
    </Dialog>
</template>
