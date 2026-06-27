<script setup lang="ts">
import type { Collection } from '@/types/collection';

const props = defineProps<{
    collection: Collection;
}>();

const emit = defineEmits<{
    open: [collectionId: number];
}>();
</script>

<template>
    <Card class="h-full">
        <template #title>
            <div class="flex items-center justify-between gap-3">
                <span>{{ props.collection.name }}</span>
                <Tag :value="props.collection.type || 'personal'" severity="contrast" />
            </div>
        </template>
        <template #content>
            <div class="flex flex-col gap-4 h-full">
                <p class="text-surface-600 dark:text-surface-300 min-h-16">
                    {{ props.collection.description || 'Coleccion personal para organizar cartas y variantes fisicas.' }}
                </p>

                <div class="grid grid-cols-2 gap-3">
                    <div class="rounded-xl bg-surface-100 dark:bg-surface-800 p-3">
                        <div class="text-surface-500 text-sm">Items</div>
                        <div class="text-2xl font-semibold">{{ props.collection.items_count }}</div>
                    </div>
                    <div class="rounded-xl bg-surface-100 dark:bg-surface-800 p-3">
                        <div class="text-surface-500 text-sm">Cartas</div>
                        <div class="text-2xl font-semibold">{{ props.collection.total_quantity }}</div>
                    </div>
                </div>

                <Button label="Abrir detalle" icon="pi pi-arrow-right" class="mt-auto" outlined @click="emit('open', props.collection.id)" />
            </div>
        </template>
    </Card>
</template>
