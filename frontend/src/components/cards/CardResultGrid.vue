<script setup lang="ts">
import type { CardSearchResult } from '@/types/card';
import CardResultItem from './CardResultItem.vue';

defineProps<{
    results: CardSearchResult[];
}>();

const emit = defineEmits<{
    add: [card: CardSearchResult];
}>();
</script>

<template>
    <div class="grid grid-cols-12 gap-6">
        <div v-for="card in results" :key="card.external_id" class="col-span-12 md:col-span-6 xl:col-span-4">
            <CardResultItem :card="card" @add="emit('add', $event)" />
        </div>
    </div>
</template>
