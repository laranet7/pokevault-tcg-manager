<script setup>
import { computed } from 'vue';
import { useAuth } from '@/stores/auth';
import AppMenuItem from './AppMenuItem.vue';

const { isAdmin } = useAuth();

const model = computed(() => [
    {
        label: 'Inicio',
        items: [
            {
                label: 'Dashboard',
                icon: 'pi pi-fw pi-home',
                to: '/'
            }
        ]
    },
    {
        label: 'Catalogo',
        items: [
            {
                label: 'Buscar carta',
                icon: 'pi pi-fw pi-search',
                to: '/cards/search'
            },
            {
                label: 'Colecciones',
                icon: 'pi pi-fw pi-folder-open',
                to: '/collections'
            }
        ]
    },
    {
        label: 'Cuenta',
        items: [
            {
                label: 'Mi perfil',
                icon: 'pi pi-fw pi-user',
                to: '/profile'
            },
            {
                label: 'Usuarios',
                icon: 'pi pi-fw pi-users',
                to: '/users',
                visible: isAdmin.value
            }
        ]
    },
    {
        label: 'Documentacion',
        items: [
            {
                label: 'Pokemon TCG API',
                icon: 'pi pi-fw pi-book',
                url: 'https://docs.pokemontcg.io/',
                target: '_blank'
            },
            {
                label: 'Sakai Documentation',
                icon: 'pi pi-fw pi-bookmark',
                url: 'https://sakai.primevue.org/start/documentation',
                target: '_blank'
            }
        ]
    }
]);
</script>

<template>
    <ul class="layout-menu">
        <template v-for="(item, i) in model" :key="item">
            <app-menu-item v-if="!item.separator" :item="item" :index="i"></app-menu-item>
            <li v-if="item.separator" class="menu-separator"></li>
        </template>
    </ul>
</template>

<style lang="scss" scoped></style>
