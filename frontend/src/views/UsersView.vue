<script setup lang="ts">
import { createUser, listUsers, updateUser } from '@/api/usersApi';
import { replaceCurrentUser, useAuth } from '@/stores/auth';
import type { CreateUserPayload, User } from '@/types/user';
import { computed, onMounted, reactive, ref } from 'vue';
import { useToast } from 'primevue/usetoast';

const toast = useToast();
const { state } = useAuth();

const loadingUsers = ref(false);
const savingUser = ref(false);
const users = ref<User[]>([]);
const userDialogVisible = ref(false);
const editingUserId = ref<number | null>(null);

const userForm = reactive({
    username: '',
    full_name: '',
    email: '',
    password: '',
    is_admin: false,
    is_active: true,
    must_change_password: true
});

const dialogTitle = computed(() => (editingUserId.value ? 'Editar usuario' : 'Nuevo usuario'));
const currentUserId = computed(() => state.user?.id ?? null);

async function loadUsers(): Promise<void> {
    loadingUsers.value = true;
    try {
        users.value = await listUsers();
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible cargar los usuarios.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        loadingUsers.value = false;
    }
}

function resetUserForm(): void {
    editingUserId.value = null;
    userForm.username = '';
    userForm.full_name = '';
    userForm.email = '';
    userForm.password = '';
    userForm.is_admin = false;
    userForm.is_active = true;
    userForm.must_change_password = true;
}

function openCreateUser(): void {
    resetUserForm();
    userDialogVisible.value = true;
}

function openEditUser(user: User): void {
    editingUserId.value = user.id;
    userForm.username = user.username;
    userForm.full_name = user.full_name || '';
    userForm.email = user.email || '';
    userForm.password = '';
    userForm.is_admin = user.is_admin;
    userForm.is_active = user.is_active;
    userForm.must_change_password = user.must_change_password;
    userDialogVisible.value = true;
}

async function saveUser(): Promise<void> {
    savingUser.value = true;
    try {
        if (editingUserId.value) {
            const updated = await updateUser(editingUserId.value, {
                username: userForm.username,
                full_name: userForm.full_name || null,
                email: userForm.email || null,
                password: userForm.password || null,
                is_admin: userForm.is_admin,
                is_active: userForm.is_active,
                must_change_password: userForm.must_change_password
            });

            users.value = users.value.map((user) => (user.id === updated.id ? updated : user));
            if (updated.id === currentUserId.value) {
                replaceCurrentUser(updated);
            }
        } else {
            const payload: CreateUserPayload = {
                username: userForm.username,
                full_name: userForm.full_name || null,
                email: userForm.email || null,
                password: userForm.password,
                is_admin: userForm.is_admin,
                is_active: userForm.is_active
            };
            const created = await createUser(payload);
            users.value = [...users.value, created].sort((left, right) => left.username.localeCompare(right.username));
        }

        toast.add({ severity: 'success', summary: 'Usuario guardado', detail: 'Los cambios fueron aplicados.', life: 3000 });
        userDialogVisible.value = false;
        resetUserForm();
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible guardar el usuario.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        savingUser.value = false;
    }
}

onMounted(loadUsers);
</script>

<template>
    <div class="card">
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
            <div>
                <div class="text-2xl font-semibold">Usuarios</div>
                <p class="text-surface-500 mb-0">Administra accesos, estado, permisos y cambio obligatorio de clave.</p>
            </div>
            <Button label="Nuevo usuario" icon="pi pi-user-plus" @click="openCreateUser" />
        </div>

        <DataTable :value="users" :loading="loadingUsers" dataKey="id" paginator :rows="10" responsiveLayout="scroll">
            <Column field="username" header="Usuario" />
            <Column field="full_name" header="Nombre" />
            <Column field="email" header="Email" />
            <Column header="Rol">
                <template #body="{ data }">
                    <Tag :value="data.is_admin ? 'Admin' : 'Usuario'" :severity="data.is_admin ? 'danger' : 'info'" />
                </template>
            </Column>
            <Column header="Estado">
                <template #body="{ data }">
                    <Tag :value="data.is_active ? 'Activo' : 'Inactivo'" :severity="data.is_active ? 'success' : 'secondary'" />
                </template>
            </Column>
            <Column header="Cambio de clave">
                <template #body="{ data }">
                    <Tag :value="data.must_change_password ? 'Pendiente' : 'OK'" :severity="data.must_change_password ? 'warn' : 'success'" />
                </template>
            </Column>
            <Column header="Acciones" style="min-width: 8rem">
                <template #body="{ data }">
                    <Button icon="pi pi-pencil" rounded text @click="openEditUser(data)" />
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="userDialogVisible" modal :header="dialogTitle" :style="{ width: '38rem' }">
            <div class="grid grid-cols-12 gap-4">
                <div class="col-span-12">
                    <label class="block text-sm mb-2">Usuario</label>
                    <InputText v-model="userForm.username" class="w-full" />
                </div>
                <div class="col-span-12">
                    <label class="block text-sm mb-2">Nombre completo</label>
                    <InputText v-model="userForm.full_name" class="w-full" />
                </div>
                <div class="col-span-12">
                    <label class="block text-sm mb-2">Email</label>
                    <InputText v-model="userForm.email" class="w-full" />
                </div>
                <div class="col-span-12">
                    <label class="block text-sm mb-2">{{ editingUserId ? 'Nueva clave temporal' : 'Clave inicial' }}</label>
                    <Password v-model="userForm.password" :feedback="false" fluid toggleMask />
                </div>
                <div class="col-span-12 md:col-span-4">
                    <div class="flex items-center gap-3 min-h-12 px-3 rounded-xl border border-surface-200 dark:border-surface-700">
                        <ToggleSwitch v-model="userForm.is_admin" />
                        <span>Admin</span>
                    </div>
                </div>
                <div class="col-span-12 md:col-span-4">
                    <div class="flex items-center gap-3 min-h-12 px-3 rounded-xl border border-surface-200 dark:border-surface-700">
                        <ToggleSwitch v-model="userForm.is_active" />
                        <span>Activo</span>
                    </div>
                </div>
                <div class="col-span-12 md:col-span-4">
                    <div class="flex items-center gap-3 min-h-12 px-3 rounded-xl border border-surface-200 dark:border-surface-700">
                        <ToggleSwitch v-model="userForm.must_change_password" />
                        <span>Forzar cambio</span>
                    </div>
                </div>
            </div>

            <template #footer>
                <div class="flex justify-end gap-3">
                    <Button label="Cancelar" severity="secondary" outlined @click="userDialogVisible = false" />
                    <Button label="Guardar" icon="pi pi-save" :loading="savingUser" @click="saveUser" />
                </div>
            </template>
        </Dialog>
    </div>
</template>
