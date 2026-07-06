<script setup lang="ts">
import { getCollectionsValuation } from '@/api/dashboardApi';
import { createCollection, listCollections, refreshCollectionPrices, updateCollection } from '@/api/collectionsApi';
import CollectionSettingsDialog from '@/components/collections/CollectionSettingsDialog.vue';
import type { Collection, CreateCollectionPayload, UpdateCollectionPayload } from '@/types/collection';
import type { CollectionValuation } from '@/types/pricing';
import { computed, onMounted, ref } from 'vue';
import type { MenuItem } from 'primevue/menuitem';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';

const router = useRouter();
const toast = useToast();
const loading = ref(true);
const saving = ref(false);
const collections = ref<Collection[]>([]);
const valuations = ref<CollectionValuation[]>([]);
const error = ref('');
const dialogVisible = ref(false);
const dialogMode = ref<'create' | 'edit'>('create');
const selectedCollection = ref<Collection | null>(null);
const optionsMenu = ref();
const bulkRefreshVisible = ref(false);
const bulkRefreshing = ref(false);
const bulkRefreshCurrentName = ref('');
const selectedRefreshCollectionIds = ref<number[]>([]);
const valuationsByCollection = computed(() =>
    Object.fromEntries(valuations.value.map((valuation) => [valuation.collection_id, valuation]))
);
const refreshableCollections = computed(() =>
    collections.value.filter((collection) => collection.can_edit && Number(collection.total_quantity || 0) > 0)
);
const bulkRefreshSelectionCount = computed(() => selectedRefreshCollectionIds.value.length);
const allRefreshableSelected = computed(
    () => refreshableCollections.value.length > 0 && selectedRefreshCollectionIds.value.length === refreshableCollections.value.length
);
const collectionOptions = computed<MenuItem[]>(() => [
    {
        label: 'Actualizar valorizacion',
        icon: 'pi pi-refresh',
        disabled: !refreshableCollections.value.length || bulkRefreshing.value,
        command: () => {
            openBulkRefreshDialog();
        }
    }
]);

function formatMoney(value: number | string | null | undefined, currency = 'USD'): string {
    return new Intl.NumberFormat('es-CL', {
        style: 'currency',
        currency,
        maximumFractionDigits: 2
    }).format(Number(value ?? 0));
}

function formatPercent(value: number | string | null | undefined): string {
    const amount = Number(value ?? 0);
    return `${amount > 0 ? '+' : ''}${amount.toFixed(2)}%`;
}

function variationSeverity(value: number | string | null | undefined): 'success' | 'danger' | 'secondary' {
    const amount = Number(value ?? 0);
    if (amount > 0) {
        return 'success';
    }
    if (amount < 0) {
        return 'danger';
    }
    return 'secondary';
}

async function loadCollections(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
        const [collectionsResponse, valuationsResponse] = await Promise.all([listCollections(), getCollectionsValuation()]);
        collections.value = collectionsResponse;
        valuations.value = valuationsResponse;
    } catch (err) {
        error.value = err instanceof Error ? err.message : 'No fue posible cargar las colecciones.';
        toast.add({ severity: 'error', summary: 'Error', detail: error.value, life: 4000 });
    } finally {
        loading.value = false;
    }
}

function openCreateDialog(): void {
    dialogMode.value = 'create';
    selectedCollection.value = null;
    dialogVisible.value = true;
}

function toggleOptionsMenu(event: Event): void {
    optionsMenu.value?.toggle(event);
}

function openBulkRefreshDialog(): void {
    selectedRefreshCollectionIds.value = refreshableCollections.value.map((collection) => collection.id);
    bulkRefreshVisible.value = true;
}

function closeBulkRefreshDialog(): void {
    if (bulkRefreshing.value) {
        return;
    }

    bulkRefreshVisible.value = false;
    bulkRefreshCurrentName.value = '';
}

function toggleSelectAllRefreshableCollections(): void {
    if (allRefreshableSelected.value) {
        selectedRefreshCollectionIds.value = [];
        return;
    }

    selectedRefreshCollectionIds.value = refreshableCollections.value.map((collection) => collection.id);
}

async function handleBulkRefreshPrices(): Promise<void> {
    if (!selectedRefreshCollectionIds.value.length) {
        toast.add({ severity: 'warn', summary: 'Seleccion requerida', detail: 'Elige una o mas colecciones para actualizar.', life: 3000 });
        return;
    }

    bulkRefreshing.value = true;
    let updatedCollections = 0;
    const failedCollections: string[] = [];
    let shouldCloseDialog = false;

    try {
        for (const collectionId of selectedRefreshCollectionIds.value) {
            const collection = refreshableCollections.value.find((entry) => entry.id === collectionId);
            if (!collection) {
                continue;
            }

            bulkRefreshCurrentName.value = collection.name;

            try {
                await refreshCollectionPrices(collection.id);
                updatedCollections += 1;
            } catch {
                failedCollections.push(collection.name);
            }
        }

        await loadCollections();

        if (updatedCollections > 0) {
            toast.add({
                severity: failedCollections.length ? 'warn' : 'success',
                summary: failedCollections.length ? 'Valorizacion parcial' : 'Valorizacion actualizada',
                detail: failedCollections.length
                    ? `${updatedCollections} colecciones actualizadas, ${failedCollections.length} con error.`
                    : `${updatedCollections} colecciones actualizadas correctamente.`,
                life: 5000
            });
        }

        if (failedCollections.length) {
            toast.add({
                severity: 'error',
                summary: 'Colecciones con error',
                detail: failedCollections.join(', '),
                life: 7000
            });
        }

        if (updatedCollections > 0 || failedCollections.length) {
            shouldCloseDialog = true;
        }
    } finally {
        bulkRefreshing.value = false;
        bulkRefreshCurrentName.value = '';
        if (shouldCloseDialog) {
            closeBulkRefreshDialog();
        }
    }
}

async function saveCollection(payload: CreateCollectionPayload | UpdateCollectionPayload): Promise<void> {
    if (!payload.name?.trim()) {
        toast.add({ severity: 'warn', summary: 'Nombre requerido', detail: 'Ingresa un nombre para la coleccion.', life: 3000 });
        return;
    }

    saving.value = true;
    try {
        if (dialogMode.value === 'create') {
            await createCollection(payload as CreateCollectionPayload);
            toast.add({ severity: 'success', summary: 'Coleccion creada', detail: 'La coleccion ya esta disponible.', life: 3000 });
        } else if (selectedCollection.value) {
            await updateCollection(selectedCollection.value.id, payload);
            toast.add({ severity: 'success', summary: 'Coleccion actualizada', detail: 'Los cambios fueron guardados.', life: 3000 });
        }

        dialogVisible.value = false;
        await loadCollections();
    } catch (err) {
        const detail = err instanceof Error ? err.message : 'No fue posible guardar la coleccion.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        saving.value = false;
    }
}

onMounted(loadCollections);
</script>

<template>
    <div class="flex flex-col gap-6">
        <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
                <div class="text-3xl font-semibold">Colecciones</div>
                <p class="text-surface-500 mb-0">Administra tus colecciones, su valor base y su valorizacion historica desde una sola tabla.</p>
            </div>
            <div class="flex items-center gap-3">
                <Tag :value="`${collections.length} colecciones`" severity="info" />
                <Button
                    icon="pi pi-ellipsis-v"
                    severity="secondary"
                    outlined
                    aria-label="Opciones"
                    @click="toggleOptionsMenu"
                />
                <Button label="Nueva coleccion" icon="pi pi-plus" @click="openCreateDialog" />
                <Menu ref="optionsMenu" :model="collectionOptions" popup />
            </div>
        </div>

        <Message v-if="error" severity="error">{{ error }}</Message>

        <div class="card">
            <DataTable :value="collections" :loading="loading" dataKey="id" paginator :rows="10" responsiveLayout="scroll" stripedRows>
                <template #empty>
                    <div class="text-center py-10">
                        <i class="pi pi-folder-open text-4xl text-surface-400 mb-4"></i>
                        <div class="text-2xl font-semibold mb-2">Todavia no hay colecciones</div>
                        <p class="text-surface-500 mb-4">Crea una nueva coleccion para empezar a organizar tus cartas.</p>
                        <Button label="Crear coleccion" icon="pi pi-plus" @click="openCreateDialog" />
                    </div>
                </template>

                <Column field="name" header="Coleccion" style="min-width: 14rem">
                    <template #body="{ data }">
                        <div>
                            <div class="font-semibold text-lg">{{ data.name }}</div>
                            <div class="text-surface-500">{{ data.description || 'Sin descripcion' }}</div>
                        </div>
                    </template>
                </Column>
                <Column field="type" header="Tipo" style="min-width: 10rem">
                    <template #body="{ data }">
                        <Tag :value="data.type || 'sin tipo'" severity="contrast" />
                    </template>
                </Column>
                <Column header="Valor base" style="min-width: 12rem">
                    <template #body="{ data }">
                        {{ formatMoney(valuationsByCollection[data.id]?.base_value, valuationsByCollection[data.id]?.currency || 'USD') }}
                    </template>
                </Column>
                <Column header="Valor venta" style="min-width: 12rem">
                    <template #body="{ data }">
                        {{ formatMoney(valuationsByCollection[data.id]?.sale_value, valuationsByCollection[data.id]?.currency || 'USD') }}
                    </template>
                </Column>
                <Column header="Variacion" style="min-width: 11rem">
                    <template #body="{ data }">
                        <Tag
                            v-if="valuationsByCollection[data.id]?.base_difference_percent !== null"
                            :value="formatPercent(valuationsByCollection[data.id]?.base_difference_percent)"
                            :severity="variationSeverity(valuationsByCollection[data.id]?.base_difference_percent)"
                        />
                        <span v-else class="text-surface-500">Sin historial</span>
                    </template>
                </Column>
                <Column header="Visibilidad" style="min-width: 10rem">
                    <template #body="{ data }">
                        <Tag :value="data.is_public ? 'Publica' : 'Privada'" :severity="data.is_public ? 'success' : 'secondary'" />
                    </template>
                </Column>
                <Column header="Orden" style="min-width: 12rem">
                    <template #body="{ data }">
                        <Tag :value="data.sort_by_pokedex ? 'Pokedex' : 'Manual'" :severity="data.sort_by_pokedex ? 'warn' : 'info'" />
                    </template>
                </Column>
                <Column field="items_count" header="Items" />
                <Column field="total_quantity" header="Cartas" />
                <Column header="Acciones" style="min-width: 6rem">
                    <template #body="{ data }">
                        <div class="flex">
                            <Button icon="pi pi-arrow-right" text rounded @click="router.push(`/collections/${data.id}`)" />
                        </div>
                    </template>
                </Column>
            </DataTable>
        </div>

        <CollectionSettingsDialog
            v-model:visible="dialogVisible"
            :collection="selectedCollection"
            :mode="dialogMode"
            :saving="saving"
            @save="saveCollection"
        />

        <Dialog
            v-model:visible="bulkRefreshVisible"
            modal
            header="Actualizar valorizacion"
            :style="{ width: 'min(92vw, 34rem)' }"
            :closable="!bulkRefreshing"
        >
            <div class="flex flex-col gap-4">
                <p class="text-surface-500 mb-0">
                    Elige las colecciones que quieres revalorizar en este momento. Se actualizaran una por una automaticamente.
                </p>

                <div class="flex items-center justify-between gap-3 rounded-xl border border-surface-200 dark:border-surface-700 px-4 py-3">
                    <div>
                        <div class="font-medium">Seleccion multiple</div>
                        <div class="text-sm text-surface-500">
                            {{ bulkRefreshSelectionCount }} de {{ refreshableCollections.length }} colecciones seleccionadas
                        </div>
                    </div>
                    <Button
                        :label="allRefreshableSelected ? 'Quitar todas' : 'Seleccionar todas'"
                        severity="secondary"
                        outlined
                        size="small"
                        @click="toggleSelectAllRefreshableCollections"
                    />
                </div>

                <Message v-if="!refreshableCollections.length" severity="info" :closable="false">
                    No hay colecciones editables con cartas para actualizar su valorizacion.
                </Message>

                <div
                    v-else
                    class="max-h-80 overflow-y-auto rounded-xl border border-surface-200 dark:border-surface-700 divide-y divide-surface-200 dark:divide-surface-700"
                >
                    <label
                        v-for="collection in refreshableCollections"
                        :key="collection.id"
                        class="flex items-start gap-3 px-4 py-3 cursor-pointer hover:bg-surface-50 dark:hover:bg-surface-900 transition-colors"
                    >
                        <Checkbox v-model="selectedRefreshCollectionIds" :value="collection.id" :inputId="`refresh-collection-${collection.id}`" />
                        <div class="min-w-0 flex-1">
                            <div class="font-medium">{{ collection.name }}</div>
                            <div class="text-sm text-surface-500">
                                {{ collection.total_quantity }} cartas
                                <span v-if="valuationsByCollection[collection.id]?.last_price_update">
                                    · Ultima actualizacion: {{ new Date(valuationsByCollection[collection.id].last_price_update).toLocaleString('es-CL') }}
                                </span>
                            </div>
                        </div>
                    </label>
                </div>

                <Message v-if="bulkRefreshing && bulkRefreshCurrentName" severity="info" :closable="false">
                    Actualizando: <strong>{{ bulkRefreshCurrentName }}</strong>
                </Message>
            </div>

            <template #footer>
                <div class="flex justify-end gap-3">
                    <Button label="Cancelar" severity="secondary" outlined :disabled="bulkRefreshing" @click="closeBulkRefreshDialog" />
                    <Button
                        label="Actualizar"
                        icon="pi pi-refresh"
                        :loading="bulkRefreshing"
                        :disabled="!refreshableCollections.length || !selectedRefreshCollectionIds.length"
                        @click="handleBulkRefreshPrices"
                    />
                </div>
            </template>
        </Dialog>
    </div>
</template>
