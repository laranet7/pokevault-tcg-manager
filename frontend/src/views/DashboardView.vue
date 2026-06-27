<script setup lang="ts">
import { getCollectionsValuation, getDashboardPriceMovers } from '@/api/dashboardApi';
import { requestBlob } from '@/api/http';
import { listCollections } from '@/api/collectionsApi';
import CollectionItemPriceHistoryDialog from '@/components/collections/CollectionItemPriceHistoryDialog.vue';
import type { Collection } from '@/types/collection';
import type { CollectionValuation, DashboardPriceMover, DashboardPriceMovers } from '@/types/pricing';
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';

const router = useRouter();
const toast = useToast();
const loading = ref(true);
const collections = ref<Collection[]>([]);
const valuations = ref<CollectionValuation[]>([]);
const movers = ref<DashboardPriceMovers | null>(null);
const error = ref('');
const localImageUrls = ref<Record<string, string>>({});
const objectUrls = new Set<string>();
const priceHistoryVisible = ref(false);
const selectedMover = ref<DashboardPriceMover | null>(null);
const selectedMoverPeriod = ref<7 | 30 | 90>(30);
const moversLoading = ref(false);

const totalCollections = computed(() => collections.value.length);
const totalCards = computed(() => collections.value.reduce((sum, collection) => sum + Number(collection.total_quantity || 0), 0));
const estimatedValue = computed(() =>
    valuations.value.reduce((sum, collection) => {
        return sum + Number(collection.sale_value ?? collection.base_value ?? 0);
    }, 0)
);
const forSaleCount = computed(() =>
    valuations.value.reduce((sum, collection) => {
        const saleValue = Number(collection.sale_value ?? 0);
        return sum + (saleValue > 0 ? 1 : 0);
    }, 0)
);
const totalBaseValue = computed(() => valuations.value.reduce((sum, collection) => sum + Number(collection.base_value ?? 0), 0));
const totalSaleValue = computed(() => valuations.value.reduce((sum, collection) => sum + Number(collection.sale_value ?? 0), 0));
const periodDays = computed(() => movers.value?.period_days ?? 30);
const topGainers = computed(() => movers.value?.top_gainers ?? []);
const topLosers = computed(() => movers.value?.top_losers ?? []);
const moverPeriodOptions = [
    { label: '7D', value: 7 },
    { label: '30D', value: 30 },
    { label: '90D', value: 90 }
];

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

function imageCacheKey(cardId: number, size: 'small' | 'large'): string {
    return `${cardId}:${size}`;
}

function revokeObjectUrls(): void {
    for (const url of objectUrls) {
        URL.revokeObjectURL(url);
    }
    objectUrls.clear();
}

function getMoverImageSrc(mover: DashboardPriceMover, size: 'small' | 'large' = 'small'): string | null {
    const cached = localImageUrls.value[imageCacheKey(mover.card_id, size)];
    if (cached) {
        return cached;
    }

    if (size === 'large') {
        return mover.image_large || mover.image_small;
    }

    return mover.image_small || mover.image_large;
}

async function cacheMoverImage(mover: DashboardPriceMover, size: 'small' | 'large'): Promise<string | null> {
    const key = imageCacheKey(mover.card_id, size);
    if (localImageUrls.value[key]) {
        return localImageUrls.value[key];
    }

    try {
        const blob = await requestBlob(`/cards/${mover.card_id}/image?size=${size}`);
        const objectUrl = URL.createObjectURL(blob);
        objectUrls.add(objectUrl);
        localImageUrls.value = {
            ...localImageUrls.value,
            [key]: objectUrl
        };
        return objectUrl;
    } catch {
        return null;
    }
}

async function hydrateMoverThumbnails(entries: DashboardPriceMover[]): Promise<void> {
    await Promise.all(entries.map((entry) => cacheMoverImage(entry, 'small')));
}

function moverSubtitle(mover: DashboardPriceMover): string {
    const setName = mover.set_name || 'Edicion desconocida';
    return `${setName} - ${mover.card_number}`;
}

function moverCollectionLabel(mover: DashboardPriceMover): string {
    return `Coleccion: ${mover.collection_name}`;
}

function moverRangeLabel(mover: DashboardPriceMover): string {
    const from = new Date(mover.from_captured_at).toLocaleDateString('es-CL');
    const to = new Date(mover.to_captured_at).toLocaleDateString('es-CL');
    return `${from} -> ${to}`;
}

function openMoverHistory(mover: DashboardPriceMover): void {
    selectedMover.value = mover;
    priceHistoryVisible.value = true;
    void cacheMoverImage(mover, 'large');
}

async function loadMovers(): Promise<void> {
    moversLoading.value = true;
    try {
        const moversResponse = await getDashboardPriceMovers(selectedMoverPeriod.value);
        movers.value = moversResponse;
        void hydrateMoverThumbnails([...(moversResponse.top_gainers || []), ...(moversResponse.top_losers || [])]);
    } catch (err) {
        const detail = err instanceof Error ? err.message : 'No fue posible cargar el ranking de variaciones.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        moversLoading.value = false;
    }
}

async function loadDashboard(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
        const [collectionsResponse, valuationResponse, moversResponse] = await Promise.all([
            listCollections(),
            getCollectionsValuation(),
            getDashboardPriceMovers(selectedMoverPeriod.value)
        ]);
        collections.value = collectionsResponse;
        valuations.value = valuationResponse;
        movers.value = moversResponse;
        void hydrateMoverThumbnails([...(moversResponse.top_gainers || []), ...(moversResponse.top_losers || [])]);
    } catch (err) {
        error.value = err instanceof Error ? err.message : 'No fue posible cargar el dashboard.';
        toast.add({ severity: 'error', summary: 'Error', detail: error.value, life: 4000 });
    } finally {
        loading.value = false;
    }
}

onMounted(loadDashboard);
onBeforeUnmount(() => {
    revokeObjectUrls();
});
</script>

<template>
    <div class="grid grid-cols-12 gap-8">
        <div class="col-span-12">
            <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                    <div class="text-3xl font-semibold">Dashboard</div>
                    <p class="text-surface-500 mb-0">Resumen rapido de tus colecciones, valorizacion y cartas registradas.</p>
                </div>
                <div class="flex gap-3">
                    <Button label="Buscar carta" icon="pi pi-search" @click="router.push('/cards/search')" />
                    <Button label="Ver colecciones" icon="pi pi-folder-open" severity="secondary" outlined @click="router.push('/collections')" />
                </div>
            </div>
        </div>

        <div v-if="error" class="col-span-12">
            <Message severity="error">{{ error }}</Message>
        </div>

        <template v-if="loading">
            <div v-for="index in 4" :key="`summary-${index}`" class="col-span-12 md:col-span-6 xl:col-span-3">
                <Skeleton height="9rem" borderRadius="1rem" />
            </div>
            <div v-for="index in 4" :key="`bottom-${index}`" class="col-span-12 xl:col-span-4">
                <Skeleton height="20rem" borderRadius="1rem" />
            </div>
        </template>

        <template v-else>
            <div class="col-span-12 md:col-span-6 xl:col-span-3">
                <div class="card !mb-0">
                    <div class="flex items-start justify-between">
                        <div>
                            <div class="text-surface-500 mb-2">Total de colecciones</div>
                            <div class="text-4xl font-semibold">{{ totalCollections }}</div>
                        </div>
                        <div class="rounded-xl p-3 bg-cyan-100 dark:bg-cyan-500/20 text-cyan-700 dark:text-cyan-200">
                            <i class="pi pi-folder text-2xl"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-span-12 md:col-span-6 xl:col-span-3">
                <div class="card !mb-0">
                    <div class="flex items-start justify-between">
                        <div>
                            <div class="text-surface-500 mb-2">Total de cartas registradas</div>
                            <div class="text-4xl font-semibold">{{ totalCards }}</div>
                        </div>
                        <div class="rounded-xl p-3 bg-orange-100 dark:bg-orange-500/20 text-orange-700 dark:text-orange-200">
                            <i class="pi pi-th-large text-2xl"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-span-12 md:col-span-6 xl:col-span-3">
                <div class="card !mb-0">
                    <div class="flex items-start justify-between">
                        <div>
                            <div class="text-surface-500 mb-2">Valor estimado total</div>
                            <div class="text-4xl font-semibold">{{ formatMoney(estimatedValue) }}</div>
                        </div>
                        <div class="rounded-xl p-3 bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-200">
                            <i class="pi pi-wallet text-2xl"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-span-12 md:col-span-6 xl:col-span-3">
                <div class="card !mb-0">
                    <div class="flex items-start justify-between">
                        <div>
                            <div class="text-surface-500 mb-2">Colecciones con valor venta</div>
                            <div class="text-4xl font-semibold">{{ forSaleCount }}</div>
                        </div>
                        <div class="rounded-xl p-3 bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-200">
                            <i class="pi pi-shop text-2xl"></i>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-span-12 xl:col-span-6 2xl:col-span-4">
                <div class="card h-full">
                    <div class="flex items-start justify-between gap-4 mb-4">
                        <div>
                            <div class="text-2xl font-semibold">Valorizacion por coleccion</div>
                            <p class="text-surface-500 mb-0">Valor base y valor venta por cada coleccion registrada.</p>
                        </div>
                        <Tag :value="`${valuations.length} colecciones`" severity="info" />
                    </div>

                    <div v-if="valuations.length" class="flex flex-col gap-3">
                        <div class="grid grid-cols-12 gap-3 text-sm font-medium text-surface-500 px-1">
                            <div class="col-span-4">Coleccion</div>
                            <div class="col-span-4 text-right">Valor base</div>
                            <div class="col-span-4 text-right">Valor venta</div>
                        </div>

                        <div
                            v-for="valuation in valuations"
                            :key="valuation.collection_id"
                            class="p-4 rounded-2xl bg-surface-50 dark:bg-surface-900 border border-surface-100 dark:border-surface-800"
                        >
                            <div class="grid grid-cols-12 gap-3 items-start">
                                <div class="col-span-12 md:col-span-4">
                                    <div class="font-semibold">{{ valuation.collection_name }}</div>
                                    <div v-if="valuation.last_price_update" class="text-xs text-surface-500 mt-1">
                                        Actualizado: {{ new Date(valuation.last_price_update).toLocaleString('es-CL') }}
                                    </div>
                                </div>
                                <div class="col-span-6 md:col-span-4 text-right">
                                    <div class="font-semibold">{{ formatMoney(valuation.base_value, valuation.currency) }}</div>
                                </div>
                                <div class="col-span-6 md:col-span-4 text-right">
                                    <div class="font-semibold">{{ formatMoney(valuation.sale_value, valuation.currency) }}</div>
                                </div>
                            </div>
                            <div v-if="valuation.base_difference_percent !== null" class="mt-3 flex justify-end">
                                <Tag :severity="variationSeverity(valuation.base_difference_percent)" :value="`Variacion ${formatPercent(valuation.base_difference_percent)}`" />
                            </div>
                        </div>

                        <Divider class="my-1" />

                        <div class="flex flex-col gap-2">
                            <div class="flex items-center justify-between">
                                <span class="text-surface-500">Total base</span>
                                <span class="font-semibold">{{ formatMoney(totalBaseValue) }}</span>
                            </div>
                            <div class="flex items-center justify-between">
                                <span class="text-surface-500">Total venta</span>
                                <span class="font-semibold">{{ formatMoney(totalSaleValue) }}</span>
                            </div>
                        </div>
                    </div>

                    <div v-else class="text-surface-500">Aun no hay valorizaciones disponibles para mostrar.</div>
                </div>
            </div>

            <div class="col-span-12 xl:col-span-6 2xl:col-span-4 flex flex-col gap-8">
                <div class="card">
                    <div class="text-2xl font-semibold mb-3">Colecciones recientes</div>
                    <div v-if="collections.length" class="flex flex-col gap-3">
                        <div
                            v-for="collection in collections.slice(0, 3)"
                            :key="collection.id"
                            class="flex flex-col md:flex-row md:items-center md:justify-between gap-3 p-4 rounded-2xl bg-surface-50 dark:bg-surface-900"
                        >
                            <div>
                                <div class="font-semibold text-lg">{{ collection.name }}</div>
                                <div class="text-surface-500">{{ collection.description || 'Sin descripcion todavia.' }}</div>
                            </div>
                            <div class="flex items-center gap-2">
                                <Tag :value="`${collection.total_quantity} cartas`" severity="info" />
                                <Button label="Abrir" text @click="router.push(`/collections/${collection.id}`)" />
                            </div>
                        </div>
                    </div>
                    <div v-else class="text-surface-500">Todavia no hay colecciones. Crea la primera para empezar.</div>
                </div>

                <div class="card">
                    <div class="text-2xl font-semibold mb-3">Acciones rapidas</div>
                    <div class="grid grid-cols-1 gap-3">
                        <button class="p-4 rounded-2xl border border-surface-200 dark:border-surface-700 text-left hover:border-primary transition-colors" @click="router.push('/cards/search')">
                            <div class="font-semibold mb-1">Buscar carta</div>
                            <div class="text-surface-500">Consulta por codigo y trae datos oficiales desde Pokemon TCG API.</div>
                        </button>
                        <button class="p-4 rounded-2xl border border-surface-200 dark:border-surface-700 text-left hover:border-primary transition-colors" @click="router.push('/collections')">
                            <div class="font-semibold mb-1">Administrar colecciones</div>
                            <div class="text-surface-500">Actualiza valorizacion, revisa detalle y sigue el historico de precios.</div>
                        </button>
                    </div>
                </div>
            </div>

            <div class="col-span-12 xl:col-span-6 2xl:col-span-4">
                <div class="card h-full">
                    <div class="mb-4">
                        <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                            <div>
                                <div class="text-2xl font-semibold">Top variaciones</div>
                                <p class="text-surface-500 mb-0">Cartas con mayor movimiento porcentual en los ultimos {{ periodDays }} dias.</p>
                            </div>
                            <SelectButton
                                v-model="selectedMoverPeriod"
                                :options="moverPeriodOptions"
                                optionLabel="label"
                                optionValue="value"
                                :allowEmpty="false"
                                @update:modelValue="loadMovers"
                            />
                        </div>
                    </div>

                    <Tabs value="up">
                        <TabList>
                            <Tab value="up">Subidas</Tab>
                            <Tab value="down">Bajadas</Tab>
                        </TabList>
                        <TabPanels class="pt-4">
                            <TabPanel value="up">
                                <div class="flex items-center justify-between gap-3 mb-4">
                                    <div class="text-sm text-surface-500">Top cartas con mejor alza porcentual.</div>
                                    <Tag :value="`${topGainers.length} cartas`" severity="success" />
                                </div>

                                <div v-if="moversLoading" class="py-10 flex justify-center">
                                    <ProgressSpinner style="width: 2.5rem; height: 2.5rem" strokeWidth="5" />
                                </div>
                                <div v-else-if="topGainers.length" class="flex flex-col gap-3">
                                    <button
                                        v-for="mover in topGainers"
                                        :key="`gainer-${mover.collection_item_id}`"
                                        class="w-full rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 p-4 text-left transition hover:border-emerald-400 hover:bg-emerald-500/5"
                                        @click="openMoverHistory(mover)"
                                    >
                                        <div class="flex items-center gap-4">
                                            <div class="flex h-20 w-14 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-950 p-1">
                                                <img v-if="getMoverImageSrc(mover)" :src="getMoverImageSrc(mover) || undefined" :alt="mover.card_name" class="h-full w-full object-contain" />
                                                <div v-else class="text-[11px] text-surface-500 text-center">Sin imagen</div>
                                            </div>
                                            <div class="min-w-0 flex-1">
                                                <div class="font-semibold text-lg truncate">{{ mover.card_name }}</div>
                                                <div class="text-surface-500 truncate">{{ moverSubtitle(mover) }}</div>
                                                <div class="text-sm text-surface-500 truncate">{{ moverCollectionLabel(mover) }}</div>
                                                <div class="text-xs text-surface-400 mt-2">{{ moverRangeLabel(mover) }}</div>
                                            </div>
                                            <div class="text-right shrink-0">
                                                <Tag :severity="variationSeverity(mover.difference_percent)" :value="formatPercent(mover.difference_percent)" />
                                                <div class="mt-2 text-lg font-semibold text-emerald-400">{{ formatMoney(mover.difference, mover.currency) }}</div>
                                                <div class="text-xs text-surface-500 mt-1">
                                                    {{ formatMoney(mover.previous_price, mover.currency) }} -> {{ formatMoney(mover.current_price, mover.currency) }}
                                                </div>
                                            </div>
                                        </div>
                                    </button>
                                </div>

                                <div v-else class="text-surface-500">Aun no hay suficientes movimientos al alza dentro del ultimo mes.</div>
                            </TabPanel>
                            <TabPanel value="down">
                                <div class="flex items-center justify-between gap-3 mb-4">
                                    <div class="text-sm text-surface-500">Top cartas con mayor caida porcentual.</div>
                                    <Tag :value="`${topLosers.length} cartas`" severity="danger" />
                                </div>

                                <div v-if="moversLoading" class="py-10 flex justify-center">
                                    <ProgressSpinner style="width: 2.5rem; height: 2.5rem" strokeWidth="5" />
                                </div>
                                <div v-else-if="topLosers.length" class="flex flex-col gap-3">
                                    <button
                                        v-for="mover in topLosers"
                                        :key="`loser-${mover.collection_item_id}`"
                                        class="w-full rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 p-4 text-left transition hover:border-rose-400 hover:bg-rose-500/5"
                                        @click="openMoverHistory(mover)"
                                    >
                                        <div class="flex items-center gap-4">
                                            <div class="flex h-20 w-14 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-950 p-1">
                                                <img v-if="getMoverImageSrc(mover)" :src="getMoverImageSrc(mover) || undefined" :alt="mover.card_name" class="h-full w-full object-contain" />
                                                <div v-else class="text-[11px] text-surface-500 text-center">Sin imagen</div>
                                            </div>
                                            <div class="min-w-0 flex-1">
                                                <div class="font-semibold text-lg truncate">{{ mover.card_name }}</div>
                                                <div class="text-surface-500 truncate">{{ moverSubtitle(mover) }}</div>
                                                <div class="text-sm text-surface-500 truncate">{{ moverCollectionLabel(mover) }}</div>
                                                <div class="text-xs text-surface-400 mt-2">{{ moverRangeLabel(mover) }}</div>
                                            </div>
                                            <div class="text-right shrink-0">
                                                <Tag :severity="variationSeverity(mover.difference_percent)" :value="formatPercent(mover.difference_percent)" />
                                                <div class="mt-2 text-lg font-semibold text-rose-400">{{ formatMoney(mover.difference, mover.currency) }}</div>
                                                <div class="text-xs text-surface-500 mt-1">
                                                    {{ formatMoney(mover.previous_price, mover.currency) }} -> {{ formatMoney(mover.current_price, mover.currency) }}
                                                </div>
                                            </div>
                                        </div>
                                    </button>
                                </div>

                                <div v-else class="text-surface-500">Aun no hay suficientes movimientos a la baja dentro del ultimo mes.</div>
                            </TabPanel>
                        </TabPanels>
                    </Tabs>
                </div>
            </div>
        </template>

        <CollectionItemPriceHistoryDialog
            v-model:visible="priceHistoryVisible"
            :item-id="selectedMover?.collection_item_id ?? null"
            :title="selectedMover?.card_name || 'Carta'"
            :subtitle="selectedMover ? `${selectedMover.collection_name} - ${selectedMover.set_name || 'Edicion desconocida'} - ${selectedMover.card_number}` : ''"
            :image-src="selectedMover ? getMoverImageSrc(selectedMover, 'large') || getMoverImageSrc(selectedMover, 'small') : null"
            :image-alt="selectedMover?.card_name || 'Carta'"
            :default-range-days="selectedMoverPeriod"
            :current-base-price="selectedMover?.current_price ?? null"
            :currency="selectedMover?.currency || 'USD'"
        />
    </div>
</template>
