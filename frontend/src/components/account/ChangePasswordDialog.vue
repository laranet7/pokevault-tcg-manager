<script setup lang="ts">
import { changeCurrentPassword } from '@/stores/auth';
import { ref, watch } from 'vue';
import { useToast } from 'primevue/usetoast';

const props = defineProps<{
    visible: boolean;
}>();

const emit = defineEmits<{
    'update:visible': [value: boolean];
    changed: [];
}>();

const toast = useToast();

const currentPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const loading = ref(false);

function resetForm(): void {
    currentPassword.value = '';
    newPassword.value = '';
    confirmPassword.value = '';
    loading.value = false;
}

function closeDialog(): void {
    emit('update:visible', false);
}

watch(
    () => props.visible,
    (visible) => {
        if (!visible) {
            resetForm();
        }
    }
);

async function submit(): Promise<void> {
    if (!currentPassword.value || !newPassword.value || !confirmPassword.value) {
        toast.add({ severity: 'warn', summary: 'Datos incompletos', detail: 'Completa la clave actual, la nueva clave y su confirmacion.', life: 4000 });
        return;
    }

    if (newPassword.value !== confirmPassword.value) {
        toast.add({ severity: 'warn', summary: 'Revisa la clave', detail: 'La nueva clave y su confirmacion deben coincidir.', life: 4000 });
        return;
    }

    loading.value = true;
    try {
        await changeCurrentPassword({
            current_password: currentPassword.value,
            new_password: newPassword.value
        });
        toast.add({ severity: 'success', summary: 'Clave actualizada', detail: 'Tu clave fue actualizada correctamente.', life: 3000 });
        emit('changed');
        closeDialog();
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible cambiar la clave.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <Dialog :visible="props.visible" modal header="Cambiar clave" :style="{ width: '32rem' }" @update:visible="emit('update:visible', $event)">
        <div class="flex flex-col gap-5">
            <p class="text-surface-500 mb-0">Actualiza tu clave de acceso sin salir de la sesion actual.</p>

            <div>
                <label class="block text-sm mb-2">Clave actual</label>
                <Password v-model="currentPassword" :toggleMask="true" fluid :feedback="false" />
            </div>

            <div>
                <label class="block text-sm mb-2">Nueva clave</label>
                <Password v-model="newPassword" :toggleMask="true" fluid :feedback="false" />
            </div>

            <div>
                <label class="block text-sm mb-2">Confirmar nueva clave</label>
                <Password v-model="confirmPassword" :toggleMask="true" fluid :feedback="false" />
            </div>
        </div>

        <template #footer>
            <div class="flex justify-end gap-3">
                <Button label="Cancelar" severity="secondary" outlined @click="closeDialog" />
                <Button label="Guardar nueva clave" :loading="loading" @click="submit" />
            </div>
        </template>
    </Dialog>
</template>
