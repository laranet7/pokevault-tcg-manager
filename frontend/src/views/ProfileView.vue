<script setup lang="ts">
import { getTermsStatus } from '@/api/termsApi';
import { updateMe } from '@/api/usersApi';
import { replaceCurrentUser, useAuth } from '@/stores/auth';
import type { TermsStatus } from '@/types/terms';
import { computed, onMounted, reactive, ref } from 'vue';
import { useToast } from 'primevue/usetoast';

const toast = useToast();
const { state } = useAuth();

const profileForm = reactive({
    username: state.user?.username || '',
    full_name: state.user?.full_name || '',
    email: state.user?.email || ''
});

const savingProfile = ref(false);
const loadingTerms = ref(true);
const termsStatus = ref<TermsStatus | null>(null);

const formattedAcceptedAt = computed(() => {
    if (!termsStatus.value?.accepted_at) {
        return 'Pendiente';
    }

    return new Intl.DateTimeFormat('es-CL', {
        dateStyle: 'short',
        timeStyle: 'short'
    }).format(new Date(termsStatus.value.accepted_at));
});

async function loadTermsStatus(): Promise<void> {
    loadingTerms.value = true;
    try {
        termsStatus.value = await getTermsStatus();
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible cargar el estado de terminos.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        loadingTerms.value = false;
    }
}

async function saveProfile(): Promise<void> {
    savingProfile.value = true;
    try {
        const user = await updateMe({
            username: profileForm.username,
            full_name: profileForm.full_name || null,
            email: profileForm.email || null
        });
        replaceCurrentUser(user);
        profileForm.username = user.username;
        profileForm.full_name = user.full_name || '';
        profileForm.email = user.email || '';
        toast.add({ severity: 'success', summary: 'Perfil actualizado', detail: 'Tus datos fueron guardados.', life: 3000 });
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible actualizar el perfil.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        savingProfile.value = false;
    }
}

onMounted(async () => {
    await loadTermsStatus();
});
</script>

<template>
    <div class="grid grid-cols-12 gap-8">
        <div class="col-span-12 xl:col-span-7">
            <div class="card">
                <div class="text-2xl font-semibold mb-3">Mi perfil</div>
                <p class="text-surface-500 mb-5">Actualiza tus datos base desde este panel.</p>

                <div class="grid grid-cols-12 gap-4">
                    <div class="col-span-12">
                        <label class="block text-sm mb-2">Usuario</label>
                        <InputText v-model="profileForm.username" class="w-full" />
                    </div>
                    <div class="col-span-12">
                        <label class="block text-sm mb-2">Nombre completo</label>
                        <InputText v-model="profileForm.full_name" class="w-full" />
                    </div>
                    <div class="col-span-12">
                        <label class="block text-sm mb-2">Email</label>
                        <InputText v-model="profileForm.email" class="w-full" />
                    </div>
                </div>

                <div class="mt-5">
                    <Button label="Guardar perfil" icon="pi pi-save" :loading="savingProfile" @click="saveProfile" />
                </div>

                <Divider class="my-6" />

                <div class="flex flex-col gap-3">
                    <div>
                        <div class="text-xl font-semibold mb-1">Terminos aceptados</div>
                        <p class="text-surface-500 mb-0">Consulta la aceptacion vigente registrada para tu cuenta.</p>
                    </div>

                    <div v-if="loadingTerms" class="text-surface-500">Cargando estado de terminos...</div>

                    <div v-else class="grid grid-cols-12 gap-4">
                        <div class="col-span-12 md:col-span-4">
                            <div class="text-sm text-surface-500 mb-1">Version aceptada</div>
                            <div class="font-medium">{{ termsStatus?.accepted_version || 'Pendiente' }}</div>
                        </div>
                        <div class="col-span-12 md:col-span-4">
                            <div class="text-sm text-surface-500 mb-1">Fecha de aceptacion</div>
                            <div class="font-medium">{{ formattedAcceptedAt }}</div>
                        </div>
                        <div class="col-span-12 md:col-span-4">
                            <div class="text-sm text-surface-500 mb-1">Version vigente</div>
                            <div class="font-medium">{{ termsStatus?.current_version || 'No disponible' }}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
