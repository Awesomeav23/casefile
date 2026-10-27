<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AuthCard from '@/components/AuthCard.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiTextField from '@/components/ui/UiTextField.vue'
import { safeNext, useFieldErrors, validators } from '@/composables/useFieldErrors'
import { m } from '@/i18n'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const busy = ref(false)
const errors = useFieldErrors<'email' | 'password'>()

const checkEmail = () => errors.set('email', validators.email(email.value))
const checkPassword = () => errors.set('password', validators.required(password.value))

async function submit() {
  errors.form.value = null
  checkEmail()
  checkPassword()
  if (errors.hasErrors()) return
  busy.value = true
  try {
    await auth.login({ email: email.value.trim(), password: password.value })
    await router.push(safeNext(route.query.next))
  } catch (error) {
    errors.fromApi(error, ['email', 'password'])
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard :title="m.screens.login.title" :lead="m.auth.benefit">
    <form novalidate @submit.prevent="submit">
      <UiTextField
        v-model="email"
        :label="m.auth.email"
        type="email"
        autocomplete="email"
        required
        :error="errors.fields.value.email"
        @blur="checkEmail"
      />
      <UiTextField
        v-model="password"
        :label="m.auth.password"
        type="password"
        autocomplete="current-password"
        required
        :error="errors.fields.value.password"
        @blur="checkPassword"
      />
      <p v-if="errors.form.value" role="alert" class="auth-card__alert">{{ errors.form.value }}</p>
      <UiButton type="submit" variant="primary" size="lg" :busy="busy">{{
        m.auth.logInButton
      }}</UiButton>
    </form>
    <div class="auth-card__links">
      <RouterLink to="/reset-password">{{ m.auth.forgot }}</RouterLink>
      <span
        >{{ m.auth.noAccount }}
        <RouterLink to="/register">{{ m.auth.createAccount }}</RouterLink></span
      >
      <span
        >{{ m.auth.guestNote }} <RouterLink to="/cases">{{ m.auth.browseCases }}</RouterLink></span
      >
    </div>
  </AuthCard>
</template>
