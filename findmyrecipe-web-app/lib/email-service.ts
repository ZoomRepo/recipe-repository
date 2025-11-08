import nodemailer from "nodemailer"

import { resolveLoginGateConfig } from "./login-gate-config"

let cachedTransporter: nodemailer.Transporter | null = null

function ensureEmailConfig() {
  const config = resolveLoginGateConfig()

  if (!config.loginEmailSender) {
    throw new Error("LOGIN_EMAIL_SENDER environment variable must be set to send login codes")
  }

  if (!config.smtpHost || !config.smtpPort || !config.smtpUser || !config.smtpPassword) {
    throw new Error("SMTP configuration is incomplete. Please set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, and SMTP_PASSWORD.")
  }

  return config
}

function getTransporter() {
  if (cachedTransporter) {
    return cachedTransporter
  }

  const config = ensureEmailConfig()

  cachedTransporter = nodemailer.createTransport({
    host: config.smtpHost!,
    port: config.smtpPort!,
    secure: config.smtpSecure,
    auth: {
      user: config.smtpUser!,
      pass: config.smtpPassword!,
    },
  })

  return cachedTransporter
}

export async function sendLoginCodeEmail({
  recipient,
  code,
}: {
  recipient: string
  code: string
}): Promise<void> {
  const config = ensureEmailConfig()
  const transporter = getTransporter()

  await transporter.sendMail({
    from: config.loginEmailSender!,
    to: recipient,
    subject: config.emailSubject,
    text: `Your login code is ${code}. It will expire in ${config.codeExpiryMinutes} minutes.`,
    html: `<p>Your login code is <strong>${code}</strong>.</p><p>This code will expire in ${config.codeExpiryMinutes} minutes.</p>`,
  })
}
