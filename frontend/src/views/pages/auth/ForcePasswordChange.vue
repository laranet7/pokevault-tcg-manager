<script setup lang="ts">
import FloatingConfigurator from '@/components/FloatingConfigurator.vue';
import { changeCurrentPassword, logout, useAuth } from '@/stores/auth';
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';

const router = useRouter();
const toast = useToast();
const { state } = useAuth();

const currentPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const loading = ref(false);

const username = computed(() => state.user?.username || '');

async function submit(): Promise<void> {
    if (!newPassword.value || newPassword.value !== confirmPassword.value) {
        toast.add({ severity: 'warn', summary: 'Revisa la clave', detail: 'La nueva clave y su confirmacion deben coincidir.', life: 4000 });
        return;
    }

    loading.value = true;
    try {
        await changeCurrentPassword({
            current_password: currentPassword.value,
            new_password: newPassword.value
        });
        toast.add({ severity: 'success', summary: 'Clave actualizada', detail: 'Ya puedes usar el sistema normalmente.', life: 3000 });
        await router.push('/');
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible cambiar la clave.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <FloatingConfigurator />
    <div class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen min-w-[100vw] overflow-hidden">
        <div class="flex flex-col items-center justify-center">
            <div style="border-radius: 56px; padding: 0.3rem; background: linear-gradient(180deg, var(--primary-color) 10%, rgba(14, 165, 233, 0) 32%)">
                <div class="w-full bg-surface-0 dark:bg-surface-900 py-16 px-8 sm:px-20" style="border-radius: 53px">
                    <div class="text-center mb-8">
                        <div class="text-surface-900 dark:text-surface-0 text-3xl font-medium mb-4">Cambio obligatorio de clave</div>
                        <span class="text-muted-color font-medium">El usuario {{ username }} debe actualizar su clave antes de continuar.</span>
                    </div>

                    <div class="flex flex-col gap-5">
                        <div>
                            <label class="block text-surface-900 dark:text-surface-0 font-medium text-xl mb-2">Clave actual</label>
                            <Password v-model="currentPassword" :toggleMask="true" fluid :feedback="false" />
                        </div>
                        <div>
                            <label class="block text-surface-900 dark:text-surface-0 font-medium text-xl mb-2">Nueva clave</label>
                            <Password v-model="newPassword" :toggleMask="true" fluid :feedback="false" />
                        </div>
                        <div>
                            <label class="block text-surface-900 dark:text-surface-0 font-medium text-xl mb-2">Confirmar nueva clave</label>
                            <Password v-model="confirmPassword" :toggleMask="true" fluid :feedback="false" />
                        </div>
                        <div class="flex gap-3">
                            <Button label="Cerrar sesion" severity="secondary" outlined class="flex-1" @click="logout(); router.push('/auth/login')" />
                            <Button label="Guardar nueva clave" class="flex-1" :loading="loading" @click="submit" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
