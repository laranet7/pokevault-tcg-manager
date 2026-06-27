<script setup lang="ts">
import { createCollectionItem, createCollectionItemWithImage } from '@/api/collectionItemsApi';
import { listCollections } from '@/api/collectionsApi';
import { useAuth } from '@/stores/auth';
import type { CardSearchResult } from '@/types/card';
import type { Collection } from '@/types/collection';
import type { CreateCollectionItemPayload, PatternVariant } from '@/types/collectionItem';
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';
import { useToast } from 'primevue/usetoast';

const DEFAULT_LANGUAGE = 'Ingles';
const DEFAULT_CONDITION = 'Near Mint';
const DEFAULT_FINISH = 'Normal';

type StoredAddPreferences = {
    collectionId: number | null;
    language: string;
    condition: string;
    finish: string;
    patternVariant: PatternVariant | null;
};

type PatternVariantField = PatternVariant | 'none';

const props = defineProps<{
    visible: boolean;
    card: CardSearchResult | null;
}>();

const emit = defineEmits<{
    'update:visible': [value: boolean];
    saved: [];
}>();

const toast = useToast();
const { state } = useAuth();
const loadingCollections = ref(false);
const saving = ref(false);
const collections = ref<Collection[]>([]);
const selectedCollectionId = ref<number | null>(null);
const imageFile = ref<File | null>(null);
const imagePreviewUrl = ref<string | null>(null);

const form = reactive({
    quantity: 1,
    language: DEFAULT_LANGUAGE,
    condition: DEFAULT_CONDITION,
    finish: DEFAULT_FINISH,
    pattern_variant: 'none' as PatternVariantField,
    is_for_sale: false,
    base_price: null as number | null,
    base_price_currency: 'USD',
    sale_margin_percent: 30,
    sale_status: 'not_available',
    notes: ''
});

const languageOptions = ['Espanol', 'Ingles', 'Japones', 'Otro'].map((value) => ({ label: value, value }));
const conditionOptions = ['Mint', 'Near Mint', 'Excellent', 'Good', 'Played', 'Damaged'].map((value) => ({ label: value, value }));
const finishOptions = ['Normal', 'Holo', 'Reverse Holo', 'Full Art', 'Illustration Rare', 'Special Illustration Rare', 'Promo'].map((value) => ({
    label: value,
    value
}));
const patternVariantOptions = [
    { label: 'Sin patron especial', value: 'none' },
    { label: 'Poke Ball Pattern', value: 'poke_ball' },
    { label: 'Master Ball Pattern', value: 'master_ball' }
];
const saleStatusOptions = [
    { label: 'No disponible', value: 'not_available' },
    { label: 'Disponible', value: 'available' },
    { label: 'Reservada', value: 'reserved' },
    { label: 'Vendida', value: 'sold' }
];

const collectionOptions = computed(() => collections.value.map((collection) => ({ label: collection.name, value: collection.id })));

type RawPriceEntry = {
    market?: number | string | null;
    mid?: number | string | null;
    low?: number | string | null;
};

type SuggestedCardSetup = {
    finish: string;
    basePrice: number | null;
    currency: string;
};

function getTcgplayerPrices(card: CardSearchResult | null): Record<string, RawPriceEntry> {
    const tcgplayerPrices = card?.raw_prices?.tcgplayer;
    if (!tcgplayerPrices || typeof tcgplayerPrices !== 'object' || Array.isArray(tcgplayerPrices)) {
        return {};
    }

    return tcgplayerPrices as Record<string, RawPriceEntry>;
}

function getCardmarketPrices(card: CardSearchResult | null): Record<string, number | string | null> {
    const cardmarketPrices = card?.raw_prices?.cardmarket;
    if (!cardmarketPrices || typeof cardmarketPrices !== 'object' || Array.isArray(cardmarketPrices)) {
        return {};
    }

    return cardmarketPrices as Record<string, number | string | null>;
}

function pickPriceFromEntry(entry: RawPriceEntry | undefined): number | null {
    if (!entry) {
        return null;
    }

    const amount = entry.market ?? entry.mid ?? entry.low;
    if (amount === null || amount === undefined || amount === '') {
        return null;
    }

    const normalized = Number(amount);
    return Number.isFinite(normalized) ? normalized : null;
}

function inferFinishFromCard(card: CardSearchResult | null, preferredFinish: string): string {
    const rarity = (card?.rarity || '').toLowerCase();
    const tcgplayerPrices = getTcgplayerPrices(card);
    const labels = Object.keys(tcgplayerPrices);
    const hasNormal = labels.includes('normal');
    const hasHolo = labels.includes('holofoil');
    const hasReverse = labels.includes('reverseHolofoil');

    if (rarity.includes('special illustration rare')) {
        return 'Special Illustration Rare';
    }
    if (rarity.includes('illustration rare')) {
        return 'Illustration Rare';
    }
    if (rarity.includes('promo')) {
        return 'Promo';
    }
    if (rarity.includes('full art')) {
        return 'Full Art';
    }
    if (rarity.includes('reverse holo')) {
        return 'Reverse Holo';
    }
    if (rarity.includes('holo')) {
        return 'Holo';
    }

    if (hasReverse && !hasNormal && !hasHolo) {
        return 'Reverse Holo';
    }
    if (hasHolo && !hasNormal && !hasReverse) {
        return 'Holo';
    }
    if (hasNormal && !hasHolo && !hasReverse) {
        return 'Normal';
    }

    return preferredFinish || DEFAULT_FINISH;
}

function resolveSuggestedCardSetup(card: CardSearchResult | null, preferredFinish: string): SuggestedCardSetup {
    const finish = inferFinishFromCard(card, preferredFinish);
    const tcgplayerPrices = getTcgplayerPrices(card);
    const cardmarketPrices = getCardmarketPrices(card);

    const finishCandidates: Record<string, string[]> = {
        Normal: ['normal'],
        Holo: ['holofoil'],
        'Reverse Holo': ['reverseHolofoil'],
        'Full Art': ['holofoil', 'normal'],
        'Illustration Rare': ['holofoil', 'normal'],
        'Special Illustration Rare': ['holofoil', 'normal'],
        Promo: ['holofoil', 'normal']
    };

    for (const label of finishCandidates[finish] || []) {
        const amount = pickPriceFromEntry(tcgplayerPrices[label]);
        if (amount !== null) {
            return {
                finish,
                basePrice: amount,
                currency: 'USD'
            };
        }
    }

    const fallbackPrice =
        cardmarketPrices.averageSellPrice ??
        cardmarketPrices.trendPrice ??
        (finish === 'Reverse Holo' ? cardmarketPrices.reverseHoloTrend ?? cardmarketPrices.reverseHoloSell : null);

    if (fallbackPrice !== null && fallbackPrice !== undefined && fallbackPrice !== '') {
        return {
            finish,
            basePrice: Number(fallbackPrice),
            currency: 'EUR'
        };
    }

    return {
        finish,
        basePrice: card?.prices[0] ? Number(card.prices[0].amount) : null,
        currency: card?.prices[0]?.currency ?? 'USD'
    };
}

function getPreferencesKey(): string {
    return `pokevault:add-card-preferences:${state.user?.id ?? 'guest'}`;
}

function resolveLegacyPatternVariant(value: Partial<StoredAddPreferences> & { isPokeball?: boolean }): PatternVariant | null {
    if (value.patternVariant) {
        return value.patternVariant;
    }
    return value.isPokeball ? 'poke_ball' : null;
}

function resolvePatternVariantFieldValue(value: PatternVariant | null | undefined): PatternVariantField {
    return value ?? 'none';
}

function serializePatternVariant(value: PatternVariantField): PatternVariant | null {
    return value === 'none' ? null : value;
}

function readPreferences(): StoredAddPreferences {
    if (typeof window === 'undefined') {
        return {
            collectionId: null,
            language: DEFAULT_LANGUAGE,
            condition: DEFAULT_CONDITION,
            finish: DEFAULT_FINISH,
            patternVariant: null
        };
    }

    const rawValue = window.localStorage.getItem(getPreferencesKey());
    if (!rawValue) {
        return {
            collectionId: null,
            language: DEFAULT_LANGUAGE,
            condition: DEFAULT_CONDITION,
            finish: DEFAULT_FINISH,
            patternVariant: null
        };
    }

    try {
        const parsed = JSON.parse(rawValue) as Partial<StoredAddPreferences> & { isPokeball?: boolean };
        const legacyPatternVariant = resolveLegacyPatternVariant(parsed);
        const { patternVariant: _patternVariant, isPokeball: _isPokeball, ...restParsed } = parsed;
        return {
            collectionId: null,
            language: DEFAULT_LANGUAGE,
            condition: DEFAULT_CONDITION,
            finish: DEFAULT_FINISH,
            ...restParsed,
            patternVariant: legacyPatternVariant
        };
    } catch {
        window.localStorage.removeItem(getPreferencesKey());
        return {
            collectionId: null,
            language: DEFAULT_LANGUAGE,
            condition: DEFAULT_CONDITION,
            finish: DEFAULT_FINISH,
            patternVariant: null
        };
    }
}

function persistPreferences(): void {
    if (typeof window === 'undefined') {
        return;
    }

    const payload: StoredAddPreferences = {
        collectionId: selectedCollectionId.value,
        language: form.language,
        condition: form.condition,
        finish: form.finish,
        patternVariant: serializePatternVariant(form.pattern_variant)
    };

    window.localStorage.setItem(getPreferencesKey(), JSON.stringify(payload));
}

function closeDialog(): void {
    emit('update:visible', false);
}

function revokeImagePreview(): void {
    if (!imagePreviewUrl.value) {
        return;
    }

    URL.revokeObjectURL(imagePreviewUrl.value);
    imagePreviewUrl.value = null;
}

function clearImage(): void {
    imageFile.value = null;
    revokeImagePreview();
}

function handleImageSelection(event: Event): void {
    const target = event.target as HTMLInputElement | null;
    const file = target?.files?.[0] ?? null;

    revokeImagePreview();
    imageFile.value = file;

    if (file) {
        imagePreviewUrl.value = URL.createObjectURL(file);
    }
}

function resetForm(): void {
    const preferences = readPreferences();
    const preferredCollectionExists = collections.value.some((collection) => collection.id === preferences.collectionId);
    const suggestedSetup = resolveSuggestedCardSetup(props.card, preferences.finish || DEFAULT_FINISH);

    selectedCollectionId.value = preferredCollectionExists ? preferences.collectionId : (collections.value[0]?.id ?? null);
    form.quantity = 1;
    form.language = preferences.language || DEFAULT_LANGUAGE;
    form.condition = preferences.condition || DEFAULT_CONDITION;
    form.finish = suggestedSetup.finish;
    form.pattern_variant = resolvePatternVariantFieldValue(preferences.patternVariant);
    form.is_for_sale = false;
    form.base_price = suggestedSetup.basePrice;
    form.base_price_currency = suggestedSetup.currency;
    form.sale_margin_percent = 30;
    form.sale_status = 'not_available';
    form.notes = '';
    clearImage();
}

async function loadCollections(): Promise<void> {
    loadingCollections.value = true;
    try {
        collections.value = await listCollections('edit');
        resetForm();
    } finally {
        loadingCollections.value = false;
    }
}

watch(
    () => props.visible,
    async (visible) => {
        if (visible) {
            await loadCollections();
        } else {
            clearImage();
        }
    }
);

watch(
    () => props.card?.external_id,
    () => {
        if (props.visible) {
            resetForm();
        }
    }
);

async function save(): Promise<void> {
    if (!props.card || !selectedCollectionId.value) {
        toast.add({ severity: 'warn', summary: 'Falta informacion', detail: 'Selecciona una coleccion antes de guardar.', life: 3000 });
        return;
    }

    const payload: CreateCollectionItemPayload = {
        quantity: form.quantity,
        language: form.language,
        condition: form.condition,
        finish: form.finish,
        pattern_variant: serializePatternVariant(form.pattern_variant),
        is_for_sale: form.is_for_sale,
        base_price: form.base_price,
        base_price_currency: form.base_price_currency,
        sale_margin_percent: form.sale_margin_percent,
        sale_status: form.sale_status,
        notes: form.notes || null,
        card: {
            external_id: props.card.external_id,
            name: props.card.name,
            number: props.card.number,
            set_id: props.card.set_id,
            set_name: props.card.set_name,
            printed_total: props.card.printed_total,
            supertype: props.card.supertype,
            pokedex_number: props.card.pokedex_number,
            rarity: props.card.rarity,
            image_small: props.card.image_small,
            image_large: props.card.image_large,
            api_source: props.card.api_source
        }
    };

    saving.value = true;
    try {
        if (imageFile.value) {
            await createCollectionItemWithImage(selectedCollectionId.value, {
                ...payload,
                image: imageFile.value
            });
        } else {
            await createCollectionItem(selectedCollectionId.value, payload);
        }
        persistPreferences();
        toast.add({ severity: 'success', summary: 'Guardado', detail: 'La carta fue agregada a la coleccion.', life: 3000 });
        emit('saved');
        closeDialog();
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible guardar la carta.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        saving.value = false;
    }
}

onBeforeUnmount(() => {
    revokeImagePreview();
});
</script>

<template>
    <Dialog :visible="props.visible" modal header="Agregar a coleccion" :style="{ width: '42rem' }" @update:visible="emit('update:visible', $event)">
        <div v-if="props.card" class="flex flex-col gap-5">
            <div class="flex items-center gap-4 p-4 rounded-xl bg-surface-50 dark:bg-surface-900">
                <img
                    v-if="imagePreviewUrl || props.card.image_small"
                    :src="imagePreviewUrl || props.card.image_small || undefined"
                    :alt="props.card.name"
                    class="h-24 rounded-md object-contain"
                />
                <div v-else class="h-24 w-20 rounded-md border border-dashed border-surface-300 dark:border-surface-600 flex items-center justify-center text-xs text-surface-500">
                    Sin imagen
                </div>
                <div>
                    <div class="flex items-center gap-2 flex-wrap">
                        <div class="text-lg font-semibold">{{ props.card.name }}</div>
                        <Tag
                            :value="props.card.api_source === 'tcgdex' ? 'TCGDex' : 'Pokemon TCG API'"
                            :severity="props.card.api_source === 'tcgdex' ? 'warn' : 'info'"
                        />
                    </div>
                    <div class="text-surface-500">
                        {{ props.card.number }}
                        <span v-if="props.card.printed_total">/ {{ props.card.printed_total }}</span>
                        - {{ props.card.set_name }}
                    </div>
                    <div v-if="props.card.pokedex_number" class="text-sm text-surface-500 mt-1">Pokedex #{{ props.card.pokedex_number }}</div>
                </div>
            </div>

            <div v-if="loadingCollections" class="flex justify-center py-6">
                <ProgressSpinner style="width: 3rem; height: 3rem" strokeWidth="6" />
            </div>

            <Message v-else-if="!collections.length" severity="warn">No hay colecciones disponibles. Crea una desde la vista de colecciones.</Message>

            <div v-else class="grid grid-cols-12 gap-4">
                <div class="col-span-12 md:col-span-6">
                    <label class="block text-sm mb-2">Coleccion</label>
                    <Select v-model="selectedCollectionId" :options="collectionOptions" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <div class="col-span-12 md:col-span-6">
                    <label class="block text-sm mb-2">Idioma</label>
                    <Select v-model="form.language" :options="languageOptions" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <div class="col-span-12 md:col-span-6">
                    <label class="block text-sm mb-2">Estado fisico</label>
                    <Select v-model="form.condition" :options="conditionOptions" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <div class="col-span-12 md:col-span-6">
                    <label class="block text-sm mb-2">Acabado</label>
                    <Select v-model="form.finish" :options="finishOptions" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <div class="col-span-12 md:col-span-6">
                    <label class="block text-sm mb-2">Patron especial</label>
                    <Select v-model="form.pattern_variant" :options="patternVariantOptions" optionLabel="label" optionValue="value" class="w-full" />
                    <small class="text-surface-500 mt-2 block">Usalo para variantes como Poke Ball Pattern o Master Ball Pattern.</small>
                </div>
                <div class="col-span-12 md:col-span-4">
                    <label class="block text-sm mb-2">Cantidad</label>
                    <InputNumber v-model="form.quantity" :min="1" class="w-full" inputClass="w-full" />
                </div>
                <div class="col-span-12 md:col-span-4">
                    <label class="block text-sm mb-2">Precio base</label>
                    <InputNumber v-model="form.base_price" mode="currency" :currency="form.base_price_currency" locale="en-US" class="w-full" inputClass="w-full" />
                </div>
                <div class="col-span-12 md:col-span-4">
                    <label class="block text-sm mb-2">Margen de venta</label>
                    <InputNumber v-model="form.sale_margin_percent" suffix="%" :min="0" class="w-full" inputClass="w-full" />
                </div>
                <div class="col-span-12 md:col-span-6">
                    <label class="block text-sm mb-2">Estado de venta</label>
                    <Select v-model="form.sale_status" :options="saleStatusOptions" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <div class="col-span-12 md:col-span-6">
                    <label class="block text-sm mb-2">Disponible para venta</label>
                    <div class="flex items-center gap-3 min-h-12 px-3 rounded-xl border border-surface-200 dark:border-surface-700">
                        <ToggleSwitch v-model="form.is_for_sale" />
                        <span>{{ form.is_for_sale ? 'Si' : 'No' }}</span>
                    </div>
                </div>
                <div class="col-span-12">
                    <label class="block text-sm mb-2">Imagen de respaldo</label>
                    <div class="rounded-xl border border-surface-200 dark:border-surface-700 p-4 flex flex-col gap-3">
                        <div class="text-sm text-surface-500">
                            {{ props.card.image_small ? 'Puedes reemplazar la imagen si esta variante necesita una mejor copia.' : 'Esta carta no trae imagen. Puedes cargarla aqui antes de agregarla.' }}
                        </div>
                        <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="handleImageSelection" />
                        <div v-if="imageFile" class="flex items-center justify-between gap-3">
                            <span class="text-sm">{{ imageFile.name }}</span>
                            <Button label="Quitar imagen" icon="pi pi-times" severity="secondary" outlined size="small" @click="clearImage" />
                        </div>
                    </div>
                </div>
                <div class="col-span-12">
                    <label class="block text-sm mb-2">Notas</label>
                    <Textarea v-model="form.notes" rows="3" class="w-full" />
                </div>
            </div>
        </div>

        <template #footer>
            <div class="flex justify-end gap-3">
                <Button label="Cancelar" severity="secondary" outlined @click="closeDialog" />
                <Button label="Guardar" icon="pi pi-save" :loading="saving" @click="save" />
            </div>
        </template>
    </Dialog>
</template>
