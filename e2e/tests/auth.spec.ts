import { expect, test, type Page } from '@playwright/test'

/** auth.spec (TESTING_PLAN §8): register → logout → login → password reset request. */

const PASSWORD = 'a-long-password-1'
const mainNav = (page: Page) => page.getByRole('navigation', { name: 'Main' })

test('register, log out, log in, and request a password reset', async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`

  await page.goto('/register')
  await expect(page.getByRole('heading', { name: 'Create an account' })).toBeVisible()
  await expect(page.getByText('Keep your progress across devices')).toBeVisible()
  await page.getByLabel('Display name').fill('E2E Tester')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Create account' }).click()

  await expect(page).toHaveURL(/\/cases$/)
  await expect(mainNav(page)).toContainText('E2E Tester')

  await page.reload() // the session survives a reload
  await expect(mainNav(page)).toContainText('E2E Tester')

  await mainNav(page).getByRole('button', { name: 'Log out' }).click()
  await expect(page).toHaveURL(/\/$/)
  await expect(mainNav(page).getByRole('link', { name: 'Log in' })).toBeVisible()

  await mainNav(page).getByRole('link', { name: 'Log in' }).click()
  await page.getByLabel('Email').fill(email.toUpperCase()) // emails are case-insensitive
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page).toHaveURL(/\/cases$/)
  await expect(mainNav(page)).toContainText('E2E Tester')

  await mainNav(page).getByRole('button', { name: 'Log out' }).click()
  await page.goto('/reset-password')
  await page.getByLabel('Email').fill(email)
  await page.getByRole('button', { name: 'Send reset link' }).click()
  await expect(page.getByRole('main').getByRole('status')).toContainText('Check your email')
})

test('a wrong password shows a clear error and keeps you on the form', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill('nobody@example.com')
  await page.getByLabel('Password', { exact: true }).fill('wrong-password')
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page.getByRole('alert')).toHaveText("That email and password don't match.")
  await expect(page).toHaveURL(/\/login$/)
})

test('nobody is asked to sign up to browse cases (guest play, D-01)', async ({ page }) => {
  await page.goto('/cases')
  await expect(page).toHaveURL(/\/cases$/)
  await expect(page.getByRole('heading', { name: 'Case library' })).toBeVisible()
})
