<script setup lang="ts">
import PokeBallLogo from '@/components/branding/PokeBallLogo.vue';
import { ApiError } from '@/api/http';
import FloatingConfigurator from '@/components/FloatingConfigurator.vue';
import { loginWithCredentials } from '@/stores/auth';
import { ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';

const REMEMBERED_USERNAME_KEY = 'pokevault:remembered-username';

function readRememberedUsername(): string {
    if (typeof window === 'undefined') {
        return '';
    }

    return window.localStorage.getItem(REMEMBERED_USERNAME_KEY) || '';
}

const route = useRoute();
const router = useRouter();
const toast = useToast();

const rememberedUsername = readRememberedUsername();
const username = ref(rememberedUsername);
const password = ref('');
const rememberUsername = ref(Boolean(rememberedUsername));
const loading = ref(false);

watch(rememberUsername, (enabled) => {
    if (!enabled && typeof window !== 'undefined') {
        window.localStorage.removeItem(REMEMBERED_USERNAME_KEY);
    }
});

function persistRememberedUsername(): void {
    if (typeof window === 'undefined') {
        return;
    }

    if (rememberUsername.value && username.value.trim()) {
        window.localStorage.setItem(REMEMBERED_USERNAME_KEY, username.value.trim());
        return;
    }

    window.localStorage.removeItem(REMEMBERED_USERNAME_KEY);
}

async function submit(): Promise<void> {
    loading.value = true;
    try {
        const user = await loginWithCredentials({
            username: username.value.trim(),
            password: password.value
        });

        persistRememberedUsername();

        const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/';
        if (user.must_change_password) {
            await router.push('/auth/force-password-change');
            return;
        }

        await router.push(redirect);
    } catch (error) {
        const detail =
            error instanceof ApiError && error.status === 401
                ? 'Usuario o clave incorrectos.'
                : error instanceof Error
                  ? error.message
                  : 'No fue posible iniciar sesion.';
        toast.add({ severity: 'error', summary: 'Login fallido', detail, life: 4000 });
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <FloatingConfigurator />
    <div class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen min-w-[100vw] overflow-hidden">
        <div class="flex flex-col items-center justify-center">
            <div style="border-radius: 56px; padding: 0.3rem; background: linear-gradient(180deg, var(--primary-color) 10%, rgba(16, 185, 129, 0) 32%)">
                <div class="w-full bg-surface-0 dark:bg-surface-900 py-16 px-8 sm:px-20" style="border-radius: 53px">
                    <div class="text-center mb-8">
                        <PokeBallLogo class="mb-8 mx-auto h-[4.1rem] w-[4.1rem] shrink-0" />
                        <div class="text-surface-900 dark:text-surface-0 text-3xl font-medium mb-4">Bienvenido a PokeVault TCG</div>
                        <span class="text-muted-color font-medium">Inicia sesion para administrar tu coleccion</span>
                    </div>

                    <div>
                        <label for="username1" class="block text-surface-900 dark:text-surface-0 text-xl font-medium mb-2">Usuario</label>
                        <InputText id="username1" type="text" placeholder="Ingresa tu usuario" class="w-full md:w-[30rem] mb-6" v-model="username" @keyup.enter="submit" />

                        <label for="password1" class="block text-surface-900 dark:text-surface-0 font-medium text-xl mb-2">Clave</label>
                        <Password id="password1" v-model="password" placeholder="Ingresa tu clave" :toggleMask="true" class="mb-6" fluid :feedback="false" @keyup.enter="submit" />

                        <div class="flex items-center justify-between mb-8 gap-4">
                            <div class="flex items-center gap-2">
                                <Checkbox v-model="rememberUsername" inputId="rememberMe" binary />
                                <label for="rememberMe">Recordar usuario</label>
                            </div>
                        </div>

                        <Button label="Entrar" class="w-full" :loading="loading" @click="submit" />
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.pi-eye {
    transform: scale(1.6);
    margin-right: 1rem;
}

.pi-eye-slash {
    transform: scale(1.6);
    margin-right: 1rem;
}
</style>
