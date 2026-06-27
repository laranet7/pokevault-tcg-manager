<script setup lang="ts">
import { exportCollectionToExcel, exportCollectionToPdf, type CollectionExportFormat, type CollectionExportOptions } from '@/utils/collectionExport';
import type { Collection } from '@/types/collection';
import type { CollectionItem } from '@/types/collectionItem';
import { computed, reactive } from 'vue';
import { useToast } from 'primevue/usetoast';

const props = defineProps<{
    visible: boolean;
    collection: Collection | null;
    items: CollectionItem[];
}>();

const emit = defineEmits<{
    'update:visible': [value: boolean];
}>();

const toast = useToast();

const formatOptions = [
    { label: 'PDF', value: 'pdf' },
    { label: 'Excel', value: 'excel' }
] satisfies Array<{ label: string; value: CollectionExportFormat }>;

const pdfColumnOptions = [
    { label: '2 columnas', value: 2 },
    { label: '3 columnas', value: 3 }
];

const state = reactive<CollectionExportOptions & { exporting: boolean }>({
    format: 'pdf',
    pdfColumns: 3,
    includeBasePrice: false,
    includeSalePrice: false,
    exporting: false
});

const exporting = computed(() => state.exporting);
const hasItems = computed(() => props.items.length > 0);

function closeDialog(): void {
    emit('update:visible', false);
}

async function handleExport(): Promise<void> {
    if (!props.collection || !hasItems.value) {
        toast.add({ severity: 'warn', summary: 'Sin datos', detail: 'La coleccion no tiene cartas para exportar.', life: 3500 });
        return;
    }

    state.exporting = true;
    try {
        if (state.format === 'pdf') {
            await exportCollectionToPdf(props.collection, props.items, state);
        } else {
            await exportCollectionToExcel(props.collection, props.items, state);
        }

        toast.add({
            severity: 'success',
            summary: 'Exportacion lista',
            detail: `Se genero el archivo ${state.format.toUpperCase()} de la coleccion.`,
            life: 3500
        });
        closeDialog();
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible exportar la coleccion.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 5000 });
    } finally {
        state.exporting = false;
    }
}
</script>

<template>
    <Dialog :visible="props.visible" modal header="Exportar coleccion" :style="{ width: '34rem' }" @update:visible="emit('update:visible', $event)">
        <div class="flex flex-col gap-5">
            <div>
                <div class="text-lg font-semibold">{{ props.collection?.name || 'Coleccion' }}</div>
                <p class="text-surface-500 mb-0">
                    {{ hasItems ? `Se exportaran ${props.items.length} items.` : 'No hay cartas para exportar en esta coleccion.' }}
                </p>
            </div>

            <div class="grid grid-cols-12 gap-4">
                <div class="col-span-12">
                    <label class="block text-sm mb-2">Formato</label>
                    <SelectButton v-model="state.format" :options="formatOptions" optionLabel="label" optionValue="value" :allowEmpty="false" />
                </div>

                <div v-if="state.format === 'pdf'" class="col-span-12">
                    <label class="block text-sm mb-2">Distribucion PDF</label>
                    <Select v-model="state.pdfColumns" :options="pdfColumnOptions" optionLabel="label" optionValue="value" class="w-full" />
                </div>

                <div class="col-span-12">
                    <div class="flex items-center justify-between gap-4 min-h-14 px-4 rounded-xl border border-surface-200 dark:border-surface-700">
                        <div>
                            <div class="font-medium">Incluir precio TCG</div>
                            <div class="text-sm text-surface-500">Usa el precio base guardado en la coleccion.</div>
                        </div>
                        <ToggleSwitch v-model="state.includeBasePrice" />
                    </div>
                </div>

                <div class="col-span-12">
                    <div class="flex items-center justify-between gap-4 min-h-14 px-4 rounded-xl border border-surface-200 dark:border-surface-700">
                        <div>
                            <div class="font-medium">Incluir precio final de venta</div>
                            <div class="text-sm text-surface-500">Usa el precio de venta registrado para cada item.</div>
                        </div>
                        <ToggleSwitch v-model="state.includeSalePrice" />
                    </div>
                </div>

                <div class="col-span-12">
                    <Message severity="info" :closable="false">
                        <span v-if="state.format === 'pdf'">El PDF mostrara las cartas en grilla con imagen, nombre, rareza, estado y edicion.</span>
                        <span v-else>El Excel se exportara como tabla sin imagen, listo para ordenar o filtrar.</span>
                    </Message>
                </div>
            </div>
        </div>

        <template #footer>
            <div class="flex justify-end gap-3">
                <Button label="Cancelar" severity="secondary" outlined @click="closeDialog" />
                <Button label="Descargar" icon="pi pi-download" :disabled="!hasItems" :loading="exporting" @click="handleExport" />
            </div>
        </template>
    </Dialog>
</template>
