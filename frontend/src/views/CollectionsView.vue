<script setup lang="ts">
import { getCollectionsValuation } from '@/api/dashboardApi';
import { createCollection, listCollections, updateCollection } from '@/api/collectionsApi';
import CollectionSettingsDialog from '@/components/collections/CollectionSettingsDialog.vue';
import type { Collection, CreateCollectionPayload, UpdateCollectionPayload } from '@/types/collection';
import type { CollectionValuation } from '@/types/pricing';
import { computed, onMounted, ref } from 'vue';
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
const valuationsByCollection = computed(() =>
    Object.fromEntries(valuations.value.map((valuation) => [valuation.collection_id, valuation]))
);

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
                <Button label="Nueva coleccion" icon="pi pi-plus" @click="openCreateDialog" />
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
    </div>
</template>
