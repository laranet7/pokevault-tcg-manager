<script setup lang="ts">
import { getCollectionItemPriceHistory } from '@/api/collectionItemsApi';
import { useLayout } from '@/layout/composables/layout';
import type { PriceHistoryEntry } from '@/types/pricing';
import { computed, onMounted, ref, watch } from 'vue';
import { useToast } from 'primevue/usetoast';

type RangePreset = '7d' | '30d' | '90d' | 'all';

const props = defineProps<{
    visible: boolean;
    itemId: number | null;
    title: string;
    subtitle?: string | null;
    imageSrc?: string | null;
    imageAlt?: string | null;
    defaultRangeDays?: 7 | 30 | 90;
    currentBasePrice?: number | string | null;
    currentSalePrice?: number | string | null;
    currency?: string | null;
}>();

const emit = defineEmits<{
    'update:visible': [value: boolean];
}>();

const toast = useToast();
const { layoutConfig, isDarkTheme } = useLayout();

const loading = ref(false);
const error = ref('');
const history = ref<PriceHistoryEntry[]>([]);
const selectedPreset = ref<RangePreset>('30d');
const startDate = ref<Date | null>(null);
const endDate = ref<Date | null>(null);
const chartData = ref();
const chartOptions = ref();
const syncingPreset = ref(false);

const presetOptions: Array<{ label: string; value: RangePreset }> = [
    { label: '7D', value: '7d' },
    { label: '30D', value: '30d' },
    { label: '90D', value: '90d' },
    { label: 'Todo', value: 'all' }
];

function resolveDefaultPreset(): RangePreset {
    if (props.defaultRangeDays === 7) {
        return '7d';
    }
    if (props.defaultRangeDays === 90) {
        return '90d';
    }
    return '30d';
}

const historyWithDates = computed(() =>
    history.value.map((entry) => ({
        ...entry,
        capturedDate: new Date(entry.captured_at)
    }))
);

const minAvailableDate = computed<Date | null>(() => historyWithDates.value[0]?.capturedDate ?? null);
const maxAvailableDate = computed<Date | null>(() => historyWithDates.value[historyWithDates.value.length - 1]?.capturedDate ?? null);

const filteredHistory = computed(() => {
    if (!historyWithDates.value.length) {
        return [];
    }

    const start = startDate.value ? normalizeDateStart(startDate.value) : null;
    const end = endDate.value ? normalizeDateEnd(endDate.value) : null;

    return historyWithDates.value.filter((entry) => {
        if (start && entry.capturedDate < start) {
            return false;
        }
        if (end && entry.capturedDate > end) {
            return false;
        }
        return true;
    });
});

const latestEntry = computed(() => filteredHistory.value[filteredHistory.value.length - 1] ?? historyWithDates.value[historyWithDates.value.length - 1] ?? null);
const earliestEntry = computed(() => filteredHistory.value[0] ?? null);
const currentCurrency = computed(() => latestEntry.value?.currency || props.currency || 'USD');
const currentBaseValue = computed(() => latestEntry.value?.base_price ?? props.currentBasePrice ?? null);
const currentSaleValue = computed(() => latestEntry.value?.sale_price ?? props.currentSalePrice ?? null);
const priceDifference = computed(() => {
    if (!earliestEntry.value || !latestEntry.value || earliestEntry.value === latestEntry.value) {
        return null;
    }

    const first = Number(earliestEntry.value.base_price ?? 0);
    const last = Number(latestEntry.value.base_price ?? 0);
    return Number((last - first).toFixed(2));
});
const priceDifferencePercent = computed(() => {
    if (!earliestEntry.value || !latestEntry.value || earliestEntry.value === latestEntry.value) {
        return null;
    }

    const first = Number(earliestEntry.value.base_price ?? 0);
    const last = Number(latestEntry.value.base_price ?? 0);
    if (!first) {
        return null;
    }

    return Number((((last - first) / first) * 100).toFixed(2));
});

const historyRows = computed(() =>
    filteredHistory.value.map((entry, index, list) => {
        const previous = index > 0 ? list[index - 1] : null;
        const previousBase = Number(previous?.base_price ?? 0);
        const currentBase = Number(entry.base_price ?? 0);
        const difference = previous ? Number((currentBase - previousBase).toFixed(2)) : null;
        const differencePercent = previous && previousBase ? Number((((currentBase - previousBase) / previousBase) * 100).toFixed(2)) : null;

        return {
            ...entry,
            difference,
            differencePercent
        };
    })
);

function normalizeDateStart(value: Date): Date {
    const date = new Date(value);
    date.setHours(0, 0, 0, 0);
    return date;
}

function normalizeDateEnd(value: Date): Date {
    const date = new Date(value);
    date.setHours(23, 59, 59, 999);
    return date;
}

function shiftDate(base: Date, days: number): Date {
    const next = new Date(base);
    next.setDate(next.getDate() + days);
    return next;
}

function formatMoney(amount: number | string | null | undefined, currency = 'USD'): string {
    if (amount === null || amount === undefined || Number.isNaN(Number(amount))) {
        return '-';
    }

    return new Intl.NumberFormat('es-CL', {
        style: 'currency',
        currency,
        maximumFractionDigits: 2
    }).format(Number(amount));
}

function formatPercent(value: number | string | null | undefined): string {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return 'Sin historial';
    }

    const amount = Number(value);
    return `${amount > 0 ? '+' : ''}${amount.toFixed(2)}%`;
}

function formatDate(value: string | Date): string {
    const date = value instanceof Date ? value : new Date(value);
    return new Intl.DateTimeFormat('es-CL', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    }).format(date);
}

function formatDateTime(value: string | Date): string {
    const date = value instanceof Date ? value : new Date(value);
    return new Intl.DateTimeFormat('es-CL', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

function variationSeverity(value: number | null): 'success' | 'danger' | 'secondary' {
    if (value === null) {
        return 'secondary';
    }
    if (value > 0) {
        return 'success';
    }
    if (value < 0) {
        return 'danger';
    }
    return 'secondary';
}

function applyPreset(preset: RangePreset): void {
    syncingPreset.value = true;
    selectedPreset.value = preset;

    if (!minAvailableDate.value || !maxAvailableDate.value) {
        startDate.value = null;
        endDate.value = null;
        syncingPreset.value = false;
        return;
    }

    const latest = maxAvailableDate.value;
    let start = minAvailableDate.value;

    if (preset === '7d') {
        start = shiftDate(latest, -6);
    } else if (preset === '30d') {
        start = shiftDate(latest, -29);
    } else if (preset === '90d') {
        start = shiftDate(latest, -89);
    }

    startDate.value = start < minAvailableDate.value ? minAvailableDate.value : start;
    endDate.value = latest;
    syncingPreset.value = false;
}

function syncChart(): void {
    const documentStyle = getComputedStyle(document.documentElement);
    const textMutedColor = documentStyle.getPropertyValue('--text-color-secondary');
    const textColor = documentStyle.getPropertyValue('--text-color');
    const surfaceBorder = documentStyle.getPropertyValue('--surface-border');
    const primary500 = documentStyle.getPropertyValue('--p-primary-500');
    const primary300 = documentStyle.getPropertyValue('--p-primary-300');
    const saleColor = documentStyle.getPropertyValue('--p-amber-400');

    chartData.value = {
        labels: filteredHistory.value.map((entry) => formatDate(entry.captured_at)),
        datasets: [
            {
                label: 'Precio base',
                data: filteredHistory.value.map((entry) => Number(entry.base_price ?? 0)),
                fill: true,
                tension: 0.35,
                borderColor: primary500,
                backgroundColor: `${primary300}22`,
                borderWidth: 3,
                pointRadius: filteredHistory.value.length > 1 ? 3 : 5,
                pointHoverRadius: 5,
                pointBackgroundColor: primary500,
                pointBorderColor: primary500
            },
            {
                label: 'Precio venta',
                data: filteredHistory.value.map((entry) => (entry.sale_price === null ? null : Number(entry.sale_price))),
                fill: false,
                tension: 0.35,
                borderColor: saleColor,
                borderDash: [6, 6],
                borderWidth: 2,
                pointRadius: 2,
                pointHoverRadius: 4,
                spanGaps: true,
                hidden: filteredHistory.value.every((entry) => entry.sale_price === null)
            }
        ]
    };

    chartOptions.value = {
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: textColor,
                    usePointStyle: true
                }
            },
            tooltip: {
                callbacks: {
                    label(context: { dataset: { label?: string }; parsed: { y: number | null } }) {
                        const value = context.parsed.y;
                        return `${context.dataset.label || 'Precio'}: ${formatMoney(value, currentCurrency.value)}`;
                    }
                }
            }
        },
        scales: {
            x: {
                ticks: {
                    color: textMutedColor,
                    maxRotation: 0
                },
                grid: {
                    color: 'transparent',
                    drawBorder: false
                }
            },
            y: {
                ticks: {
                    color: textMutedColor,
                    callback(value: string | number) {
                        return formatMoney(value, currentCurrency.value);
                    }
                },
                grid: {
                    color: surfaceBorder,
                    drawBorder: false
                }
            }
        }
    };
}

async function loadHistory(): Promise<void> {
    if (!props.visible || !props.itemId) {
        return;
    }

    loading.value = true;
    error.value = '';
    try {
        history.value = await getCollectionItemPriceHistory(props.itemId);
        applyPreset(resolveDefaultPreset());
    } catch (err) {
        error.value = err instanceof Error ? err.message : 'No fue posible cargar el historico de precios.';
        toast.add({ severity: 'error', summary: 'Error', detail: error.value, life: 4000 });
        history.value = [];
    } finally {
        loading.value = false;
    }
}

watch(
    () => props.visible,
    (visible) => {
        if (!visible) {
            return;
        }
        void loadHistory();
    }
);

watch(
    () => props.itemId,
    () => {
        if (props.visible) {
            void loadHistory();
        }
    }
);

watch(
    () => props.defaultRangeDays,
    () => {
        if (props.visible && history.value.length) {
            applyPreset(resolveDefaultPreset());
        }
    }
);

watch([filteredHistory, () => layoutConfig.primary, () => layoutConfig.surface, isDarkTheme], () => {
    syncChart();
});

watch([startDate, endDate], ([start, end]) => {
    if (start && minAvailableDate.value && start < minAvailableDate.value) {
        startDate.value = minAvailableDate.value;
        return;
    }

    if (end && maxAvailableDate.value && end > maxAvailableDate.value) {
        endDate.value = maxAvailableDate.value;
        return;
    }

    if (start && end && start > end) {
        endDate.value = start;
    }

    if (!syncingPreset.value) {
        selectedPreset.value = 'all';
    }
});

onMounted(() => {
    syncChart();
});
</script>

<template>
    <Dialog
        :visible="visible"
        modal
        maximizable
        :header="`Historico de precios - ${title}`"
        :style="{ width: 'min(96vw, 76rem)' }"
        @update:visible="emit('update:visible', $event)"
    >
        <div class="flex flex-col gap-5">
            <div class="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
                <div class="flex flex-col sm:flex-row items-start gap-4">
                    <div class="w-full max-w-[8rem] shrink-0">
                        <div class="aspect-[63/88] rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 p-2 flex items-center justify-center">
                            <img
                                v-if="imageSrc"
                                :src="imageSrc"
                                :alt="imageAlt || title"
                                class="max-h-full max-w-full object-contain rounded-xl shadow-sm"
                            />
                            <div v-else class="px-4 text-center text-sm text-surface-500">Imagen no disponible</div>
                        </div>
                    </div>
                    <div class="pt-1">
                        <div class="text-2xl font-semibold">{{ title }}</div>
                        <div v-if="subtitle" class="text-surface-500 mt-1">{{ subtitle }}</div>
                        <div v-if="minAvailableDate && maxAvailableDate" class="text-sm text-surface-500 mt-3">
                            Rango disponible desde {{ formatDate(minAvailableDate) }} hasta {{ formatDate(maxAvailableDate) }}.
                        </div>
                    </div>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 min-w-full xl:min-w-[32rem]">
                    <div class="rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 p-4">
                        <div class="text-sm text-surface-500 mb-1">Precio base actual</div>
                        <div class="text-2xl font-semibold">{{ formatMoney(currentBaseValue, currentCurrency) }}</div>
                    </div>
                    <div class="rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 p-4">
                        <div class="text-sm text-surface-500 mb-1">Precio venta actual</div>
                        <div class="text-2xl font-semibold">{{ formatMoney(currentSaleValue, currentCurrency) }}</div>
                    </div>
                    <div class="rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 p-4">
                        <div class="text-sm text-surface-500 mb-1">Variacion del rango</div>
                        <div class="flex items-center gap-2">
                            <Tag :severity="variationSeverity(priceDifferencePercent)" :value="formatPercent(priceDifferencePercent)" />
                            <span class="font-semibold">{{ formatMoney(priceDifference, currentCurrency) }}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="rounded-2xl border border-surface-200 dark:border-surface-700 p-4">
                <div class="flex flex-col 2xl:flex-row 2xl:items-end 2xl:justify-between gap-4">
                    <div class="flex flex-wrap gap-2">
                        <Button
                            v-for="option in presetOptions"
                            :key="option.value"
                            :label="option.label"
                            size="small"
                            :outlined="selectedPreset !== option.value"
                            @click="applyPreset(option.value)"
                        />
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3 w-full 2xl:w-auto">
                        <div>
                            <label class="block text-sm mb-2">Desde</label>
                            <DatePicker v-model="startDate" :minDate="minAvailableDate || undefined" :maxDate="maxAvailableDate || undefined" showIcon fluid />
                        </div>
                        <div>
                            <label class="block text-sm mb-2">Hasta</label>
                            <DatePicker
                                v-model="endDate"
                                :minDate="startDate || minAvailableDate || undefined"
                                :maxDate="maxAvailableDate || undefined"
                                showIcon
                                fluid
                            />
                        </div>
                    </div>
                </div>
            </div>

            <Message v-if="error" severity="error">{{ error }}</Message>

            <div v-if="loading" class="rounded-2xl border border-surface-200 dark:border-surface-700 p-8">
                <div class="flex justify-center">
                    <ProgressSpinner style="width: 3rem; height: 3rem" strokeWidth="4" />
                </div>
            </div>

            <div v-else-if="!history.length" class="rounded-2xl border border-dashed border-surface-300 dark:border-surface-700 p-8 text-center">
                <i class="pi pi-chart-line text-3xl text-surface-400 mb-3"></i>
                <div class="text-xl font-semibold mb-2">Aun no hay historico disponible</div>
                <p class="text-surface-500 mb-0">Esta carta tendra grafico y tabla apenas existan capturas de precio guardadas para este item.</p>
            </div>

            <template v-else>
                <div class="rounded-2xl border border-surface-200 dark:border-surface-700 p-4">
                    <div v-if="filteredHistory.length" class="h-[24rem]">
                        <Chart type="line" :data="chartData" :options="chartOptions" class="h-full" />
                    </div>
                    <div v-else class="py-12 text-center text-surface-500">No hay datos en el rango seleccionado.</div>
                </div>

                <div class="rounded-2xl border border-surface-200 dark:border-surface-700 p-4">
                    <div class="flex items-center justify-between gap-3 mb-4">
                        <div>
                            <div class="text-xl font-semibold">Historial detallado</div>
                            <div class="text-sm text-surface-500">Registro cronologico de precios base y venta para esta carta.</div>
                        </div>
                        <Tag :value="`${historyRows.length} registros`" severity="info" />
                    </div>
                    <DataTable :value="historyRows" responsiveLayout="scroll" dataKey="captured_at" paginator :rows="8">
                        <Column header="Fecha" style="min-width: 12rem">
                            <template #body="{ data }">
                                {{ formatDateTime(data.captured_at) }}
                            </template>
                        </Column>
                        <Column header="Precio base" style="min-width: 10rem">
                            <template #body="{ data }">
                                {{ formatMoney(data.base_price, data.currency || currentCurrency) }}
                            </template>
                        </Column>
                        <Column header="Precio venta" style="min-width: 10rem">
                            <template #body="{ data }">
                                {{ formatMoney(data.sale_price, data.currency || currentCurrency) }}
                            </template>
                        </Column>
                        <Column header="Diferencia" style="min-width: 10rem">
                            <template #body="{ data }">
                                <span v-if="data.difference !== null">{{ formatMoney(data.difference, data.currency || currentCurrency) }}</span>
                                <span v-else class="text-surface-500">-</span>
                            </template>
                        </Column>
                        <Column header="%" style="min-width: 8rem">
                            <template #body="{ data }">
                                <Tag v-if="data.differencePercent !== null" :severity="variationSeverity(data.differencePercent)" :value="formatPercent(data.differencePercent)" />
                                <span v-else class="text-surface-500">-</span>
                            </template>
                        </Column>
                    </DataTable>
                </div>
            </template>
        </div>
    </Dialog>
</template>
