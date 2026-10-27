<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import AuthCard from '@/components/AuthCard.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiTextField from '@/components/ui/UiTextField.vue'
import * as authApi from '@/api/endpoints/auth'
import { useFieldErrors, validators } from '@/composables/useFieldErrors'
import { m } from '@/i18n'

const route = useRoute()
const uid = computed(() => (typeof route.query.uid === 'string' ? route.query.uid : ''))
const token = computed(() => (typeof route.query.token === 'string' ? route.query.token : ''))
const confirming = computed(() => Boolean(uid.value && token.value))

const email = ref('')
const newPassword = ref('')
const busy = ref(false)
const done = ref<string | null>(null)
const errors = useFieldErrors<'email' | 'new_password' | 'token'>()

const checkEmail = () => errors.set('email', validators.email(email.value))
const checkPassword = () => errors.set('new_password', validators.newPassword(newPassword.value))

async function submit() {
  errors.form.value = null
  if (confirming.value) checkPassword()
  else checkEmail()
  if (errors.hasErrors()) return
  busy.value = true
  try {
    if (confirming.value) {
      await authApi.confirmPasswordReset({
        uid: uid.value,
        token: token.value,
        new_password: newPassword.value,
      })
      done.value = m.auth.passwordChanged
    } else {
      const { detail } = await authApi.requestPasswordReset({ email: email.value.trim() })
      done.value = `${m.auth.checkEmail} ${detail}`
    }
  } catch (error) {
    errors.fromApi(error, ['email', 'new_password', 'token'])
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard
    :title="m.screens.resetPassword.title"
    :lead="confirming ? m.auth.chooseNew : m.auth.resetIntro"
  >
    <p v-if="done" role="status" class="auth-card__status">{{ done }}</p>
    <form v-else novalidate @submit.prevent="submit">
      <UiTextField
        v-if="confirming"
        v-model="newPassword"
        :label="m.auth.newPassword"
        :hint="m.auth.passwordHint"
        type="password"
        autocomplete="new-password"
        required
        :error="errors.fields.value.new_password"
        @blur="checkPassword"
      />
      <UiTextField
        v-else
        v-model="email"
        :label="m.auth.email"
        type="email"
        autocomplete="email"
        required
        :error="errors.fields.value.email"
        @blur="checkEmail"
      />
      <p
        v-if="errors.fields.value.token || errors.form.value"
        role="alert"
        class="auth-card__alert"
      >
        {{ errors.fields.value.token || errors.form.value }}
      </p>
      <UiButton type="submit" variant="primary" size="lg" :busy="busy">
        {{ confirming ? m.auth.setPassword : m.auth.sendLink }}
      </UiButton>
    </form>
    <div class="auth-card__links">
      <RouterLink to="/login">{{ m.auth.backToLogin }}</RouterLink>
    </div>
  </AuthCard>
</template>
