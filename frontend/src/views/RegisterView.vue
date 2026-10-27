<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AuthCard from '@/components/AuthCard.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiTextField from '@/components/ui/UiTextField.vue'
import { safeNext, useFieldErrors, validators } from '@/composables/useFieldErrors'
import { m } from '@/i18n'
import { useAuthStore } from '@/stores/auth'

type Field = 'display_name' | 'email' | 'password'
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const displayName = ref('')
const email = ref('')
const password = ref('')
const busy = ref(false)
const errors = useFieldErrors<Field>()

const checks: Record<Field, () => void> = {
  display_name: () => errors.set('display_name', validators.displayName(displayName.value)),
  email: () => errors.set('email', validators.email(email.value)),
  password: () => errors.set('password', validators.newPassword(password.value)),
}

async function submit() {
  errors.form.value = null
  Object.values(checks).forEach((check) => check())
  if (errors.hasErrors()) return
  busy.value = true
  try {
    await auth.register({
      email: email.value.trim(),
      password: password.value,
      display_name: displayName.value.trim(),
    })
    await router.push(safeNext(route.query.next))
  } catch (error) {
    errors.fromApi(error, ['display_name', 'email', 'password'])
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard :title="m.screens.register.title" :lead="m.auth.benefit">
    <form novalidate @submit.prevent="submit">
      <UiTextField
        v-model="displayName"
        :label="m.auth.displayName"
        :hint="m.auth.displayNameHint"
        autocomplete="nickname"
        required
        :error="errors.fields.value.display_name"
        @blur="checks.display_name"
      />
      <UiTextField
        v-model="email"
        :label="m.auth.email"
        type="email"
        autocomplete="email"
        required
        :error="errors.fields.value.email"
        @blur="checks.email"
      />
      <UiTextField
        v-model="password"
        :label="m.auth.password"
        :hint="m.auth.passwordHint"
        type="password"
        autocomplete="new-password"
        required
        :error="errors.fields.value.password"
        @blur="checks.password"
      />
      <p v-if="errors.form.value" role="alert" class="auth-card__alert">{{ errors.form.value }}</p>
      <UiButton type="submit" variant="primary" size="lg" :busy="busy">{{
        m.auth.registerButton
      }}</UiButton>
    </form>
    <div class="auth-card__links">
      <span
        >{{ m.auth.haveAccount }}
        <RouterLink to="/login">{{ m.auth.logInButton }}</RouterLink></span
      >
      <span
        >{{ m.auth.guestNote }} <RouterLink to="/cases">{{ m.auth.browseCases }}</RouterLink></span
      >
    </div>
  </AuthCard>
</template>
