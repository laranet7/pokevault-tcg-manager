<script setup lang="ts">
import { acceptTerms, getTermsStatus } from '@/api/termsApi';
import { logout, refreshCurrentUser, useAuth } from '@/stores/auth';
import type { TermsStatus } from '@/types/terms';
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';

const toast = useToast();
const router = useRouter();
const { state } = useAuth();

const acceptedCheckbox = ref(false);
const loadingStatus = ref(true);
const submitting = ref(false);
const retrying = ref(false);
const errorMessage = ref('');
const status = ref<TermsStatus | null>(null);

const termsSections = [
    {
        title: '1. Naturaleza del proyecto',
        paragraphs: [
            'PokeVault TCG es una aplicacion no oficial, de uso personal y sin fines de lucro, creada para organizar, registrar y valorizar colecciones personales de cartas Pokemon TCG.',
            'El sistema permite registrar colecciones, cartas, cantidades, estados fisicos, idiomas, precios base, precios estimados de venta e historial de valorizacion. La informacion generada por la aplicacion tiene caracter referencial y no constituye tasacion profesional, asesoria comercial, financiera ni garantia de valor de mercado.'
        ]
    },
    {
        title: '2. Proyecto no oficial',
        paragraphs: [
            'PokeVault TCG no esta afiliado, patrocinado, respaldado, aprobado ni asociado oficialmente con Nintendo, Creatures Inc., GAME FREAK inc., The Pokemon Company ni The Pokemon Company International.',
            'Los nombres, marcas, personajes, imagenes, referencias y demas elementos relacionados con Pokemon pertenecen a sus respectivos propietarios. Su uso dentro de este sistema es unicamente referencial, descriptivo e informativo, con el proposito de permitir la organizacion personal de colecciones.'
        ]
    },
    {
        title: '3. Uso bajo responsabilidad del usuario',
        paragraphs: [
            'El uso, instalacion, modificacion, publicacion, distribucion o ejecucion de PokeVault TCG es responsabilidad exclusiva de cada usuario.',
            'El autor o los colaboradores del proyecto no seran responsables por perdidas de informacion, errores de calculo, uso indebido del sistema, decisiones comerciales tomadas en base a los datos mostrados, problemas de instalacion, fallas tecnicas, danos directos o indirectos, ni cualquier otro perjuicio derivado del uso de la aplicacion.',
            'El usuario entiende que debe revisar, respaldar y validar la informacion antes de tomar decisiones basadas en ella.'
        ]
    },
    {
        title: '4. Precios y valorizaciones',
        paragraphs: [
            'Los precios, valorizaciones e historicos mostrados por PokeVault TCG son estimaciones referenciales. Estos valores pueden provenir de APIs externas, datos ingresados manualmente o calculos internos del sistema.',
            'El valor real de una carta puede variar segun pais, idioma, estado fisico, edicion, demanda, disponibilidad, mercado local, comisiones, impuestos, costos de envio y otros factores externos.',
            'PokeVault TCG no garantiza que los precios mostrados sean exactos, actualizados, completos o representativos del valor real de compra o venta.'
        ]
    },
    {
        title: '5. APIs y servicios externos',
        paragraphs: [
            'PokeVault TCG puede utilizar APIs o fuentes externas para obtener informacion de cartas, imagenes, sets, rarezas o precios referenciales.',
            'El sistema no controla la disponibilidad, exactitud, cambios, limites de uso ni continuidad de dichos servicios externos. Si una API externa deja de funcionar, modifica su estructura o limita el acceso, algunas funciones del sistema podrian verse afectadas.'
        ]
    },
    {
        title: '6. Contenido registrado por el usuario',
        paragraphs: [
            'Cada usuario es responsable de la informacion que registra en el sistema, incluyendo nombres de colecciones, notas, precios, cantidades, estados de cartas y cualquier otro dato ingresado manualmente.',
            'El usuario debe evitar ingresar informacion falsa, enganosa, ilegal o que infrinja derechos de terceros.'
        ]
    },
    {
        title: '7. Sin garantia',
        paragraphs: [
            'PokeVault TCG se entrega "tal cual", sin garantias de ningun tipo, expresas o implicitas.',
            'No se garantiza que el sistema este libre de errores, que funcione sin interrupciones, que sea compatible con todos los entornos, que mantenga disponibilidad permanente ni que sus datos sean exactos o completos.'
        ]
    },
    {
        title: '8. Aceptacion de terminos',
        paragraphs: [
            'Para acceder y utilizar PokeVault TCG, debes aceptar estos terminos de uso y disclaimer.',
            'Si no aceptas estos terminos, no podras continuar usando el sistema.',
            'Al marcar la casilla de aceptacion y continuar, confirmas que has leido, entendido y aceptado estas condiciones.'
        ]
    }
];

const acceptanceLabel =
    'Declaro que he leido y acepto los Terminos de uso y disclaimer de PokeVault TCG. Entiendo que PokeVault TCG es un proyecto no oficial, sin fines de lucro, no afiliado a Nintendo, Creatures Inc., GAME FREAK inc., The Pokemon Company ni The Pokemon Company International, y acepto que el uso del sistema, sus datos, precios, valorizaciones e informacion registrada es bajo mi exclusiva responsabilidad.';

const shouldCheckTerms = computed(() => Boolean(state.user) && !state.user?.must_change_password);
const dialogVisible = computed(() => shouldCheckTerms.value && (loadingStatus.value || Boolean(errorMessage.value) || !status.value?.accepted));
const canAccept = computed(() => Boolean(status.value?.current_version) && acceptedCheckbox.value && !submitting.value);

function resetDialogState(): void {
    acceptedCheckbox.value = false;
    errorMessage.value = '';
    status.value = null;
}

async function loadStatus(showRetryToast = false): Promise<void> {
    if (!shouldCheckTerms.value) {
        loadingStatus.value = false;
        resetDialogState();
        return;
    }

    loadingStatus.value = true;
    errorMessage.value = '';

    try {
        status.value = await getTermsStatus();
        acceptedCheckbox.value = false;
    } catch (error) {
        status.value = null;
        errorMessage.value = error instanceof Error ? error.message : 'No fue posible validar los terminos vigentes.';
        if (showRetryToast) {
            toast.add({ severity: 'error', summary: 'Validacion pendiente', detail: errorMessage.value, life: 4000 });
        }
    } finally {
        loadingStatus.value = false;
    }
}

async function retryStatus(): Promise<void> {
    retrying.value = true;
    await loadStatus(true);
    retrying.value = false;
}

async function closeSession(): Promise<void> {
    logout();
    await router.push('/auth/login');
}

async function submitAcceptance(): Promise<void> {
    if (!status.value) {
        return;
    }

    submitting.value = true;
    try {
        const accepted = await acceptTerms({ terms_version: status.value.current_version });
        status.value = {
            accepted: true,
            current_version: status.value.current_version,
            accepted_version: accepted.terms_version,
            accepted_at: accepted.accepted_at
        };
        acceptedCheckbox.value = false;
        await refreshCurrentUser();
        toast.add({ severity: 'success', summary: 'Terminos aceptados', detail: 'Ya puedes continuar usando PokeVault TCG.', life: 3000 });
    } catch (error) {
        const detail = error instanceof Error ? error.message : 'No fue posible registrar la aceptacion.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    } finally {
        submitting.value = false;
    }
}

onMounted(async () => {
    await loadStatus();
});

watch(
    () => state.user?.id,
    async () => {
        resetDialogState();
        await loadStatus();
    }
);

watch(
    () => state.user?.must_change_password,
    async () => {
        resetDialogState();
        await loadStatus();
    }
);
</script>

<template>
    <Dialog
        :visible="dialogVisible"
        modal
        :closable="false"
        :dismissableMask="false"
        :closeOnEscape="false"
        :draggable="false"
        header="Términos de uso y disclaimer"
        :style="{ width: 'min(60rem, 96vw)' }"
    >
        <div class="flex flex-col gap-5">
            <div>
                <div class="text-xl font-semibold mb-2">Bienvenido/a a PokeVault TCG.</div>
                <p class="text-surface-500 mb-0">
                    Antes de continuar, debes leer y aceptar estos terminos de uso. Al utilizar este sistema, declaras que entiendes y aceptas las condiciones descritas a continuacion.
                </p>
            </div>

            <div v-if="loadingStatus" class="flex flex-col items-center justify-center gap-4 py-8">
                <ProgressSpinner style="width: 3rem; height: 3rem" strokeWidth="6" />
                <p class="text-surface-500 mb-0">Validando terminos vigentes...</p>
            </div>

            <template v-else-if="errorMessage">
                <Message severity="error" :closable="false">
                    {{ errorMessage }}
                </Message>
                <p class="text-surface-500 mb-0">Necesitamos validar el estado de aceptacion antes de permitir el acceso al sistema.</p>
            </template>

            <template v-else-if="status">
                <div class="flex flex-wrap items-center gap-2">
                    <Tag severity="contrast" :value="`Version vigente ${status.current_version}`" />
                    <Tag v-if="status.accepted_version" severity="info" :value="`Ultima aceptacion ${status.accepted_version}`" />
                </div>

                <ScrollPanel style="width: 100%; height: 26rem" class="rounded-2xl border border-surface-200 dark:border-surface-700">
                    <div class="p-4 md:p-5 flex flex-col gap-5">
                        <div v-for="section in termsSections" :key="section.title" class="flex flex-col gap-2">
                            <div class="font-semibold text-base">{{ section.title }}</div>
                            <p v-for="paragraph in section.paragraphs" :key="paragraph" class="mb-0 leading-7 text-surface-700 dark:text-surface-300">
                                {{ paragraph }}
                            </p>
                        </div>
                    </div>
                </ScrollPanel>

                <div class="rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900/60 p-4">
                    <div class="flex items-start gap-3">
                        <Checkbox v-model="acceptedCheckbox" inputId="termsAccepted" binary class="mt-1" />
                        <label for="termsAccepted" class="leading-6 cursor-pointer">
                            {{ acceptanceLabel }}
                        </label>
                    </div>
                </div>
            </template>
        </div>

        <template #footer>
            <div class="flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
                <Button label="Cerrar sesion" severity="secondary" outlined :disabled="submitting" @click="closeSession" />
                <Button v-if="errorMessage" label="Reintentar" :loading="retrying" @click="retryStatus" />
                <Button v-else label="Aceptar y continuar" :disabled="!canAccept" :loading="submitting" @click="submitAcceptance" />
            </div>
        </template>
    </Dialog>
</template>
