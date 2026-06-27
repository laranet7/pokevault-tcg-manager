import AppLayout from '@/layout/AppLayout.vue';
import { ensureAuthReady, useAuth } from '@/stores/auth';
import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            component: AppLayout,
            children: [
                {
                    path: '/',
                    name: 'dashboard',
                    component: () => import('@/views/DashboardView.vue')
                },
                {
                    path: '/cards/search',
                    name: 'card-search',
                    component: () => import('@/views/CardSearchView.vue')
                },
                {
                    path: '/collections',
                    name: 'collections',
                    component: () => import('@/views/CollectionsView.vue')
                },
                {
                    path: '/collections/:id',
                    name: 'collection-detail',
                    component: () => import('@/views/CollectionDetailView.vue')
                },
                {
                    path: '/profile',
                    name: 'profile',
                    component: () => import('@/views/ProfileView.vue')
                },
                {
                    path: '/users',
                    name: 'users',
                    component: () => import('@/views/UsersView.vue')
                }
            ]
        },
        {
            path: '/auth/login',
            name: 'login',
            meta: { public: true },
            component: () => import('@/views/pages/auth/Login.vue')
        },
        {
            path: '/auth/force-password-change',
            name: 'force-password-change',
            meta: { public: true, passwordFlow: true },
            component: () => import('@/views/pages/auth/ForcePasswordChange.vue')
        },
        {
            path: '/auth/change-password',
            redirect: '/'
        },
        {
            path: '/pages/notfound',
            name: 'notfound',
            meta: { public: true },
            component: () => import('@/views/pages/NotFound.vue')
        },
        {
            path: '/:pathMatch(.*)*',
            redirect: '/pages/notfound'
        }
    ]
});

router.beforeEach(async (to) => {
    await ensureAuthReady();

    const { state, isAuthenticated } = useAuth();
    const authenticated = isAuthenticated.value;
    const mustChangePassword = Boolean(state.user?.must_change_password);

    if (authenticated && mustChangePassword && to.name !== 'force-password-change') {
        return { name: 'force-password-change' };
    }

    if (to.meta.public) {
        if (authenticated && !mustChangePassword && to.name === 'login') {
            return { name: 'dashboard' };
        }
        if (!authenticated && to.name === 'force-password-change') {
            return { name: 'login' };
        }
        return true;
    }

    if (!authenticated) {
        return { name: 'login', query: { redirect: to.fullPath } };
    }

    if (to.name === 'users' && !state.user?.is_admin) {
        return { name: 'dashboard' };
    }

    return true;
});

export default router;
