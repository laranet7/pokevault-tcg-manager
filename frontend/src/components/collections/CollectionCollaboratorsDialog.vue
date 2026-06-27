<script setup lang="ts">
import {
    deleteCollectionCollaborator,
    listCollectionCollaborators,
    transferCollectionOwnership,
    upsertCollectionCollaborator
} from '@/api/collectionsApi';
import { listUserOptions } from '@/api/usersApi';
import type { Collection, CollectionCollaborator } from '@/types/collection';
import type { UserOption } from '@/types/user';
import { computed, onMounted, ref, watch } from 'vue';
import { useToast } from 'primevue/usetoast';

const props = defineProps<{
    visible: boolean;
    collection: Collection | null;
}>();

const emit = defineEmits<{
    'update:visible': [value: boolean];
    changed: [collection?: Collection | null];
}>();

const toast = useToast();

const loading = ref(false);
const saving = ref(false);
const collaborators = ref<CollectionCollaborator[]>([]);
const userOptions = ref<UserOption[]>([]);
const selectedUserId = ref<number | null>(null);
const selectedRole = ref<'viewer' | 'editor'>('viewer');
const transferringToUserId = ref<number | null>(null);

const roleOptions = [
    { label: 'Viewer', value: 'viewer' },
    { label: 'Editor', value: 'editor' }
];

const ownerLabel = computed(() => {
    if (!props.collection?.owner) {
        return props.collection?.owner_user_id ? `Usuario #${props.collection.owner_user_id}` : 'Sin owner asignado';
    }
    return props.collection.owner.full_name ? `${props.collection.owner.username} · ${props.collection.owner.full_name}` : props.collection.owner.username;
});

const availableUserOptions = computed(() =>
    userOptions.value
        .filter((user) => user.id !== props.collection?.owner_user_id)
        .map((user) => ({
            label: user.full_name ? `${user.username} · ${user.full_name}` : user.username,
            value: user.id
        }))
);

const editorTransferOptions = computed(() =>
    collaborators.value
        .filter((collaborator) => collaborator.role === 'editor')
        .map((collaborator) => ({
            label: collaborator.user.full_name ? `${collaborator.user.username} · ${collaborator.user.full_name}` : collaborator.user.username,
            value: collaborator.user_id
        }))
);

async function loadData(): Promise<void> {
    if (!props.visible || !props.collection) {
        return;
    }

    loading.value = true;
    try {
        const [collaboratorsResponse, usersResponse] = await Promise.all([
            listCollectionCollaborators(props.collection.id),
            listUserOptions()
        ]);
        collaborators.value = collaboratorsResponse;
        userOptions.value = usersResponse;
        transferringToUserId.value = editorTransferOptions.value[0]?.value ?? null;
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible cargar los colaboradores.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        loading.value = false;
    }
}

async function addCollaborator(): Promise<void> {
    if (!props.collection || !selectedUserId.value) {
        toast.add({ severity: 'warn', summary: 'Datos incompletos', detail: 'Selecciona un usuario y un rol.', life: 3000 });
        return;
    }

    saving.value = true;
    try {
        await upsertCollectionCollaborator(props.collection.id, {
            user_id: selectedUserId.value,
            role: selectedRole.value
        });
        selectedUserId.value = null;
        selectedRole.value = 'viewer';
        await loadData();
        toast.add({ severity: 'success', summary: 'Colaborador guardado', detail: 'El acceso fue actualizado.', life: 3000 });
        emit('changed');
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible guardar el colaborador.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        saving.value = false;
    }
}

async function removeCollaborator(userId: number): Promise<void> {
    if (!props.collection) {
        return;
    }

    saving.value = true;
    try {
        await deleteCollectionCollaborator(props.collection.id, userId);
        await loadData();
        toast.add({ severity: 'success', summary: 'Colaborador eliminado', detail: 'El usuario ya no tiene acceso a la coleccion.', life: 3000 });
        emit('changed');
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible quitar el colaborador.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        saving.value = false;
    }
}

async function transferOwnership(): Promise<void> {
    if (!props.collection || !transferringToUserId.value) {
        toast.add({ severity: 'warn', summary: 'Seleccion requerida', detail: 'Elige un colaborador editor para transferir la coleccion.', life: 3000 });
        return;
    }

    saving.value = true;
    try {
        const updatedCollection = await transferCollectionOwnership(props.collection.id, { user_id: transferringToUserId.value });
        toast.add({ severity: 'success', summary: 'Owner transferido', detail: 'La coleccion ya fue transferida al colaborador seleccionado.', life: 3000 });
        emit('changed', updatedCollection);
        emit('update:visible', false);
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible transferir la coleccion.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        saving.value = false;
    }
}

watch(
    () => props.visible,
    async (visible) => {
        if (visible) {
            await loadData();
        }
    }
);

onMounted(async () => {
    if (props.visible) {
        await loadData();
    }
});
</script>

<template>
    <Dialog
        :visible="props.visible"
        modal
        header="Colaboradores"
        :style="{ width: 'min(52rem, 96vw)' }"
        @update:visible="emit('update:visible', $event)"
    >
        <div class="flex flex-col gap-6">
            <div class="rounded-2xl border border-surface-200 dark:border-surface-700 p-4">
                <div class="text-sm text-surface-500 mb-1">Owner actual</div>
                <div class="font-semibold">{{ ownerLabel }}</div>
            </div>

            <div class="grid grid-cols-12 gap-4">
                <div class="col-span-12 md:col-span-6">
                    <label class="block text-sm mb-2">Usuario</label>
                    <Select v-model="selectedUserId" :options="availableUserOptions" optionLabel="label" optionValue="value" class="w-full" filter />
                </div>
                <div class="col-span-12 md:col-span-4">
                    <label class="block text-sm mb-2">Rol</label>
                    <Select v-model="selectedRole" :options="roleOptions" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <div class="col-span-12 md:col-span-2 flex items-end">
                    <Button label="Agregar" icon="pi pi-plus" class="w-full" :loading="saving" @click="addCollaborator" />
                </div>
            </div>

            <div class="rounded-2xl border border-surface-200 dark:border-surface-700 p-4">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <div class="text-lg font-semibold">Colaboradores</div>
                        <p class="text-surface-500 mb-0">Los `viewer` solo ven. Los `editor` pueden modificar cartas y recibir ownership.</p>
                    </div>
                    <Tag :value="`${collaborators.length} colaboradores`" severity="info" />
                </div>

                <DataTable :value="collaborators" :loading="loading" dataKey="user_id" responsiveLayout="scroll">
                    <template #empty>
                        <div class="text-center py-6 text-surface-500">Todavia no hay colaboradores.</div>
                    </template>
                    <Column header="Usuario">
                        <template #body="{ data }">
                            <div>
                                <div class="font-medium">{{ data.user.username }}</div>
                                <div class="text-surface-500">{{ data.user.full_name || 'Sin nombre' }}</div>
                            </div>
                        </template>
                    </Column>
                    <Column header="Rol">
                        <template #body="{ data }">
                            <Tag :value="data.role" :severity="data.role === 'editor' ? 'warn' : 'secondary'" />
                        </template>
                    </Column>
                    <Column header="Acciones" style="width: 6rem">
                        <template #body="{ data }">
                            <Button icon="pi pi-trash" rounded text severity="danger" :loading="saving" @click="removeCollaborator(data.user_id)" />
                        </template>
                    </Column>
                </DataTable>
            </div>

            <div class="rounded-2xl border border-surface-200 dark:border-surface-700 p-4">
                <div class="text-lg font-semibold mb-1">Transferir coleccion</div>
                <p class="text-surface-500 mb-4">Solo puedes transferir la coleccion a un colaborador que ya tenga rol `editor`.</p>

                <div class="grid grid-cols-12 gap-4">
                    <div class="col-span-12 md:col-span-8">
                        <label class="block text-sm mb-2">Nuevo owner</label>
                        <Select v-model="transferringToUserId" :options="editorTransferOptions" optionLabel="label" optionValue="value" class="w-full" />
                    </div>
                    <div class="col-span-12 md:col-span-4 flex items-end">
                        <Button
                            label="Transferir"
                            icon="pi pi-arrow-right-arrow-left"
                            severity="warn"
                            class="w-full"
                            :disabled="!transferringToUserId"
                            :loading="saving"
                            @click="transferOwnership"
                        />
                    </div>
                </div>
            </div>
        </div>
    </Dialog>
</template>
