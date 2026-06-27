<script setup lang="ts">
const clipPathId = `pokevault-ball-clip-${Math.random().toString(36).slice(2, 10)}`;
</script>

<template>
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <defs>
            <clipPath :id="clipPathId">
                <circle cx="32" cy="32" r="28" />
            </clipPath>
        </defs>

        <circle cx="32" cy="32" r="28" fill="#101828" />
        <g :clip-path="`url(#${clipPathId})`">
            <path d="M4 32C4 16.536 16.536 4 32 4C47.464 4 60 16.536 60 32H4Z" fill="#FF3B30" />
            <path d="M4 32H60C60 47.464 47.464 60 32 60C16.536 60 4 47.464 4 32Z" fill="#F8FAFC" />
            <path d="M44 4.924C54.021 9.407 60.774 19.454 60.774 31.079H54.479C54.479 21.465 50.224 12.843 43.496 6.993L44 4.924Z" fill="#D92D20" opacity="0.9" />
            <path d="M60.774 31.079C60.774 42.704 54.021 52.75 44 57.234L43.496 55.166C50.224 49.316 54.479 40.693 54.479 31.079H60.774Z" fill="#D0D5DD" opacity="0.95" />
        </g>
        <rect x="4" y="28" width="56" height="8" rx="4" fill="#101828" />
        <circle cx="32" cy="32" r="11.5" fill="#101828" />
        <circle cx="32" cy="32" r="5.5" fill="var(--primary-color)" />
        <circle cx="32" cy="32" r="3.25" fill="#FFFFFF" opacity="0.35" />
    </svg>
</template>
