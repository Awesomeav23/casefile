<script setup lang="ts">
/** Investigation workspace shell: left rail + active section (SCREEN_DESIGN §7.1). */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { m } from '@/i18n'

const route = useRoute()
const id = computed(() => String(route.params.playthroughId))

const sections = [
  { name: 'overview', label: m.nav.overview },
  { name: 'locations', label: m.nav.locations },
  { name: 'evidence', label: m.nav.evidence },
  { name: 'people', label: m.nav.people },
  { name: 'timeline', label: m.nav.timeline },
  { name: 'board', label: m.nav.board },
  { name: 'theories', label: m.nav.theories },
] as const
</script>

<template>
  <div class="workspace">
    <nav class="workspace__rail" :aria-label="m.nav.workspace">
      <ul>
        <li v-for="s in sections" :key="s.name">
          <RouterLink :to="`/play/${id}/${s.name}`" class="workspace__link">{{
            s.label
          }}</RouterLink>
        </li>
      </ul>
      <RouterLink :to="`/play/${id}/accuse`" class="workspace__accuse">{{
        m.nav.accuse
      }}</RouterLink>
    </nav>
    <div class="workspace__content"><RouterView /></div>
  </div>
</template>

<style scoped>
.workspace {
  display: grid;
  grid-template-columns: var(--rail-width) 1fr;
  gap: var(--space-5);
  min-height: 70vh;
}
.workspace__rail {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: var(--space-4) 0;
  border-right: 1px solid var(--color-border);
}
.workspace__rail ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-1);
}
.workspace__link {
  display: block;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  color: var(--color-text);
  text-decoration: none;
}
.workspace__link:hover {
  background: var(--color-raised);
}
.workspace__link.router-link-active {
  color: var(--color-accent);
  font-weight: 600;
}
.workspace__accuse {
  margin: var(--space-4) var(--space-3) 0 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-sm);
  color: var(--color-accent);
  font-weight: 600;
  text-align: center;
  text-decoration: none;
}
@media (max-width: 767px) {
  .workspace {
    grid-template-columns: 1fr;
  }
  .workspace__rail {
    border-right: 0;
    border-bottom: 1px solid var(--color-border);
  }
  .workspace__rail ul {
    grid-auto-flow: column;
    overflow-x: auto;
  }
}
</style>
