<script setup>
import ChangePasswordDialog from '@/components/account/ChangePasswordDialog.vue';
import PokeBallLogo from '@/components/branding/PokeBallLogo.vue';
import { useLayout } from '@/layout/composables/layout';
import { logout, useAuth } from '@/stores/auth';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import AppConfigurator from './AppConfigurator.vue';

const { toggleMenu, toggleDarkMode, isDarkTheme } = useLayout();
const { state, isAdmin } = useAuth();
const router = useRouter();
const changePasswordVisible = ref(false);

async function handleLogout() {
    logout();
    await router.push('/auth/login');
}
</script>

<template>
    <div class="layout-topbar">
        <div class="layout-topbar-logo-container">
            <button class="layout-menu-button layout-topbar-action" @click="toggleMenu">
                <i class="pi pi-bars"></i>
            </button>
            <router-link to="/" class="layout-topbar-logo">
                <PokeBallLogo class="layout-topbar-brand-icon" />

                <span>PokeVault TCG</span>
            </router-link>
        </div>

        <div class="layout-topbar-actions">
            <div class="layout-config-menu">
                <button type="button" class="layout-topbar-action" @click="toggleDarkMode">
                    <i :class="['pi', { 'pi-moon': isDarkTheme, 'pi-sun': !isDarkTheme }]"></i>
                </button>
                <div class="relative">
                    <button
                        v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'p-anchored-overlay-enter-active', leaveToClass: 'hidden', leaveActiveClass: 'p-anchored-overlay-leave-active', hideOnOutsideClick: true }"
                        type="button"
                        class="layout-topbar-action layout-topbar-action-highlight"
                    >
                        <i class="pi pi-palette"></i>
                    </button>
                    <AppConfigurator />
                </div>
            </div>

            <button
                class="layout-topbar-menu-button layout-topbar-action"
                v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'p-anchored-overlay-enter-active', leaveToClass: 'hidden', leaveActiveClass: 'p-anchored-overlay-leave-active', hideOnOutsideClick: true }"
            >
                <i class="pi pi-ellipsis-v"></i>
            </button>

            <div class="layout-topbar-menu hidden lg:block">
                <div class="layout-topbar-menu-content">
                    <button type="button" class="layout-topbar-action" @click="router.push('/cards/search')">
                        <i class="pi pi-search"></i>
                        <span>Buscar carta</span>
                    </button>
                    <button v-if="isAdmin" type="button" class="layout-topbar-action" @click="router.push('/users')">
                        <i class="pi pi-users"></i>
                        <span>Usuarios</span>
                    </button>
                    <div class="relative">
                        <button
                            type="button"
                            class="layout-topbar-action"
                            v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'p-anchored-overlay-enter-active', leaveToClass: 'hidden', leaveActiveClass: 'p-anchored-overlay-leave-active', hideOnOutsideClick: true }"
                        >
                            <i class="pi pi-user"></i>
                            <span>{{ state.user?.username || 'Cuenta' }}</span>
                        </button>
                        <div class="hidden absolute right-0 top-full mt-2 min-w-56 rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900 shadow-xl p-2 z-20">
                            <button type="button" class="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-surface-100 dark:hover:bg-surface-800 text-left" @click="router.push('/profile')">
                                <i class="pi pi-user-edit"></i>
                                <span>Mi perfil</span>
                            </button>
                            <button type="button" class="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-surface-100 dark:hover:bg-surface-800 text-left" @click="changePasswordVisible = true">
                                <i class="pi pi-lock"></i>
                                <span>Cambiar clave</span>
                            </button>
                            <button type="button" class="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-surface-100 dark:hover:bg-surface-800 text-left text-red-500" @click="handleLogout">
                                <i class="pi pi-sign-out"></i>
                                <span>Cerrar sesion</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <ChangePasswordDialog v-model:visible="changePasswordVisible" />
</template>
