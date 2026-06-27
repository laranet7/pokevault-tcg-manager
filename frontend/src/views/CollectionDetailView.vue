<script setup lang="ts">
import { deleteCollectionItem, listCollectionItems, moveCollectionItems, updateCollectionItem } from '@/api/collectionItemsApi';
import { deleteCollection, getCollection, getCollectionPriceVariation, listCollections, refreshCollectionPrices, updateCollection } from '@/api/collectionsApi';
import { requestBlob } from '@/api/http';
import CollectionCollaboratorsDialog from '@/components/collections/CollectionCollaboratorsDialog.vue';
import CollectionExportDialog from '@/components/collections/CollectionExportDialog.vue';
import CollectionItemPriceHistoryDialog from '@/components/collections/CollectionItemPriceHistoryDialog.vue';
import CollectionSettingsDialog from '@/components/collections/CollectionSettingsDialog.vue';
import type { Collection, UpdateCollectionPayload } from '@/types/collection';
import type { CollectionItem } from '@/types/collectionItem';
import type { CollectionItemVariation, CollectionPriceVariation } from '@/types/pricing';
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useConfirm } from 'primevue/useconfirm';
import { useToast } from 'primevue/usetoast';
import type { MenuItem } from 'primevue/menuitem';
import Tooltip from 'primevue/tooltip';

const route = useRoute();
const router = useRouter();
const confirm = useConfirm();
const toast = useToast();
const vTooltip = Tooltip;

const loading = ref(true);
const collection = ref<Collection | null>(null);
const items = ref<CollectionItem[]>([]);
const variation = ref<CollectionPriceVariation | null>(null);
const error = ref('');
const selectedItems = ref<CollectionItem[]>([]);
const editVisible = ref(false);
const saving = ref(false);
const selectedItem = ref<CollectionItem | null>(null);
const optionsMenu = ref();
const selectedOptionsMenu = ref();
const collectionDialogVisible = ref(false);
const collaboratorsDialogVisible = ref(false);
const exportDialogVisible = ref(false);
const moveDialogVisible = ref(false);
const collectionSaving = ref(false);
const refreshingPrices = ref(false);
const movingItems = ref(false);
const variationExpanded = ref(false);
const availableCollections = ref<Collection[]>([]);
const targetCollectionId = ref<number | null>(null);
const previewVisible = ref(false);
const previewLoading = ref(false);
const previewItem = ref<CollectionItem | null>(null);
const previewImageUrl = ref<string | null>(null);
const priceHistoryVisible = ref(false);
const priceHistoryItem = ref<CollectionItem | null>(null);
const localImageUrls = ref<Record<string, string>>({});
const objectUrls = new Set<string>();

const editForm = reactive({
    quantity: 1,
    language: 'Espanol',
    condition: 'Mint',
    finish: 'Normal',
    is_pokeball: false,
    is_for_sale: false,
    base_price: null as number | null,
    base_price_currency: 'USD',
    sale_margin_percent: null as number | null,
    sale_price: null as number | null,
    sale_status: 'not_available',
    notes: ''
});

const conditionOptions = ['Mint', 'Near Mint', 'Excellent', 'Good', 'Played', 'Damaged'].map((value) => ({ label: value, value }));
const finishOptions = ['Normal', 'Holo', 'Reverse Holo', 'Full Art', 'Illustration Rare', 'Special Illustration Rare', 'Promo'].map((value) => ({
    label: value,
    value
}));
const languageOptions = ['Espanol', 'Ingles', 'Japones', 'Otro'].map((value) => ({ label: value, value }));
const saleStatusOptions = [
    { label: 'No disponible', value: 'not_available' },
    { label: 'Disponible', value: 'available' },
    { label: 'Reservada', value: 'reserved' },
    { label: 'Vendida', value: 'sold' }
];

const collectionId = computed(() => Number(route.params.id));
const canEditCollection = computed(() => Boolean(collection.value?.can_edit));
const canManageCollection = computed(() => Boolean(collection.value?.can_manage));
const targetCollectionOptions = computed(() =>
    availableCollections.value
        .filter((entry) => entry.id !== collectionId.value)
        .map((entry) => ({ label: entry.name, value: entry.id }))
);
const variationMap = computed<Record<number, CollectionItemVariation>>(() =>
    Object.fromEntries((variation.value?.item_variations || []).map((itemVariation) => [itemVariation.collection_item_id, itemVariation]))
);
const estimatedTotal = computed(() =>
    items.value.reduce((sum, item) => {
        const unit = Number(item.sale_price ?? item.base_price ?? 0);
        return sum + unit * Number(item.quantity);
    }, 0)
);
const totalBaseCost = computed(() =>
    items.value.reduce((sum, item) => {
        const unit = Number(item.base_price ?? 0);
        return sum + unit * Number(item.quantity);
    }, 0)
);
const totalSaleCost = computed(() =>
    items.value.reduce((sum, item) => {
        const unit = Number(item.sale_price ?? 0);
        return sum + unit * Number(item.quantity);
    }, 0)
);
const collectionOptions = computed<MenuItem[]>(() => {
    const baseItems: MenuItem[] = [
        {
            label: 'Exportar',
            icon: 'pi pi-download',
            disabled: !items.value.length,
            command: () => {
                exportDialogVisible.value = true;
            }
        },
        {
            label: 'Actualizar valorizacion',
            icon: 'pi pi-refresh',
            disabled: !collection.value || refreshingPrices.value || !canEditCollection.value,
            command: () => {
                void handleRefreshPrices();
            }
        }
    ];

    if (canManageCollection.value) {
        baseItems.push(
            {
                label: 'Configurar coleccion',
                icon: 'pi pi-cog',
                disabled: !collection.value,
                command: () => {
                    collectionDialogVisible.value = true;
                }
            },
            {
                label: 'Colaboradores',
                icon: 'pi pi-users',
                disabled: !collection.value,
                command: () => {
                    collaboratorsDialogVisible.value = true;
                }
            },
            {
                label: 'Eliminar coleccion',
                icon: 'pi pi-trash',
                disabled: !collection.value,
                command: () => {
                    confirmDeleteCollection();
                }
            }
        );
    }

    return baseItems;
});
const selectedCollectionOptions = computed<MenuItem[]>(() =>
    canEditCollection.value
        ? [
              {
                  label: 'Mover seleccionadas',
                  icon: 'pi pi-arrow-right-arrow-left',
                  disabled: !selectedItems.value.length,
                  command: () => {
                      void openMoveDialog();
                  }
              }
          ]
        : []
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

function getCardImageSrc(item: CollectionItem, size: 'small' | 'large' = 'small'): string | null {
    const cached = localImageUrls.value[imageCacheKey(item.card.id, size)];
    if (cached) {
        return cached;
    }

    if (size === 'large') {
        return item.card.image_large || item.card.image_small;
    }

    return item.card.image_small || item.card.image_large;
}

async function cacheCardImage(item: CollectionItem, size: 'small' | 'large'): Promise<string | null> {
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

async function hydrateCardThumbnails(entries: CollectionItem[]): Promise<void> {
    await Promise.all(entries.map((item) => cacheCardImage(item, 'small')));
}

function formatMoney(amount: number | string | null | undefined, currency = 'USD'): string {
    return new Intl.NumberFormat('es-CL', {
        style: 'currency',
        currency,
        maximumFractionDigits: 2
    }).format(Number(amount ?? 0));
}

function formatPercent(value: number | string | null | undefined): string {
    const amount = Number(value ?? 0);
    return `${amount > 0 ? '+' : ''}${amount.toFixed(2)}%`;
}

function variationSeverity(trend: CollectionItemVariation['trend'] | undefined): 'success' | 'danger' | 'secondary' | 'contrast' {
    if (trend === 'up') {
        return 'success';
    }
    if (trend === 'down') {
        return 'danger';
    }
    if (trend === 'equal') {
        return 'secondary';
    }
    return 'contrast';
}

function variationLabel(itemVariation: CollectionItemVariation | undefined): string {
    if (!itemVariation) {
        return 'Sin historial';
    }
    if (itemVariation.trend === 'up') {
        return 'Subio';
    }
    if (itemVariation.trend === 'down') {
        return 'Bajo';
    }
    if (itemVariation.trend === 'equal') {
        return 'Sin cambio';
    }
    return 'Sin historial';
}

function collectionVariationTrend(): CollectionItemVariation['trend'] | undefined {
    if (variation.value?.total_difference_percent === null || variation.value?.total_difference_percent === undefined) {
        return undefined;
    }

    const amount = Number(variation.value.total_difference_percent);
    if (amount > 0) {
        return 'up';
    }
    if (amount < 0) {
        return 'down';
    }
    return 'equal';
}

function normalizeBadgeText(value: string | null | undefined): string | null {
    const normalized = value?.trim();
    if (!normalized || normalized.toLowerCase() === 'none') {
        return null;
    }
    return normalized;
}

function resolveFinishLabel(item: CollectionItem): string | null {
    const finish = normalizeBadgeText(item.finish);
    if (!finish) {
        return item.is_pokeball ? 'Pokeball' : null;
    }

    return item.is_pokeball ? `${finish} Pokeball` : finish;
}

function resolveRarityLabel(item: CollectionItem): string | null {
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

function normalizeEditForm(item: CollectionItem): void {
    editForm.quantity = item.quantity;
    editForm.language = item.language || 'Espanol';
    editForm.condition = item.condition || 'Mint';
    editForm.finish = item.finish || 'Normal';
    editForm.is_pokeball = item.is_pokeball;
    editForm.is_for_sale = item.is_for_sale;
    editForm.base_price = item.base_price === null ? null : Number(item.base_price);
    editForm.base_price_currency = item.base_price_currency || 'USD';
    editForm.sale_margin_percent = item.sale_margin_percent === null ? null : Number(item.sale_margin_percent);
    editForm.sale_price = item.sale_price === null ? null : Number(item.sale_price);
    editForm.sale_status = item.sale_status || 'not_available';
    editForm.notes = item.notes || '';
}

async function openMoveDialog(): Promise<void> {
    if (!selectedItems.value.length) {
        toast.add({ severity: 'warn', summary: 'Seleccion requerida', detail: 'Selecciona una o mas cartas para mover.', life: 3000 });
        return;
    }

    try {
        availableCollections.value = await listCollections('edit');
        targetCollectionId.value = targetCollectionOptions.value[0]?.value ?? null;
        moveDialogVisible.value = true;
    } catch (err) {
        const detail = err instanceof Error ? err.message : 'No fue posible cargar las colecciones disponibles.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    }
}

function toggleOptionsMenu(event: Event): void {
    optionsMenu.value?.toggle(event);
}

function toggleSelectedOptionsMenu(event: Event): void {
    selectedOptionsMenu.value?.toggle(event);
}

async function loadPage(): Promise<void> {
    if (!Number.isFinite(collectionId.value)) {
        error.value = 'Coleccion invalida.';
        loading.value = false;
        return;
    }

    loading.value = true;
    error.value = '';
    try {
        const [collectionResponse, itemsResponse, variationResponse] = await Promise.all([
            getCollection(collectionId.value),
            listCollectionItems(collectionId.value),
            getCollectionPriceVariation(collectionId.value)
        ]);
        collection.value = collectionResponse;
        items.value = itemsResponse;
        variation.value = variationResponse;
        selectedItems.value = [];
        void hydrateCardThumbnails(itemsResponse);
    } catch (err) {
        error.value = err instanceof Error ? err.message : 'No fue posible cargar la coleccion.';
        toast.add({ severity: 'error', summary: 'Error', detail: error.value, life: 4000 });
    } finally {
        loading.value = false;
    }
}

async function openPreview(item: CollectionItem): Promise<void> {
    previewItem.value = item;
    previewVisible.value = true;
    previewLoading.value = true;
    previewImageUrl.value = getCardImageSrc(item, 'large');

    try {
        const cached = await cacheCardImage(item, 'large');
        if (previewItem.value?.id === item.id && cached) {
            previewImageUrl.value = cached;
        }
    } finally {
        if (previewItem.value?.id === item.id) {
            previewLoading.value = false;
        }
    }
}

function openEdit(item: CollectionItem): void {
    selectedItem.value = item;
    normalizeEditForm(item);
    editVisible.value = true;
}

function openPriceHistory(item: CollectionItem): void {
    priceHistoryItem.value = item;
    priceHistoryVisible.value = true;
}

async function saveEdit(): Promise<void> {
    if (!selectedItem.value) {
        return;
    }

    saving.value = true;
    try {
        const updated = await updateCollectionItem(selectedItem.value.id, {
            quantity: editForm.quantity,
            language: editForm.language,
            condition: editForm.condition,
            finish: editForm.finish,
            is_pokeball: editForm.is_pokeball,
            is_for_sale: editForm.is_for_sale,
            base_price: editForm.base_price,
            base_price_currency: editForm.base_price_currency,
            sale_margin_percent: editForm.sale_margin_percent,
            sale_price: editForm.sale_price,
            sale_status: editForm.sale_status,
            notes: editForm.notes || null
        });
        items.value = items.value.map((item) => (item.id === updated.id ? updated : item));
        toast.add({ severity: 'success', summary: 'Item actualizado', detail: 'Los cambios fueron guardados.', life: 3000 });
        editVisible.value = false;
        await loadPage();
    } catch (err) {
        const detail = err instanceof Error ? err.message : 'No fue posible actualizar el item.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        saving.value = false;
    }
}

async function saveCollectionSettings(payload: UpdateCollectionPayload): Promise<void> {
    if (!collection.value) {
        return;
    }

    collectionSaving.value = true;
    try {
        await updateCollection(collection.value.id, payload);
        toast.add({ severity: 'success', summary: 'Coleccion actualizada', detail: 'La configuracion fue guardada.', life: 3000 });
        collectionDialogVisible.value = false;
        await loadPage();
    } catch (err) {
        const detail = err instanceof Error ? err.message : 'No fue posible guardar la configuracion.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        collectionSaving.value = false;
    }
}

async function handleCollaboratorsChanged(updatedCollection?: Collection | null): Promise<void> {
    if (updatedCollection) {
        collection.value = updatedCollection;
    }
    await loadPage();
}

async function handleRefreshPrices(): Promise<void> {
    if (!collection.value) {
        return;
    }

    refreshingPrices.value = true;
    try {
        const response = await refreshCollectionPrices(collection.value.id);
        const hasFailures = response.items_failed > 0;
        toast.add({
            severity: hasFailures ? 'warn' : 'success',
            summary: hasFailures ? 'Valorizacion actualizada con observaciones' : 'Valorizacion actualizada',
            detail: `${response.updated_items} cartas actualizadas, ${response.items_without_price} sin precio, ${response.items_failed} con error.`,
            life: hasFailures ? 6500 : 4500
        });
        await loadPage();
    } catch (err) {
        const detail = err instanceof Error ? err.message : 'No fue posible actualizar la valorizacion.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 5000 });
    } finally {
        refreshingPrices.value = false;
    }
}

function confirmDeleteCollection(): void {
    if (!collection.value) {
        return;
    }

    confirm.require({
        message: `Se eliminara la coleccion ${collection.value.name} y todas sus cartas registradas.`,
        header: 'Eliminar coleccion',
        icon: 'pi pi-exclamation-triangle',
        acceptLabel: 'Eliminar',
        rejectLabel: 'Cancelar',
        acceptClass: 'p-button-danger',
        accept: async () => {
            if (!collection.value) {
                return;
            }

            try {
                await deleteCollection(collection.value.id);
                toast.add({ severity: 'success', summary: 'Coleccion eliminada', detail: 'La coleccion fue eliminada correctamente.', life: 3000 });
                await router.push('/collections');
            } catch (err) {
                const detail = err instanceof Error ? err.message : 'No fue posible eliminar la coleccion.';
                toast.add({ severity: 'error', summary: 'Error', detail, life: 5000 });
            }
        }
    });
}

async function handleMoveSelectedItems(): Promise<void> {
    if (!selectedItems.value.length || !targetCollectionId.value) {
        toast.add({ severity: 'warn', summary: 'Datos incompletos', detail: 'Selecciona cartas y una coleccion destino.', life: 3000 });
        return;
    }

    movingItems.value = true;
    try {
        const response = await moveCollectionItems({
            item_ids: selectedItems.value.map((item) => item.id),
            target_collection_id: targetCollectionId.value
        });
        toast.add({
            severity: 'success',
            summary: 'Cartas movidas',
            detail: `${response.moved_items} items movidos, ${response.merged_items} fusionados en la coleccion destino.`,
            life: 4500
        });
        moveDialogVisible.value = false;
        selectedItems.value = [];
        await loadPage();
    } catch (err) {
        const detail = err instanceof Error ? err.message : 'No fue posible mover las cartas seleccionadas.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 5000 });
    } finally {
        movingItems.value = false;
    }
}

function removeItem(item: CollectionItem): void {
    confirm.require({
        message: `Se eliminara ${item.card.name} de ${collection.value?.name || 'la coleccion'}.`,
        header: 'Eliminar item',
        icon: 'pi pi-exclamation-triangle',
        acceptLabel: 'Eliminar',
        rejectLabel: 'Cancelar',
        acceptClass: 'p-button-danger',
        accept: async () => {
            try {
                await deleteCollectionItem(item.id);
                items.value = items.value.filter((entry) => entry.id !== item.id);
                toast.add({ severity: 'success', summary: 'Item eliminado', detail: 'La carta fue removida de la coleccion.', life: 3000 });
                await loadPage();
            } catch (err) {
                const detail = err instanceof Error ? err.message : 'No fue posible eliminar el item.';
                toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
            }
        }
    });
}

watch(
    () => route.params.id,
    () => {
        loadPage();
    }
);

watch(
    () => editForm.finish,
    (finish) => {
        if (finish !== 'Reverse Holo') {
            editForm.is_pokeball = false;
        }
    }
);

onMounted(loadPage);
onBeforeUnmount(() => {
    revokeObjectUrls();
});
</script>

<template>
    <div class="flex flex-col gap-6">
        <div class="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
            <div>
                <Button label="Volver a colecciones" icon="pi pi-arrow-left" text class="!px-0 mb-3" @click="router.push('/collections')" />
                <div class="text-3xl font-semibold">{{ collection?.name || 'Detalle de coleccion' }}</div>
                <p class="text-surface-500 mb-0">{{ collection?.description || 'Revisa, edita y elimina las cartas fisicas registradas en esta coleccion.' }}</p>
            </div>
            <div class="flex flex-wrap items-center gap-3">
                <Tag :value="`${items.length} items`" severity="info" />
                <Tag
                    v-if="collection"
                    v-tooltip.bottom="collection.sort_by_pokedex ? 'Las cartas Pokemon se muestran ordenadas por numero de Pokedex. Las cartas no Pokemon quedan al final.' : 'La coleccion mantiene el orden manual de las cartas.'"
                    :value="collection.sort_by_pokedex ? 'Orden Pokedex activo' : 'Orden manual'"
                    :severity="collection.sort_by_pokedex ? 'warn' : 'secondary'"
                />
                <Button
                    v-if="selectedItems.length && canEditCollection"
                    :label="`${selectedItems.length} seleccionadas`"
                    icon="pi pi-angle-down"
                    iconPos="right"
                    outlined
                    @click="toggleSelectedOptionsMenu"
                />
                <Menu ref="selectedOptionsMenu" :model="selectedCollectionOptions" popup />
                <Button label="Opciones" icon="pi pi-angle-down" iconPos="right" outlined @click="toggleOptionsMenu" />
                <Menu ref="optionsMenu" :model="collectionOptions" popup />
            </div>
        </div>

        <Message v-if="error" severity="error">{{ error }}</Message>

        <div v-if="loading" class="card">
            <Skeleton height="24rem" borderRadius="1rem" />
        </div>

        <template v-else>
            <div class="grid grid-cols-12 gap-6">
                <div class="col-span-12">
                    <div class="card h-full">
                        <div v-if="variation" class="flex flex-col gap-4">
                            <div class="flex flex-col 2xl:flex-row 2xl:items-center 2xl:justify-between gap-4">
                                <div class="flex items-start gap-3">
                                    <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                                        <i class="pi pi-chart-line text-lg"></i>
                                    </div>
                                    <div>
                                        <div class="text-xl font-semibold">Variacion</div>
                                        <p class="text-surface-500 mb-0 text-sm">Resumen rapido de la ultima captura de precios.</p>
                                    </div>
                                </div>
                                <div class="flex flex-wrap items-center gap-3">
                                    <div class="flex items-center gap-2 rounded-2xl border border-surface-200 dark:border-surface-700 px-3 py-2">
                                        <i class="pi pi-arrow-up text-emerald-500"></i>
                                        <span class="text-sm text-surface-500">Subieron</span>
                                        <span class="text-base font-semibold">{{ variation.items_up }}</span>
                                    </div>
                                    <div class="flex items-center gap-2 rounded-2xl border border-surface-200 dark:border-surface-700 px-3 py-2">
                                        <i class="pi pi-arrow-down text-rose-500"></i>
                                        <span class="text-sm text-surface-500">Bajaron</span>
                                        <span class="text-base font-semibold">{{ variation.items_down }}</span>
                                    </div>
                                    <div class="flex items-center gap-2 rounded-2xl border border-emerald-500/25 bg-emerald-500/10 px-3 py-2">
                                        <i class="pi pi-wallet text-emerald-400"></i>
                                        <span class="text-sm text-surface-500">Costo base</span>
                                        <span class="text-base font-semibold text-emerald-300">{{ formatMoney(totalBaseCost) }}</span>
                                    </div>
                                    <div class="flex items-center gap-2 rounded-2xl border border-yellow-500/25 bg-yellow-500/10 px-3 py-2">
                                        <i class="pi pi-dollar text-yellow-300"></i>
                                        <span class="text-sm text-surface-500">Costo venta</span>
                                        <span class="text-base font-semibold text-yellow-200">{{ formatMoney(totalSaleCost) }}</span>
                                    </div>
                                    <Tag :severity="variationSeverity(collectionVariationTrend())" :value="variation.total_difference_percent !== null ? formatPercent(variation.total_difference_percent) : 'Sin historial'" />
                                    <div class="rounded-2xl bg-surface-50 dark:bg-surface-900 px-3 py-2 text-sm">
                                        <span class="text-surface-500">Diferencia total: </span>
                                        <span class="font-semibold">{{ formatMoney(variation.total_difference) }}</span>
                                    </div>
                                    <Button
                                        :label="variationExpanded ? 'Ocultar detalle' : 'Ver detalle'"
                                        :icon="variationExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
                                        size="small"
                                        outlined
                                        @click="variationExpanded = !variationExpanded"
                                    />
                                </div>
                            </div>

                            <Transition
                                enterActiveClass="transition-all duration-300 ease-out"
                                enterFromClass="opacity-0 -translate-y-2"
                                enterToClass="opacity-100 translate-y-0"
                                leaveActiveClass="transition-all duration-200 ease-in"
                                leaveFromClass="opacity-100 translate-y-0"
                                leaveToClass="opacity-0 -translate-y-2"
                            >
                                <div v-if="variationExpanded" class="grid grid-cols-12 gap-4">
                                    <div class="col-span-12 md:col-span-6 xl:col-span-3">
                                        <div class="h-full rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 p-4">
                                            <div class="flex items-center gap-3 mb-3">
                                                <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400">
                                                    <i class="pi pi-arrow-up-right"></i>
                                                </div>
                                                <div>
                                                    <div class="text-sm text-surface-500">Subieron</div>
                                                    <div class="text-2xl font-semibold">{{ variation.items_up }}</div>
                                                </div>
                                            </div>
                                            <p class="text-sm text-surface-500 mb-0">Cartas cuyo precio base subio respecto a la captura anterior.</p>
                                        </div>
                                    </div>
                                    <div class="col-span-12 md:col-span-6 xl:col-span-3">
                                        <div class="h-full rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 p-4">
                                            <div class="flex items-center gap-3 mb-3">
                                                <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-500/15 text-rose-400">
                                                    <i class="pi pi-arrow-down-right"></i>
                                                </div>
                                                <div>
                                                    <div class="text-sm text-surface-500">Bajaron</div>
                                                    <div class="text-2xl font-semibold">{{ variation.items_down }}</div>
                                                </div>
                                            </div>
                                            <p class="text-sm text-surface-500 mb-0">Cartas cuyo precio base bajo desde la ultima valorizacion.</p>
                                        </div>
                                    </div>
                                    <div class="col-span-12 md:col-span-6 xl:col-span-3">
                                        <div class="h-full rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 p-4">
                                            <div class="flex items-center gap-3 mb-3">
                                                <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-400">
                                                    <i class="pi pi-minus"></i>
                                                </div>
                                                <div>
                                                    <div class="text-sm text-surface-500">Sin cambios</div>
                                                    <div class="text-2xl font-semibold">{{ variation.items_equal }}</div>
                                                </div>
                                            </div>
                                            <p class="text-sm text-surface-500 mb-0">Cartas que mantienen el mismo valor base entre capturas.</p>
                                        </div>
                                    </div>
                                    <div class="col-span-12 md:col-span-6 xl:col-span-3">
                                        <div class="h-full rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 p-4">
                                            <div class="flex items-center gap-3 mb-3">
                                                <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-500/15 text-orange-400">
                                                    <i class="pi pi-history"></i>
                                                </div>
                                                <div>
                                                    <div class="text-sm text-surface-500">Sin historico</div>
                                                    <div class="text-2xl font-semibold">{{ variation.items_without_history }}</div>
                                                </div>
                                            </div>
                                            <p class="text-sm text-surface-500 mb-0">Cartas sin referencia previa para calcular variacion porcentual.</p>
                                        </div>
                                    </div>
                                </div>
                            </Transition>
                        </div>
                        <div class="hidden">
                        <div class="flex items-start justify-between gap-3 mb-4">
                            <div>
                                <div class="text-xl font-semibold">Variación</div>
                                <p class="text-surface-500 mb-0 text-sm">Resumen rapido de la ultima captura de precios.</p>
                            </div>
                            <Tag v-if="variation" :value="`${variation.total_items} items`" severity="info" />
                        </div>
                        <div v-if="variation" class="grid grid-cols-2 gap-4">
                            <div class="p-3 rounded-2xl bg-surface-50 dark:bg-surface-900">
                                <div class="text-surface-500 mb-1">Subieron</div>
                                <div class="text-xl font-semibold">{{ variation.items_up }}</div>
                            </div>
                            <div class="p-3 rounded-2xl bg-surface-50 dark:bg-surface-900">
                                <div class="text-surface-500 mb-1">Bajaron</div>
                                <div class="text-xl font-semibold">{{ variation.items_down }}</div>
                            </div>
                            <div class="p-3 rounded-2xl bg-surface-50 dark:bg-surface-900">
                                <div class="text-surface-500 mb-1">Sin cambios</div>
                                <div class="text-xl font-semibold">{{ variation.items_equal }}</div>
                            </div>
                            <div class="p-3 rounded-2xl bg-surface-50 dark:bg-surface-900">
                                <div class="text-surface-500 mb-1">Sin historico</div>
                                <div class="text-xl font-semibold">{{ variation.items_without_history }}</div>
                            </div>
                        </div>

                        <Divider />

                        <div v-if="variation" class="flex flex-col gap-3">
                            <div class="flex items-center justify-between">
                                <span class="text-surface-500">Diferencia total</span>
                                <span class="font-semibold">{{ formatMoney(variation.total_difference) }}</span>
                            </div>
                            <div class="flex items-center justify-between">
                                <span class="text-surface-500">Variacion</span>
                                <Tag
                                    :severity="variationSeverity(
                                        Number(variation.total_difference_percent ?? 0) > 0 ? 'up' : Number(variation.total_difference_percent ?? 0) < 0 ? 'down' : 'equal'
                                    )"
                                    :value="variation.total_difference_percent !== null ? formatPercent(variation.total_difference_percent) : 'Sin historial'"
                                />
                            </div>
                        </div>
                        </div>
                    </div>
                </div>

                <div class="col-span-12">
                    <div v-if="!items.length" class="card text-center py-10">
                        <i class="pi pi-inbox text-4xl text-surface-400 mb-4"></i>
                        <div class="text-2xl font-semibold mb-2">Sin cartas todavia</div>
                        <p class="text-surface-500 mb-4">Agrega cartas desde la vista de busqueda para verlas aqui.</p>
                        <div class="flex justify-center gap-3">
                            <Button label="Ir a buscar carta" icon="pi pi-search" @click="router.push('/cards/search')" />
                            <Button v-if="collection && canManageCollection" label="Configurar coleccion" icon="pi pi-cog" outlined @click="collectionDialogVisible = true" />
                        </div>
                    </div>

                    <div v-else class="card">
                        <DataTable v-model:selection="selectedItems" :value="items" paginator :rows="10" dataKey="id" responsiveLayout="scroll">
                            <Column v-if="canEditCollection" selectionMode="multiple" headerStyle="width: 3rem" />
                            <Column header="Carta" style="min-width: 20rem">
                                <template #body="{ data }">
                                    <div class="flex items-center gap-4">
                                        <button
                                            type="button"
                                            class="group flex-shrink-0 rounded-xl border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900 p-1 transition hover:border-primary cursor-pointer"
                                            @click="openPreview(data)"
                                        >
                                            <img
                                                v-if="getCardImageSrc(data)"
                                                :src="getCardImageSrc(data) || undefined"
                                                :alt="data.card.name"
                                                class="h-20 w-14 rounded-md object-contain"
                                            />
                                            <div v-else class="h-20 w-14 rounded-md flex items-center justify-center text-xs text-surface-500">Sin imagen</div>
                                        </button>
                                        <div>
                                            <div class="font-semibold text-lg">{{ data.card.name }}</div>
                                            <div class="text-surface-500">{{ data.card.set_name }} - {{ data.card.number }}</div>
                                            <div class="flex flex-wrap items-center gap-2 mt-2">
                                                <Tag v-if="resolveFinishLabel(data)" :value="resolveFinishLabel(data) || undefined" severity="info" />
                                                <Tag v-if="resolveRarityLabel(data)" :value="resolveRarityLabel(data) || undefined" severity="contrast" />
                                            </div>
                                        </div>
                                    </div>
                                </template>
                            </Column>
                            <Column header="Pokedex" style="min-width: 8rem">
                                <template #body="{ data }">
                                    {{ data.card.pokedex_number ? `#${data.card.pokedex_number}` : '-' }}
                                </template>
                            </Column>
                            <Column field="quantity" header="Cantidad" />
                            <Column header="Base anterior" style="min-width: 10rem">
                                <template #body="{ data }">
                                    {{ formatMoney(variationMap[data.id]?.previous_price, variationMap[data.id]?.currency || data.base_price_currency || 'USD') }}
                                </template>
                            </Column>
                            <Column header="Base actual" style="min-width: 10rem">
                                <template #body="{ data }">
                                    {{ formatMoney(variationMap[data.id]?.current_price ?? data.base_price, variationMap[data.id]?.currency || data.base_price_currency || 'USD') }}
                                </template>
                            </Column>
                            <Column header="Diferencia" style="min-width: 10rem">
                                <template #body="{ data }">
                                    <span v-if="variationMap[data.id]?.difference !== null">
                                        {{ formatMoney(variationMap[data.id]?.difference, variationMap[data.id]?.currency || data.base_price_currency || 'USD') }}
                                    </span>
                                    <span v-else class="text-surface-500">-</span>
                                </template>
                            </Column>
                            <Column header="%" style="min-width: 8rem">
                                <template #body="{ data }">
                                    <span v-if="variationMap[data.id]?.difference_percent !== null">
                                        {{ formatPercent(variationMap[data.id]?.difference_percent) }}
                                    </span>
                                    <span v-else class="text-surface-500">-</span>
                                </template>
                            </Column>
                            <Column header="Tendencia" style="min-width: 9rem">
                                <template #body="{ data }">
                                    <Tag :severity="variationSeverity(variationMap[data.id]?.trend)" :value="variationLabel(variationMap[data.id])" />
                                </template>
                            </Column>
                            <Column header="Precio venta">
                                <template #body="{ data }">{{ data.sale_price ? formatMoney(Number(data.sale_price), data.base_price_currency || 'USD') : '-' }}</template>
                            </Column>
                            <Column header="Acciones" style="min-width: 12rem">
                                <template #body="{ data }">
                                    <div class="flex gap-2">
                                        <Button icon="pi pi-eye" rounded text @click="openPreview(data)" />
                                        <Button icon="pi pi-chart-line" rounded text @click="openPriceHistory(data)" />
                                        <Button v-if="canEditCollection" icon="pi pi-pencil" rounded text @click="openEdit(data)" />
                                        <Button v-if="canEditCollection" icon="pi pi-trash" rounded text severity="danger" @click="removeItem(data)" />
                                    </div>
                                </template>
                            </Column>
                        </DataTable>
                    </div>
                </div>
            </div>
        </template>

        <Dialog v-model:visible="editVisible" modal header="Editar item" :style="{ width: '40rem' }">
            <div class="grid grid-cols-12 gap-4">
                <div class="col-span-12 md:col-span-4">
                    <label class="block text-sm mb-2">Cantidad</label>
                    <InputNumber v-model="editForm.quantity" :min="1" class="w-full" inputClass="w-full" />
                </div>
                <div class="col-span-12 md:col-span-4">
                    <label class="block text-sm mb-2">Idioma</label>
                    <Select v-model="editForm.language" :options="languageOptions" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <div class="col-span-12 md:col-span-4">
                    <label class="block text-sm mb-2">Estado</label>
                    <Select v-model="editForm.condition" :options="conditionOptions" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <div class="col-span-12 md:col-span-6">
                    <label class="block text-sm mb-2">Acabado</label>
                    <Select v-model="editForm.finish" :options="finishOptions" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <div class="col-span-12 md:col-span-6">
                    <label class="block text-sm mb-2">Variante Pokeball</label>
                    <div class="flex items-center gap-3 min-h-12 px-3 rounded-xl border border-surface-200 dark:border-surface-700">
                        <ToggleSwitch v-model="editForm.is_pokeball" :disabled="editForm.finish !== 'Reverse Holo'" />
                        <span>{{ editForm.finish === 'Reverse Holo' ? (editForm.is_pokeball ? 'Activada' : 'Desactivada') : 'Disponible solo para Reverse Holo' }}</span>
                    </div>
                </div>
                <div class="col-span-12 md:col-span-6">
                    <label class="block text-sm mb-2">Estado de venta</label>
                    <Select v-model="editForm.sale_status" :options="saleStatusOptions" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <div class="col-span-12 md:col-span-4">
                    <label class="block text-sm mb-2">Precio base</label>
                    <InputNumber v-model="editForm.base_price" mode="currency" :currency="editForm.base_price_currency" locale="en-US" class="w-full" inputClass="w-full" />
                </div>
                <div class="col-span-12 md:col-span-4">
                    <label class="block text-sm mb-2">Margen</label>
                    <InputNumber v-model="editForm.sale_margin_percent" suffix="%" :min="0" class="w-full" inputClass="w-full" />
                </div>
                <div class="col-span-12 md:col-span-4">
                    <label class="block text-sm mb-2">Precio venta</label>
                    <InputNumber v-model="editForm.sale_price" mode="currency" :currency="editForm.base_price_currency" locale="en-US" class="w-full" inputClass="w-full" />
                </div>
                <div class="col-span-12">
                    <div class="flex items-center gap-3 min-h-12 px-3 rounded-xl border border-surface-200 dark:border-surface-700">
                        <ToggleSwitch v-model="editForm.is_for_sale" />
                        <span>{{ editForm.is_for_sale ? 'Disponible para venta' : 'No disponible para venta' }}</span>
                    </div>
                </div>
                <div class="col-span-12">
                    <label class="block text-sm mb-2">Notas</label>
                    <Textarea v-model="editForm.notes" rows="3" class="w-full" />
                </div>
            </div>

            <template #footer>
                <div class="flex justify-end gap-3">
                    <Button label="Cancelar" severity="secondary" outlined @click="editVisible = false" />
                    <Button label="Guardar cambios" icon="pi pi-save" :loading="saving" @click="saveEdit" />
                </div>
            </template>
        </Dialog>

        <CollectionSettingsDialog
            v-model:visible="collectionDialogVisible"
            :collection="collection"
            mode="edit"
            :saving="collectionSaving"
            :can-manage-collaborators="canManageCollection"
            @manage-collaborators="collaboratorsDialogVisible = true"
            @save="saveCollectionSettings"
        />
        <CollectionCollaboratorsDialog
            v-model:visible="collaboratorsDialogVisible"
            :collection="collection"
            @changed="handleCollaboratorsChanged"
        />
        <CollectionItemPriceHistoryDialog
            v-model:visible="priceHistoryVisible"
            :item-id="priceHistoryItem?.id ?? null"
            :title="priceHistoryItem?.card.name || 'Carta'"
            :subtitle="priceHistoryItem ? `${priceHistoryItem.card.set_name || 'Edicion desconocida'} - ${priceHistoryItem.card.number}` : ''"
            :image-src="priceHistoryItem ? getCardImageSrc(priceHistoryItem, 'large') : null"
            :image-alt="priceHistoryItem?.card.name || 'Carta'"
            :current-base-price="priceHistoryItem?.base_price ?? null"
            :current-sale-price="priceHistoryItem?.sale_price ?? null"
            :currency="priceHistoryItem?.base_price_currency || 'USD'"
        />
        <CollectionExportDialog v-model:visible="exportDialogVisible" :collection="collection" :items="items" />
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
                            <Tag v-if="resolveFinishLabel(previewItem)" :value="resolveFinishLabel(previewItem) || undefined" severity="info" />
                            <Tag v-if="resolveRarityLabel(previewItem)" :value="resolveRarityLabel(previewItem) || undefined" severity="contrast" />
                            <Tag v-if="previewItem.card.pokedex_number" :value="`Pokedex #${previewItem.card.pokedex_number}`" severity="info" />
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="rounded-xl bg-surface-50 dark:bg-surface-900 p-4">
                                <div class="text-sm text-surface-500 mb-1">Estado</div>
                                <div class="font-medium">{{ previewItem.condition || 'Sin estado' }}</div>
                            </div>
                            <div class="rounded-xl bg-surface-50 dark:bg-surface-900 p-4">
                                <div class="text-sm text-surface-500 mb-1">Acabado</div>
                                <div class="font-medium">{{ previewItem.finish || 'Normal' }}</div>
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
                            <div>
                                <div class="text-sm text-surface-500 mb-1">Precio base</div>
                                <div class="font-semibold">{{ previewItem.base_price ? formatMoney(previewItem.base_price, previewItem.base_price_currency || 'USD') : '-' }}</div>
                            </div>
                            <div>
                                <div class="text-sm text-surface-500 mb-1">Precio venta</div>
                                <div class="font-semibold">{{ previewItem.sale_price ? formatMoney(previewItem.sale_price, previewItem.base_price_currency || 'USD') : '-' }}</div>
                            </div>
                        </div>
                        <div v-if="previewItem.notes">
                            <div class="text-sm text-surface-500 mb-1">Notas</div>
                            <div class="rounded-xl border border-surface-200 dark:border-surface-700 p-4 whitespace-pre-wrap">{{ previewItem.notes }}</div>
                        </div>
                    </div>
                </div>
            </div>
        </Dialog>
        <Dialog v-model:visible="moveDialogVisible" modal header="Mover cartas a otra coleccion" :style="{ width: '30rem' }">
            <div class="flex flex-col gap-4">
                <p class="text-surface-500 mb-0">
                    Se moveran {{ selectedItems.length }} cartas desde <strong>{{ collection?.name || 'la coleccion actual' }}</strong>.
                </p>
                <div>
                    <label class="block text-sm mb-2">Coleccion destino</label>
                    <Select v-model="targetCollectionId" :options="targetCollectionOptions" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <Message severity="info" :closable="false">
                    Si ya existe una carta igual en la coleccion destino, el sistema fusionara las cantidades automaticamente.
                </Message>
            </div>

            <template #footer>
                <div class="flex justify-end gap-3">
                    <Button label="Cancelar" severity="secondary" outlined @click="moveDialogVisible = false" />
                    <Button label="Mover cartas" icon="pi pi-arrow-right-arrow-left" :loading="movingItems" :disabled="!targetCollectionId || !selectedItems.length" @click="handleMoveSelectedItems" />
                </div>
            </template>
        </Dialog>
    </div>
</template>
