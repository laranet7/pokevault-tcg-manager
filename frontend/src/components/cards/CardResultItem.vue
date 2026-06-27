<script setup lang="ts">
import type { CardSearchResult } from '@/types/card';

const props = defineProps<{
    card: CardSearchResult;
}>();

const emit = defineEmits<{
    add: [card: CardSearchResult];
}>();

function formatMoney(amount: number | string, currency: string): string {
    const numericAmount = Number(amount);
    return new Intl.NumberFormat('es-CL', {
        style: 'currency',
        currency,
        maximumFractionDigits: 2
    }).format(numericAmount);
}
</script>

<template>
    <Card class="h-full">
        <template #content>
            <div class="flex flex-col gap-4 h-full">
                <div class="bg-surface-100 dark:bg-surface-800 rounded-xl p-4 flex justify-center min-h-60">
                    <img
                        v-if="props.card.image_small"
                        :src="props.card.image_small"
                        :alt="props.card.name"
                        class="max-h-52 object-contain rounded-md"
                    />
                    <div v-else class="flex items-center justify-center text-surface-500">Sin imagen</div>
                </div>

                <div class="flex flex-col gap-2">
                    <div class="flex items-start justify-between gap-3">
                        <div>
                            <div class="text-xl font-semibold">{{ props.card.name }}</div>
                            <div class="text-surface-500">
                                {{ props.card.number }}
                                <span v-if="props.card.printed_total">/ {{ props.card.printed_total }}</span>
                                · {{ props.card.set_name || 'Set desconocido' }}
                            </div>
                            <div class="mt-2">
                                <Tag
                                    :value="props.card.api_source === 'tcgdex' ? 'TCGDex' : 'Pokemon TCG API'"
                                    :severity="props.card.api_source === 'tcgdex' ? 'warn' : 'info'"
                                />
                            </div>
                        </div>
                        <Tag v-if="props.card.rarity" :value="props.card.rarity" severity="contrast" />
                    </div>

                    <div v-if="props.card.prices.length" class="flex flex-wrap gap-2">
                        <Tag
                            v-for="price in props.card.prices.slice(0, 2)"
                            :key="`${price.source}-${price.label}`"
                            severity="success"
                            :value="`${price.source}: ${formatMoney(price.amount, price.currency)}`"
                        />
                    </div>
                    <div v-else class="text-surface-500 text-sm">Sin precio de referencia disponible.</div>
                </div>

                <div class="mt-auto">
                    <Button label="Agregar a coleccion" icon="pi pi-plus" class="w-full" @click="emit('add', props.card)" />
                </div>
            </div>
        </template>
    </Card>
</template>
