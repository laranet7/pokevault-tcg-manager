<script setup lang="ts">
import { createManualCollectionItem } from '@/api/collectionItemsApi';
import { listCollections } from '@/api/collectionsApi';
import { useAuth } from '@/stores/auth';
import type { Collection } from '@/types/collection';
import type { CreateManualCollectionItemPayload } from '@/types/collectionItem';
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
    isPokeball: boolean;
};

type PrefilledManualCard = {
    name: string;
    setId: string;
    number: string;
    printedTotal: number | null;
};

const props = defineProps<{
    visible: boolean;
    initialQuery?: string;
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

const cardForm = reactive({
    name: '',
    set_id: '',
    set_name: '',
    number: '',
    printed_total: null as number | null,
    supertype: 'Pokemon',
    pokedex_number: null as number | null,
    rarity: ''
});

const itemForm = reactive({
    quantity: 1,
    language: DEFAULT_LANGUAGE,
    condition: DEFAULT_CONDITION,
    finish: DEFAULT_FINISH,
    is_pokeball: false,
    is_for_sale: false,
    base_price: null as number | null,
    base_price_currency: 'USD',
    sale_margin_percent: 30,
    sale_price: null as number | null,
    sale_status: 'not_available',
    notes: ''
});

const collectionOptions = computed(() => collections.value.map((collection) => ({ label: collection.name, value: collection.id })));
const languageOptions = ['Espanol', 'Ingles', 'Japones', 'Otro'].map((value) => ({ label: value, value }));
const conditionOptions = ['Mint', 'Near Mint', 'Excellent', 'Good', 'Played', 'Damaged'].map((value) => ({ label: value, value }));
const finishOptions = ['Normal', 'Holo', 'Reverse Holo', 'Full Art', 'Illustration Rare', 'Special Illustration Rare', 'Promo'].map((value) => ({
    label: value,
    value
}));
const saleStatusOptions = [
    { label: 'No disponible', value: 'not_available' },
    { label: 'Disponible', value: 'available' },
    { label: 'Reservada', value: 'reserved' },
    { label: 'Vendida', value: 'sold' }
];
const supertypeOptions = ['Pokemon', 'Trainer', 'Energy', 'Otro'].map((value) => ({ label: value, value }));

function getPreferencesKey(): string {
    return `pokevault:add-card-preferences:${state.user?.id ?? 'guest'}`;
}

function readPreferences(): StoredAddPreferences {
    if (typeof window === 'undefined') {
        return {
            collectionId: null,
            language: DEFAULT_LANGUAGE,
            condition: DEFAULT_CONDITION,
            finish: DEFAULT_FINISH,
            isPokeball: false
        };
    }

    const rawValue = window.localStorage.getItem(getPreferencesKey());
    if (!rawValue) {
        return {
            collectionId: null,
            language: DEFAULT_LANGUAGE,
            condition: DEFAULT_CONDITION,
            finish: DEFAULT_FINISH,
            isPokeball: false
        };
    }

    try {
        return {
            collectionId: null,
            language: DEFAULT_LANGUAGE,
            condition: DEFAULT_CONDITION,
            finish: DEFAULT_FINISH,
            isPokeball: false,
            ...(JSON.parse(rawValue) as Partial<StoredAddPreferences>)
        };
    } catch {
        window.localStorage.removeItem(getPreferencesKey());
        return {
            collectionId: null,
            language: DEFAULT_LANGUAGE,
            condition: DEFAULT_CONDITION,
            finish: DEFAULT_FINISH,
            isPokeball: false
        };
    }
}

function persistPreferences(): void {
    if (typeof window === 'undefined') {
        return;
    }

    const payload: StoredAddPreferences = {
        collectionId: selectedCollectionId.value,
        language: itemForm.language,
        condition: itemForm.condition,
        finish: itemForm.finish,
        isPokeball: itemForm.is_pokeball
    };

    window.localStorage.setItem(getPreferencesKey(), JSON.stringify(payload));
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

function parseInitialQuery(query: string): PrefilledManualCard {
    const normalizedQuery = query.trim();
    if (!normalizedQuery) {
        return { name: '', setId: '', number: '', printedTotal: null };
    }

    const fullReferenceMatch = normalizedQuery.match(/^(.*?)[\s-]+([A-Za-z]{2,6})[\s/:-]+(\d{1,3})$/);
    if (fullReferenceMatch) {
        return {
            name: fullReferenceMatch[1].trim(),
            setId: fullReferenceMatch[2].toUpperCase(),
            number: fullReferenceMatch[3].padStart(3, '0'),
            printedTotal: null
        };
    }

    const setCodeMatch = normalizedQuery.match(/^([A-Za-z]{2,6})[\s/:-]+(\d{1,3})$/);
    if (setCodeMatch) {
        return {
            name: '',
            setId: setCodeMatch[1].toUpperCase(),
            number: setCodeMatch[2].padStart(3, '0'),
            printedTotal: null
        };
    }

    const numberMatch = normalizedQuery.match(/^(\d{1,3})\/(\d{1,3})$/);
    if (numberMatch) {
        return {
            name: '',
            setId: '',
            number: numberMatch[1].padStart(3, '0'),
            printedTotal: Number(numberMatch[2])
        };
    }

    return { name: normalizedQuery, setId: '', number: '', printedTotal: null };
}

function resetForm(): void {
    const preferences = readPreferences();
    const preferredCollectionExists = collections.value.some((collection) => collection.id === preferences.collectionId);
    const prefilledCard = parseInitialQuery(props.initialQuery || '');

    selectedCollectionId.value = preferredCollectionExists ? preferences.collectionId : (collections.value[0]?.id ?? null);

    cardForm.name = prefilledCard.name;
    cardForm.set_id = prefilledCard.setId;
    cardForm.set_name = '';
    cardForm.number = prefilledCard.number;
    cardForm.printed_total = prefilledCard.printedTotal;
    cardForm.supertype = 'Pokemon';
    cardForm.pokedex_number = null;
    cardForm.rarity = '';

    itemForm.quantity = 1;
    itemForm.language = preferences.language || DEFAULT_LANGUAGE;
    itemForm.condition = preferences.condition || DEFAULT_CONDITION;
    itemForm.finish = preferences.finish || DEFAULT_FINISH;
    itemForm.is_pokeball = itemForm.finish === 'Reverse Holo' ? Boolean(preferences.isPokeball) : false;
    itemForm.is_for_sale = false;
    itemForm.base_price = null;
    itemForm.base_price_currency = 'USD';
    itemForm.sale_margin_percent = 30;
    itemForm.sale_price = null;
    itemForm.sale_status = 'not_available';
    itemForm.notes = '';

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

function closeDialog(): void {
    emit('update:visible', false);
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

function normalizeNullableText(value: string): string | null {
    const normalized = value.trim();
    return normalized ? normalized : null;
}

async function save(): Promise<void> {
    if (!selectedCollectionId.value) {
        toast.add({ severity: 'warn', summary: 'Falta informacion', detail: 'Selecciona una coleccion antes de guardar.', life: 3000 });
        return;
    }

    if (!cardForm.name.trim()) {
        toast.add({ severity: 'warn', summary: 'Nombre requerido', detail: 'Ingresa el nombre de la carta manual.', life: 3000 });
        return;
    }

    if (!cardForm.number.trim()) {
        toast.add({ severity: 'warn', summary: 'Numero requerido', detail: 'Ingresa el numero de carta, por ejemplo 027.', life: 3000 });
        return;
    }

    const payload: CreateManualCollectionItemPayload = {
        quantity: itemForm.quantity,
        language: itemForm.language,
        condition: itemForm.condition,
        finish: itemForm.finish,
        is_pokeball: itemForm.is_pokeball,
        is_for_sale: itemForm.is_for_sale,
        base_price: itemForm.base_price,
        base_price_currency: itemForm.base_price_currency,
        sale_margin_percent: itemForm.sale_margin_percent,
        sale_price: itemForm.sale_price,
        sale_status: itemForm.sale_status,
        notes: normalizeNullableText(itemForm.notes),
        image: imageFile.value,
        card: {
            name: cardForm.name.trim(),
            number: cardForm.number.trim(),
            set_id: normalizeNullableText(cardForm.set_id),
            set_name: normalizeNullableText(cardForm.set_name),
            printed_total: cardForm.printed_total,
            supertype: normalizeNullableText(cardForm.supertype),
            pokedex_number: cardForm.pokedex_number,
            rarity: normalizeNullableText(cardForm.rarity)
        }
    };

    saving.value = true;
    try {
        await createManualCollectionItem(selectedCollectionId.value, payload);
        persistPreferences();
        toast.add({ severity: 'success', summary: 'Carta creada', detail: 'La carta manual fue agregada a la coleccion.', life: 3000 });
        emit('saved');
        closeDialog();
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible guardar la carta manual.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4500 });
    } finally {
        saving.value = false;
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
    () => itemForm.finish,
    (finish) => {
        if (finish !== 'Reverse Holo') {
            itemForm.is_pokeball = false;
        }
    }
);

onBeforeUnmount(() => {
    revokeImagePreview();
});
</script>

<template>
    <Dialog :visible="props.visible" modal header="Crear carta manual" :style="{ width: '56rem' }" @update:visible="emit('update:visible', $event)">
        <div class="flex flex-col gap-5">
            <Message severity="info" :closable="false">
                Usa este formulario para cartas que no aparecen en Pokemon TCG API. Puedes subir tu propia imagen y quedara guardada en el almacenamiento local de PokeVault TCG.
            </Message>

            <div v-if="loadingCollections" class="flex justify-center py-6">
                <ProgressSpinner style="width: 3rem; height: 3rem" strokeWidth="6" />
            </div>

            <Message v-else-if="!collections.length" severity="warn">No hay colecciones disponibles. Crea una desde la vista de colecciones.</Message>

            <div v-else class="grid grid-cols-12 gap-6">
                <div class="col-span-12 xl:col-span-7">
                    <div class="flex flex-col gap-4">
                        <div>
                            <div class="text-lg font-semibold mb-3">Datos de la carta</div>
                            <div class="grid grid-cols-12 gap-4">
                                <div class="col-span-12">
                                    <label class="block text-sm mb-2">Nombre</label>
                                    <InputText v-model="cardForm.name" class="w-full" placeholder="Haunter" />
                                </div>
                                <div class="col-span-12 md:col-span-4">
                                    <label class="block text-sm mb-2">Codigo set</label>
                                    <InputText v-model="cardForm.set_id" class="w-full" placeholder="MEP" />
                                </div>
                                <div class="col-span-12 md:col-span-4">
                                    <label class="block text-sm mb-2">Numero</label>
                                    <InputText v-model="cardForm.number" class="w-full" placeholder="027" />
                                </div>
                                <div class="col-span-12 md:col-span-4">
                                    <label class="block text-sm mb-2">Total impreso</label>
                                    <InputNumber v-model="cardForm.printed_total" :min="1" class="w-full" inputClass="w-full" />
                                </div>
                                <div class="col-span-12 md:col-span-6">
                                    <label class="block text-sm mb-2">Nombre de edicion</label>
                                    <InputText v-model="cardForm.set_name" class="w-full" placeholder="Black Bolt" />
                                </div>
                                <div class="col-span-12 md:col-span-3">
                                    <label class="block text-sm mb-2">Supertipo</label>
                                    <Select v-model="cardForm.supertype" :options="supertypeOptions" optionLabel="label" optionValue="value" class="w-full" />
                                </div>
                                <div class="col-span-12 md:col-span-3">
                                    <label class="block text-sm mb-2">Numero Pokedex</label>
                                    <InputNumber v-model="cardForm.pokedex_number" :min="1" class="w-full" inputClass="w-full" />
                                </div>
                                <div class="col-span-12">
                                    <label class="block text-sm mb-2">Rareza</label>
                                    <InputText v-model="cardForm.rarity" class="w-full" placeholder="Illustration Rare" />
                                </div>
                            </div>
                            <small class="text-surface-500 mt-3 block">Para referencias como `MEP 027`, usa `MEP` en codigo set y `027` en numero.</small>
                        </div>

                        <div>
                            <div class="text-lg font-semibold mb-3">Datos de coleccion</div>
                            <div class="grid grid-cols-12 gap-4">
                                <div class="col-span-12 md:col-span-6">
                                    <label class="block text-sm mb-2">Coleccion</label>
                                    <Select v-model="selectedCollectionId" :options="collectionOptions" optionLabel="label" optionValue="value" class="w-full" />
                                </div>
                                <div class="col-span-12 md:col-span-6">
                                    <label class="block text-sm mb-2">Idioma</label>
                                    <Select v-model="itemForm.language" :options="languageOptions" optionLabel="label" optionValue="value" class="w-full" />
                                </div>
                                <div class="col-span-12 md:col-span-6">
                                    <label class="block text-sm mb-2">Estado fisico</label>
                                    <Select v-model="itemForm.condition" :options="conditionOptions" optionLabel="label" optionValue="value" class="w-full" />
                                </div>
                                <div class="col-span-12 md:col-span-6">
                                    <label class="block text-sm mb-2">Acabado</label>
                                    <Select v-model="itemForm.finish" :options="finishOptions" optionLabel="label" optionValue="value" class="w-full" />
                                </div>
                                <div class="col-span-12 md:col-span-6">
                                    <label class="block text-sm mb-2">Variante Pokeball</label>
                                    <div class="flex items-center gap-3 min-h-12 px-3 rounded-xl border border-surface-200 dark:border-surface-700">
                                        <ToggleSwitch v-model="itemForm.is_pokeball" :disabled="itemForm.finish !== 'Reverse Holo'" />
                                        <span>{{ itemForm.finish === 'Reverse Holo' ? (itemForm.is_pokeball ? 'Activada' : 'Desactivada') : 'Disponible solo para Reverse Holo' }}</span>
                                    </div>
                                </div>
                                <div class="col-span-12 md:col-span-3">
                                    <label class="block text-sm mb-2">Cantidad</label>
                                    <InputNumber v-model="itemForm.quantity" :min="1" class="w-full" inputClass="w-full" />
                                </div>
                                <div class="col-span-12 md:col-span-3">
                                    <label class="block text-sm mb-2">Precio base</label>
                                    <InputNumber v-model="itemForm.base_price" mode="currency" :currency="itemForm.base_price_currency" locale="en-US" class="w-full" inputClass="w-full" />
                                </div>
                                <div class="col-span-12 md:col-span-4">
                                    <label class="block text-sm mb-2">Margen de venta</label>
                                    <InputNumber v-model="itemForm.sale_margin_percent" suffix="%" :min="0" class="w-full" inputClass="w-full" />
                                </div>
                                <div class="col-span-12 md:col-span-4">
                                    <label class="block text-sm mb-2">Precio venta</label>
                                    <InputNumber v-model="itemForm.sale_price" mode="currency" :currency="itemForm.base_price_currency" locale="en-US" class="w-full" inputClass="w-full" />
                                </div>
                                <div class="col-span-12 md:col-span-4">
                                    <label class="block text-sm mb-2">Estado de venta</label>
                                    <Select v-model="itemForm.sale_status" :options="saleStatusOptions" optionLabel="label" optionValue="value" class="w-full" />
                                </div>
                                <div class="col-span-12">
                                    <div class="flex items-center gap-3 min-h-12 px-3 rounded-xl border border-surface-200 dark:border-surface-700">
                                        <ToggleSwitch v-model="itemForm.is_for_sale" />
                                        <span>{{ itemForm.is_for_sale ? 'Disponible para venta' : 'No disponible para venta' }}</span>
                                    </div>
                                </div>
                                <div class="col-span-12">
                                    <label class="block text-sm mb-2">Notas</label>
                                    <Textarea v-model="itemForm.notes" rows="3" class="w-full" />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-span-12 xl:col-span-5">
                    <div class="rounded-2xl border border-surface-200 dark:border-surface-700 p-4 h-full">
                        <div class="text-lg font-semibold mb-3">Imagen</div>
                        <div class="rounded-2xl bg-surface-50 dark:bg-surface-900 min-h-72 flex items-center justify-center p-4 mb-4">
                            <img v-if="imagePreviewUrl" :src="imagePreviewUrl" alt="Vista previa" class="max-h-72 max-w-full object-contain rounded-xl shadow" />
                            <div v-else class="text-surface-500 text-center">
                                <i class="pi pi-image text-3xl mb-3 block"></i>
                                <div>Sin imagen cargada</div>
                            </div>
                        </div>
                        <div class="flex flex-col gap-3">
                            <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="handleImageSelection" />
                            <small class="text-surface-500">La imagen es opcional, pero si la subes quedara guardada localmente para vistas previas y exportaciones.</small>
                            <Button v-if="imageFile" label="Quitar imagen" icon="pi pi-times" severity="secondary" outlined @click="clearImage" />
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <template #footer>
            <div class="flex justify-end gap-3">
                <Button label="Cancelar" severity="secondary" outlined @click="closeDialog" />
                <Button label="Guardar carta manual" icon="pi pi-save" :loading="saving" :disabled="loadingCollections || !collections.length" @click="save" />
            </div>
        </template>
    </Dialog>
</template>
