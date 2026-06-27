<script setup lang="ts">
import { searchCards } from '@/api/cardsApi';
import { searchInventoryCards } from '@/api/collectionItemsApi';
import { requestBlob } from '@/api/http';
import AddToCollectionDialog from '@/components/cards/AddToCollectionDialog.vue';
import CardResultGrid from '@/components/cards/CardResultGrid.vue';
import ManualCardDialog from '@/components/cards/ManualCardDialog.vue';
import CollectionItemPriceHistoryDialog from '@/components/collections/CollectionItemPriceHistoryDialog.vue';
import type { CardSearchResult } from '@/types/card';
import type { InventorySearchResult, PatternVariant } from '@/types/collectionItem';
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';

const router = useRouter();
const toast = useToast();
const mode = ref<'general' | 'code' | 'name' | 'promo' | 'inventory'>('general');
const query = ref('');
const loading = ref(false);
const searched = ref(false);
const error = ref('');
const results = ref<CardSearchResult[]>([]);
const inventoryResults = ref<InventorySearchResult[]>([]);
const dialogVisible = ref(false);
const manualDialogVisible = ref(false);
const selectedCard = ref<CardSearchResult | null>(null);
const promoMode = ref<'code' | 'name'>('code');
const localImageUrls = ref<Record<string, string>>({});
const objectUrls = new Set<string>();
const previewVisible = ref(false);
const previewLoading = ref(false);
const previewItem = ref<InventorySearchResult | null>(null);
const previewImageUrl = ref<string | null>(null);
const priceHistoryVisible = ref(false);
const priceHistoryItem = ref<InventorySearchResult | null>(null);
const inventoryFilters = reactive({
    collection: 'all',
    set: 'all',
    language: 'all',
    finish: 'all',
    condition: 'all',
    availability: 'all'
});

const modeOptions = [
    { label: 'General', value: 'general' },
    { label: 'Por codigo', value: 'code' },
    { label: 'Por nombre', value: 'name' },
    { label: 'Promos', value: 'promo' },
    { label: 'Mi inventario', value: 'inventory' }
];

const promoModeOptions = [
    { label: 'Codigo promo', value: 'code' },
    { label: 'Nombre promo', value: 'name' }
];

const inputLabel = computed(() => {
    if (mode.value === 'general') {
        return 'Busqueda general';
    }
    if (mode.value === 'code') {
        return 'Codigo de carta';
    }
    if (mode.value === 'promo') {
        return promoMode.value === 'code' ? 'Codigo promo' : 'Nombre promo';
    }
    if (mode.value === 'inventory') {
        return 'Carta en inventario';
    }
    return 'Nombre de carta';
});

const inputPlaceholder = computed(() => {
    if (mode.value === 'general') {
        return 'Pikachu, 160/165, SVP/088, TG01/TG30';
    }
    if (mode.value === 'code') {
        return '160/165';
    }
    if (mode.value === 'promo') {
        return promoMode.value === 'code' ? 'SVP/088' : 'Pikachu';
    }
    if (mode.value === 'inventory') {
        return 'Pikachu, 160/165, SVP/088, Haunter MEP 027';
    }
    return 'Pikachu';
});

const searchDescription = computed(() =>
    mode.value === 'general'
        ? 'Busca con un solo campo por nombre, codigo normal, promo o subsets especiales como TG01/TG30.'
        : mode.value === 'code'
          ? 'Busca por codigo en formato 160/165 para encontrar la carta exacta y agregarla a una coleccion.'
          : mode.value === 'promo'
            ? 'Busca promos Scarlet & Violet por codigo promo o por nombre, sin afectar la mascara del buscador normal.'
            : mode.value === 'inventory'
              ? 'Busca dentro de las cartas que ya tienes registradas, sin importar en que coleccion esten.'
            : 'Busca por nombre para revisar variantes disponibles y agregarlas a una coleccion.'
);

function imageCacheKey(cardId: number, size: 'small' | 'large'): string {
    return `${cardId}:${size}`;
}

function revokeObjectUrls(): void {
    for (const url of objectUrls) {
        URL.revokeObjectURL(url);
    }
    objectUrls.clear();
}

function getInventoryImageSrc(item: InventorySearchResult, size: 'small' | 'large' = 'small'): string | null {
    const cached = localImageUrls.value[imageCacheKey(item.card.id, size)];
    if (cached) {
        return cached;
    }

    if (size === 'large') {
        return item.card.image_large || item.card.image_small;
    }

    return item.card.image_small || item.card.image_large;
}

async function cacheInventoryCardImage(item: InventorySearchResult, size: 'small' | 'large'): Promise<string | null> {
    const key = imageCacheKey(item.card.id, size);
    if (localImageUrls.value[key]) {
        return localImageUrls.value[key];
    }

    try {
        const blob = await requestBlob(`/cards/${item.card.id}/image?size=${size}`);
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

async function hydrateInventoryThumbnails(entries: InventorySearchResult[]): Promise<void> {
    await Promise.all(entries.map((item) => cacheInventoryCardImage(item, 'small')));
}

function normalizeCodeQuery(value: string): string {
    const normalizedValue = value.replace(/&/g, '/').replace(/\s+/g, '').replace(/[^\d/]/g, '');

    if (!normalizedValue) {
        return '';
    }

    if (normalizedValue.includes('/')) {
        const [rawLeft = '', ...rest] = normalizedValue.split('/');
        const rawRight = rest.join('');
        const left = rawLeft.replace(/\D/g, '').slice(0, 3);
        const right = rawRight.replace(/\D/g, '').slice(0, 3);
        return right ? `${left}/${right}` : `${left}/`;
    }

    const digits = normalizedValue.replace(/\D/g, '').slice(0, 6);
    if (digits.length <= 3) {
        return digits;
    }

    return `${digits.slice(0, 3)}/${digits.slice(3)}`;
}

function normalizeCodeForSearch(value: string): string {
    const [left = '', right = ''] = value.split('/');
    const normalizedLeft = String(Number.parseInt(left, 10));
    const normalizedRight = String(Number.parseInt(right, 10));
    return `${normalizedLeft}/${normalizedRight}`;
}

function normalizePromoCodeQuery(value: string): string {
    const normalizedValue = value.toUpperCase().replace(/\s+/g, '').replace(/[^A-Z0-9/]/g, '');

    if (!normalizedValue) {
        return '';
    }

    if (normalizedValue.includes('/')) {
        const [rawPrefix = '', ...rest] = normalizedValue.split('/');
        const prefix = rawPrefix.replace(/[^A-Z]/g, '').slice(0, 6) || 'SVP';
        const right = rest.join('').replace(/\D/g, '').slice(0, 3);
        return right ? `${prefix}/${right}` : `${prefix}/`;
    }

    if (/^[A-Z]{1,6}$/.test(normalizedValue)) {
        return normalizedValue;
    }

    if (/^\d{1,3}$/.test(normalizedValue)) {
        return `SVP/${normalizedValue}`;
    }

    const letters = normalizedValue.replace(/[^A-Z]/g, '').slice(0, 6) || 'SVP';
    const digits = normalizedValue.replace(/\D/g, '').slice(0, 3);
    return digits ? `${letters}/${digits}` : letters;
}

function normalizePromoCodeForSearch(value: string): string {
    const normalized = normalizePromoCodeQuery(value);
    const [, rawNumber = normalized] = normalized.split('/');
    return `SVP/${String(Number.parseInt(rawNumber, 10))}`;
}

watch(mode, () => {
    query.value = '';
    promoMode.value = 'code';
    searched.value = false;
    error.value = '';
    results.value = [];
    inventoryResults.value = [];
    resetInventoryFilters();
});

watch(promoMode, () => {
    if (mode.value !== 'promo') {
        return;
    }
    query.value = '';
    searched.value = false;
    error.value = '';
    results.value = [];
});

watch(query, (value) => {
    if (mode.value === 'code') {
        const normalizedValue = normalizeCodeQuery(value);
        if (normalizedValue !== value) {
            query.value = normalizedValue;
        }
        return;
    }

    if (mode.value === 'promo' && promoMode.value === 'code') {
        const normalizedValue = normalizePromoCodeQuery(value);
        if (normalizedValue !== value) {
            query.value = normalizedValue;
        }
    }
});

async function search(): Promise<void> {
    const normalizedQuery = query.value.trim();
    if (!normalizedQuery) {
        error.value =
            mode.value === 'general'
                ? 'Ingresa un nombre o codigo para buscar.'
                : mode.value === 'code'
                ? 'Ingresa un codigo para buscar.'
                : mode.value === 'promo'
                  ? promoMode.value === 'code'
                      ? 'Ingresa un codigo promo para buscar.'
                      : 'Ingresa un nombre promo para buscar.'
                  : mode.value === 'inventory'
                    ? 'Ingresa un nombre o codigo para buscar en tu inventario.'
                  : 'Ingresa un nombre para buscar.';
        searched.value = false;
        results.value = [];
        inventoryResults.value = [];
        return;
    }

    if (mode.value === 'code' && !/^\d{1,3}\/\d{1,3}$/.test(normalizedQuery)) {
        error.value = 'Ingresa el codigo completo en formato 096/099 o 165/166.';
        searched.value = false;
        results.value = [];
        return;
    }

    if (mode.value === 'promo' && promoMode.value === 'code' && !/^[A-Z]{2,6}\/\d{1,3}$/.test(normalizedQuery)) {
        error.value = 'Ingresa el codigo promo en formato SVP/088.';
        searched.value = false;
        results.value = [];
        return;
    }

    loading.value = true;
    searched.value = true;
    error.value = '';
    results.value = [];
    inventoryResults.value = [];
    resetInventoryFilters();

    try {
        if (mode.value === 'inventory') {
            inventoryResults.value = await searchInventoryCards(normalizedQuery);
            void hydrateInventoryThumbnails(inventoryResults.value);
        } else {
            const response = await searchCards(
                mode.value === 'general'
                    ? { general: normalizedQuery }
                    : mode.value === 'code'
                    ? { code: normalizeCodeForSearch(normalizedQuery) }
                    : mode.value === 'promo'
                      ? promoMode.value === 'code'
                          ? { promo_code: normalizePromoCodeForSearch(normalizedQuery) }
                          : { promo_name: normalizedQuery }
                      : { name: normalizedQuery }
            );
            results.value = response.results;
        }
    } catch (err) {
        error.value = err instanceof Error ? err.message : 'No fue posible realizar la busqueda.';
        toast.add({ severity: 'error', summary: 'Busqueda fallida', detail: error.value, life: 4000 });
    } finally {
        loading.value = false;
    }
}

function openAddDialog(card: CardSearchResult): void {
    selectedCard.value = card;
    dialogVisible.value = true;
}

function openManualDialog(): void {
    manualDialogVisible.value = true;
}

function formatMoney(amount: number | string | null | undefined, currency = 'USD'): string {
    return new Intl.NumberFormat('es-CL', {
        style: 'currency',
        currency,
        maximumFractionDigits: 2
    }).format(Number(amount ?? 0));
}

function normalizeBadgeText(value: string | null | undefined): string | null {
    const normalized = value?.trim();
    if (!normalized || normalized.toLowerCase() === 'none') {
        return null;
    }
    return normalized;
}

function resolvePatternVariantLabel(patternVariant: PatternVariant | null | undefined): string | null {
    if (!patternVariant) {
        return null;
    }
    if (patternVariant === 'poke_ball') {
        return 'Poke Ball Pattern';
    }
    if (patternVariant === 'master_ball') {
        return 'Master Ball Pattern';
    }
    return null;
}

function resolveInventoryFinish(item: InventorySearchResult): string {
    return normalizeBadgeText(item.finish) || 'Normal';
}

function resolveInventoryFinishWithPattern(item: InventorySearchResult): string {
    const finish = resolveInventoryFinish(item);
    const patternLabel = resolvePatternVariantLabel(item.pattern_variant);
    return patternLabel ? `${finish} - ${patternLabel}` : finish;
}

function resolveInventoryRarity(item: InventorySearchResult): string | null {
    const rarity = normalizeBadgeText(item.card.rarity);
    if (!rarity) {
        return null;
    }

    const finish = normalizeBadgeText(item.finish);
    if (finish && rarity.localeCompare(finish, undefined, { sensitivity: 'accent' }) === 0) {
        return null;
    }

    return rarity;
}

const inventoryCollectionOptions = computed(() => [
    { label: 'Todas las colecciones', value: 'all' },
    ...Array.from(new Set(inventoryResults.value.map((item) => item.collection_name).filter(Boolean)))
        .sort((a, b) => a.localeCompare(b, 'es'))
        .map((value) => ({ label: value, value }))
]);

const inventorySetOptions = computed(() => [
    { label: 'Todas las ediciones', value: 'all' },
    ...Array.from(new Set(inventoryResults.value.map((item) => item.card.set_name).filter(Boolean)))
        .sort((a, b) => String(a).localeCompare(String(b), 'es'))
        .map((value) => ({ label: String(value), value: String(value) }))
]);

const inventoryLanguageOptions = computed(() => [
    { label: 'Todos los idiomas', value: 'all' },
    ...Array.from(new Set(inventoryResults.value.map((item) => item.language).filter(Boolean)))
        .sort((a, b) => String(a).localeCompare(String(b), 'es'))
        .map((value) => ({ label: String(value), value: String(value) }))
]);

const inventoryFinishOptions = computed(() => [
    { label: 'Todos los acabados', value: 'all' },
    ...Array.from(new Set(inventoryResults.value.map((item) => resolveInventoryFinishWithPattern(item)).filter(Boolean)))
        .sort((a, b) => a.localeCompare(b, 'es'))
        .map((value) => ({ label: value, value }))
]);

const inventoryConditionOptions = computed(() => [
    { label: 'Todos los estados', value: 'all' },
    ...Array.from(new Set(inventoryResults.value.map((item) => item.condition).filter(Boolean)))
        .sort((a, b) => String(a).localeCompare(String(b), 'es'))
        .map((value) => ({ label: String(value), value: String(value) }))
]);

const inventoryAvailabilityOptions = [
    { label: 'Disponibilidad', value: 'all' },
    { label: 'Con precio base', value: 'priced' },
    { label: 'Sin precio base', value: 'unpriced' },
    { label: 'Solo en venta', value: 'for_sale' }
];

const filteredInventoryResults = computed(() =>
    inventoryResults.value.filter((item) => {
        if (inventoryFilters.collection !== 'all' && item.collection_name !== inventoryFilters.collection) {
            return false;
        }
        if (inventoryFilters.set !== 'all' && (item.card.set_name || '') !== inventoryFilters.set) {
            return false;
        }
        if (inventoryFilters.language !== 'all' && (item.language || '') !== inventoryFilters.language) {
            return false;
        }
        if (inventoryFilters.finish !== 'all' && resolveInventoryFinishWithPattern(item) !== inventoryFilters.finish) {
            return false;
        }
        if (inventoryFilters.condition !== 'all' && (item.condition || '') !== inventoryFilters.condition) {
            return false;
        }
        if (inventoryFilters.availability === 'priced' && !Number(item.base_price ?? 0)) {
            return false;
        }
        if (inventoryFilters.availability === 'unpriced' && Number(item.base_price ?? 0)) {
            return false;
        }
        if (inventoryFilters.availability === 'for_sale' && !item.is_for_sale) {
            return false;
        }
        return true;
    })
);

const totalMatches = computed(() => (mode.value === 'inventory' ? filteredInventoryResults.value.length : results.value.length));
const hasRenderableResults = computed(() => (mode.value === 'inventory' ? inventoryResults.value.length > 0 : totalMatches.value > 0));

function resetInventoryFilters(): void {
    inventoryFilters.collection = 'all';
    inventoryFilters.set = 'all';
    inventoryFilters.language = 'all';
    inventoryFilters.finish = 'all';
    inventoryFilters.condition = 'all';
    inventoryFilters.availability = 'all';
}

async function openInventoryPreview(item: InventorySearchResult): Promise<void> {
    previewItem.value = item;
    previewVisible.value = true;
    previewLoading.value = true;
    previewImageUrl.value = getInventoryImageSrc(item, 'large');

    try {
        const cached = await cacheInventoryCardImage(item, 'large');
        if (previewItem.value?.item_id === item.item_id && cached) {
            previewImageUrl.value = cached;
        }
    } finally {
        if (previewItem.value?.item_id === item.item_id) {
            previewLoading.value = false;
        }
    }
}

function openCollection(collectionId: number): void {
    router.push(`/collections/${collectionId}`);
}

function openPriceHistory(item: InventorySearchResult): void {
    priceHistoryItem.value = item;
    priceHistoryVisible.value = true;
}

onBeforeUnmount(() => {
    revokeObjectUrls();
});
</script>

<template>
    <div class="flex flex-col gap-6">
        <div class="card">
            <div class="flex flex-col gap-5">
                <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
                    <div class="flex-1">
                        <div class="text-2xl font-semibold mb-2">Buscar carta</div>
                        <p class="text-surface-500 mb-0">{{ searchDescription }}</p>
                    </div>
                    <SelectButton v-model="mode" :options="modeOptions" optionLabel="label" optionValue="value" :allowEmpty="false" />
                </div>

                <div v-if="mode === 'promo'" class="flex items-center gap-3">
                    <span class="text-sm text-surface-500">Buscar promos por:</span>
                    <SelectButton v-model="promoMode" :options="promoModeOptions" optionLabel="label" optionValue="value" :allowEmpty="false" />
                </div>

                <div class="flex flex-col lg:flex-row lg:items-end gap-4">
                    <div class="flex-1">
                        <label class="block text-sm mb-2">{{ inputLabel }}</label>
                        <InputText v-model="query" :placeholder="inputPlaceholder" class="w-full" @keyup.enter="search" />
                        <small v-if="mode === 'general'" class="text-surface-500 mt-2 block">
                            Acepta nombre, `160/165`, `SVP/088` y subsets especiales como `TG01/TG30` o `GG12/GG70`.
                        </small>
                        <small v-else-if="mode === 'inventory'" class="text-surface-500 mt-2 block">
                            Puedes buscar por nombre, codigo, promo o referencia tipo `MEP 027` para saber si ya la tienes guardada.
                        </small>
                        <small v-else-if="mode === 'code'" class="text-surface-500 mt-2 block">Escribe solo numeros y el campo completara automaticamente el formato `096/099`.</small>
                        <small v-else-if="mode === 'promo' && promoMode === 'code'" class="text-surface-500 mt-2 block">
                            Puedes escribir `088` o `SVP/088` y el campo lo normalizara automaticamente.
                        </small>
                    </div>
                    <div class="flex gap-3">
                        <Button v-if="mode !== 'inventory'" label="Crear manualmente" icon="pi pi-pencil" severity="secondary" outlined @click="openManualDialog" />
                        <Button label="Buscar" icon="pi pi-search" :loading="loading" @click="search" />
                    </div>
                </div>
            </div>
        </div>

        <Message v-if="error" severity="error">{{ error }}</Message>

        <div v-if="loading" class="card">
            <div class="flex justify-center py-10">
                <ProgressSpinner style="width: 3rem; height: 3rem" strokeWidth="6" />
            </div>
        </div>

        <div v-else-if="searched && !totalMatches && !error" class="card text-center py-10">
            <i class="pi pi-search text-4xl text-surface-400 mb-4"></i>
            <div class="text-2xl font-semibold mb-2">Sin resultados</div>
            <p class="text-surface-500 mb-0">
                {{
                    mode === 'code'
                        ? 'No se encontraron cartas para ese codigo.'
                        : mode === 'general'
                          ? 'No se encontraron cartas para ese termino.'
                        : mode === 'promo'
                          ? promoMode === 'code'
                              ? 'No se encontraron promos para ese codigo.'
                              : 'No se encontraron promos para ese nombre.'
                          : mode === 'inventory'
                            ? 'No tienes cartas registradas que coincidan con esa busqueda.'
                          : 'No se encontraron cartas para ese nombre.'
                }}
            </p>
            <Button v-if="mode !== 'inventory'" label="Crear carta manual" icon="pi pi-plus" class="mt-5" @click="openManualDialog" />
        </div>

        <div v-else-if="hasRenderableResults" class="flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <div class="text-2xl font-semibold">Resultados</div>
                <Tag
                    :value="mode === 'inventory' && filteredInventoryResults.length !== inventoryResults.length ? `${totalMatches} de ${inventoryResults.length} coincidencias` : `${totalMatches} coincidencias`"
                    severity="info"
                />
            </div>
            <CardResultGrid v-if="mode !== 'inventory'" :results="results" @add="openAddDialog" />
            <div v-else class="card">
                <div class="flex flex-col gap-4">
                    <div class="rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 p-4">
                        <div class="flex flex-col gap-4">
                            <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                                <div>
                                    <div class="font-semibold text-lg">Filtros avanzados</div>
                                    <div class="text-sm text-surface-500">Refina tu inventario por coleccion, edicion y estado sin salir del buscador.</div>
                                </div>
                                <Button label="Limpiar filtros" icon="pi pi-filter-slash" outlined size="small" @click="resetInventoryFilters" />
                            </div>
                            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                                <Select v-model="inventoryFilters.collection" :options="inventoryCollectionOptions" optionLabel="label" optionValue="value" fluid />
                                <Select v-model="inventoryFilters.set" :options="inventorySetOptions" optionLabel="label" optionValue="value" fluid />
                                <Select v-model="inventoryFilters.language" :options="inventoryLanguageOptions" optionLabel="label" optionValue="value" fluid />
                                <Select v-model="inventoryFilters.finish" :options="inventoryFinishOptions" optionLabel="label" optionValue="value" fluid />
                                <Select v-model="inventoryFilters.condition" :options="inventoryConditionOptions" optionLabel="label" optionValue="value" fluid />
                                <Select v-model="inventoryFilters.availability" :options="inventoryAvailabilityOptions" optionLabel="label" optionValue="value" fluid />
                            </div>
                        </div>
                    </div>

                    <DataTable :value="filteredInventoryResults" paginator :rows="10" dataKey="item_id" responsiveLayout="scroll">
                    <template #empty>
                        <div class="py-8 text-center">
                            <div class="font-semibold mb-2">Sin coincidencias con los filtros actuales</div>
                            <div class="text-surface-500">Ajusta o limpia los filtros para volver a ver cartas de tu inventario.</div>
                        </div>
                    </template>
                    <Column header="Carta" style="min-width: 24rem">
                        <template #body="{ data }">
                            <div class="flex items-center gap-4">
                                <button
                                    type="button"
                                    class="group flex-shrink-0 rounded-xl border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900 p-1 transition hover:border-primary cursor-pointer"
                                    @click="openInventoryPreview(data)"
                                >
                                    <img
                                        v-if="getInventoryImageSrc(data)"
                                        :src="getInventoryImageSrc(data) || undefined"
                                        :alt="data.card.name"
                                        class="h-20 w-14 rounded-md object-contain"
                                    />
                                    <div v-else class="h-20 w-14 rounded-md flex items-center justify-center text-xs text-surface-500">Sin imagen</div>
                                </button>
                                <div>
                                    <div class="font-semibold text-lg">{{ data.card.name }}</div>
                                    <div class="text-surface-500">{{ data.card.set_name || 'Edicion desconocida' }} - {{ data.card.number }}</div>
                                    <div class="flex flex-wrap gap-2 mt-2">
                                        <Tag :value="resolveInventoryFinish(data)" severity="info" />
                                        <Tag v-if="resolvePatternVariantLabel(data.pattern_variant)" :value="resolvePatternVariantLabel(data.pattern_variant) || undefined" severity="warn" />
                                        <Tag v-if="resolveInventoryRarity(data)" :value="resolveInventoryRarity(data) || undefined" severity="contrast" />
                                    </div>
                                </div>
                            </div>
                        </template>
                    </Column>
                    <Column header="Coleccion" style="min-width: 12rem">
                        <template #body="{ data }">
                            <Button :label="data.collection_name" link class="!p-0" @click="openCollection(data.collection_id)" />
                        </template>
                    </Column>
                    <Column field="quantity" header="Cantidad" />
                    <Column header="Idioma">
                        <template #body="{ data }">{{ data.language || '-' }}</template>
                    </Column>
                    <Column header="Estado">
                        <template #body="{ data }">{{ data.condition || '-' }}</template>
                    </Column>
                    <Column header="Base" style="min-width: 9rem">
                        <template #body="{ data }">{{ data.base_price ? formatMoney(data.base_price, data.base_price_currency || 'USD') : '-' }}</template>
                    </Column>
                    <Column header="Venta" style="min-width: 9rem">
                        <template #body="{ data }">{{ data.sale_price ? formatMoney(data.sale_price, data.base_price_currency || 'USD') : '-' }}</template>
                    </Column>
                    <Column header="Acciones" style="min-width: 11rem">
                        <template #body="{ data }">
                            <div class="flex flex-wrap gap-2">
                                <Button icon="pi pi-chart-line" outlined size="small" @click="openPriceHistory(data)" />
                                <Button label="Abrir" icon="pi pi-arrow-right" outlined size="small" @click="openCollection(data.collection_id)" />
                            </div>
                        </template>
                    </Column>
                    </DataTable>
                </div>
            </div>
        </div>

        <AddToCollectionDialog v-model:visible="dialogVisible" :card="selectedCard" />
        <ManualCardDialog v-model:visible="manualDialogVisible" :initial-query="query" />
        <CollectionItemPriceHistoryDialog
            v-model:visible="priceHistoryVisible"
            :item-id="priceHistoryItem?.item_id ?? null"
            :title="priceHistoryItem?.card.name || 'Carta'"
            :subtitle="priceHistoryItem ? `${priceHistoryItem.collection_name} - ${priceHistoryItem.card.set_name || 'Edicion desconocida'} - ${priceHistoryItem.card.number}` : ''"
            :image-src="priceHistoryItem ? getInventoryImageSrc(priceHistoryItem, 'large') : null"
            :image-alt="priceHistoryItem?.card.name || 'Carta'"
            :default-range-days="30"
            :current-base-price="priceHistoryItem?.base_price ?? null"
            :current-sale-price="priceHistoryItem?.sale_price ?? null"
            :currency="priceHistoryItem?.base_price_currency || 'USD'"
        />
        <Dialog v-model:visible="previewVisible" modal :header="previewItem?.card.name || 'Vista de carta'" :style="{ width: 'min(92vw, 56rem)' }">
            <div class="grid grid-cols-12 gap-6 items-start">
                <div class="col-span-12 md:col-span-5">
                    <div class="rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900 p-4 flex items-center justify-center min-h-80">
                        <ProgressSpinner v-if="previewLoading" style="width: 3rem; height: 3rem" strokeWidth="4" />
                        <img
                            v-else-if="previewItem && previewImageUrl"
                            :src="previewImageUrl"
                            :alt="previewItem.card.name"
                            class="max-h-[32rem] w-auto max-w-full object-contain rounded-xl shadow"
                        />
                        <div v-else class="text-surface-500">Imagen no disponible</div>
                    </div>
                </div>
                <div class="col-span-12 md:col-span-7" v-if="previewItem">
                    <div class="flex flex-col gap-4">
                        <div>
                            <div class="text-2xl font-semibold">{{ previewItem.card.name }}</div>
                            <div class="text-surface-500 mt-1">{{ previewItem.card.set_name || 'Edicion desconocida' }} - {{ previewItem.card.number }}</div>
                        </div>
                        <div class="flex flex-wrap gap-2">
                            <Tag :value="resolveInventoryFinish(previewItem)" severity="info" />
                            <Tag v-if="resolvePatternVariantLabel(previewItem.pattern_variant)" :value="resolvePatternVariantLabel(previewItem.pattern_variant) || undefined" severity="warn" />
                            <Tag v-if="resolveInventoryRarity(previewItem)" :value="resolveInventoryRarity(previewItem) || undefined" severity="contrast" />
                            <Tag v-if="previewItem.card.pokedex_number" :value="`Pokedex #${previewItem.card.pokedex_number}`" severity="info" />
                            <Tag :value="previewItem.collection_name" severity="secondary" />
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="rounded-xl bg-surface-50 dark:bg-surface-900 p-4">
                                <div class="text-sm text-surface-500 mb-1">Estado</div>
                                <div class="font-medium">{{ previewItem.condition || 'Sin estado' }}</div>
                            </div>
                            <div class="rounded-xl bg-surface-50 dark:bg-surface-900 p-4">
                                <div class="text-sm text-surface-500 mb-1">Acabado</div>
                                <div class="font-medium">{{ resolveInventoryFinishWithPattern(previewItem) }}</div>
                            </div>
                            <div class="rounded-xl bg-surface-50 dark:bg-surface-900 p-4">
                                <div class="text-sm text-surface-500 mb-1">Idioma</div>
                                <div class="font-medium">{{ previewItem.language || 'Sin idioma' }}</div>
                            </div>
                            <div class="rounded-xl bg-surface-50 dark:bg-surface-900 p-4">
                                <div class="text-sm text-surface-500 mb-1">Cantidad</div>
                                <div class="font-medium">{{ previewItem.quantity }}</div>
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="rounded-xl bg-surface-50 dark:bg-surface-900 p-4">
                                <div class="text-sm text-surface-500 mb-1">Precio base</div>
                                <div class="font-semibold">{{ previewItem.base_price ? formatMoney(previewItem.base_price, previewItem.base_price_currency || 'USD') : '-' }}</div>
                            </div>
                            <div class="rounded-xl bg-surface-50 dark:bg-surface-900 p-4">
                                <div class="text-sm text-surface-500 mb-1">Precio venta</div>
                                <div class="font-semibold">{{ previewItem.sale_price ? formatMoney(previewItem.sale_price, previewItem.base_price_currency || 'USD') : '-' }}</div>
                            </div>
                        </div>
                        <div class="flex gap-3">
                            <Button label="Abrir coleccion" icon="pi pi-arrow-right" @click="openCollection(previewItem.collection_id)" />
                        </div>
                        <div v-if="previewItem.notes">
                            <div class="text-sm text-surface-500 mb-1">Notas</div>
                            <div class="rounded-xl border border-surface-200 dark:border-surface-700 p-4 whitespace-pre-wrap">{{ previewItem.notes }}</div>
                        </div>
                    </div>
                </div>
            </div>
        </Dialog>
    </div>
</template>
