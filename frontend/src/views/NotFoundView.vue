<script setup lang="ts">
import { m } from '@/i18n'
</script>

<template>
  <section class="not-found">
    <h1>{{ m.screens.notFound.title }}</h1>
    <p>{{ m.screens.notFound.body }}</p>
    <RouterLink to="/cases">{{ m.common.backToLibrary }}</RouterLink>
  </section>
</template>

<style scoped>
.not-found {
  padding: var(--space-7) 0;
}
</style>
