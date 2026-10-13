# 移动表单实测数值

`node tests/auth-forms-mobile.mjs` 于最终编译缓存上重跑。390/430 的 EN/DE 控件与触控目标均 >=44；1440 保留桌面尺寸。

## 390

| 面 | 输入高度 | 主按钮 | 内容左边距 | 分组间距 | 触控高度 |
|---|---:|---:|---:|---:|---|
| en-login | 52, 52 | 52 × 324 | 33 | 24, 24, 24 | Show password 52, Remember me 44, Log in 52, Lost your password? 44 |
| en-register-1 | 52, 52, 52 | — | 33 | 24, 24 | — |
| en-register-2 | 52, 52, 52, 52, 52, 52 | — | 33 | 24, 24, 24, 24, 24 | — |
| en-register-3 | 52, 52 | — | 33 | 24 | Show password 52 |
| en-register | 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 52 | 52 × 324 | 33 | 24, 24 | Show password 52, privacy policy 44, Terms of Sale 44, Privacy 44 |
| en-forgot | 52 | 52 × 324 | 33 | 24 | Reset password 52, Back to sign in 44 |
| en-contact | 160, 52, 52, 52 | 52 × 362 | 14 | 24, 24, 24 | I agree that my details may  70.25, Privacy 44, Send message 52 |
| en-contact-success | — | 52 × 328 | 14 | — | Send another message 52 |
| de-login | 52, 52 | 52 × 324 | 33 | 24, 24, 24 | Passwort anzeigen 52, Angemeldet bleiben 44, Anmelden 52, Passwort vergessen? 44 |
| de-register-1 | 52, 52, 52 | — | 33 | 24, 24 | — |
| de-register-2 | 52, 52, 52, 52, 52, 52 | — | 33 | 24, 24, 24, 24, 24 | — |
| de-register-3 | 52, 52 | — | 33 | 24 | Passwort anzeigen 52 |
| de-register | 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 52 | 52 × 324 | 33 | 24, 24 | Passwort anzeigen 52, Datenschutzerklärung 44, Verkaufsbedingungen 44, Datenschutz 44 |
| de-forgot | 52 | 52 × 324 | 33 | 24 | Passwort zurücksetzen 52, Zurück zur Anmeldung 44 |
| de-contact | 160, 52, 52, 52 | 52 × 362 | 14 | 24, 24, 24 | Ich bin damit einverstanden, 96.5, Datenschutz 44, Nachricht senden 52 |
| de-contact-success | — | 52 × 328 | 14 | — | Weitere Nachricht senden 52 |
| en-proforma | 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 67.59 | 52 × 324 | 16 | 24, 24, 24, 24, 24, 24, 24, 24, 24, 24 | privacy policy 44, I have read and agree to the 72, terms and conditions 44, Request Proforma 52 |
| de-proforma | 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 67.59 | 52 × 324 | 16 | 24, 24, 24, 24, 24, 24, 24, 24, 24, 24 | Datenschutzerklärung 44, Ich habe die Allgemeine Gesc 100, Allgemeine Geschäftsbedingun 44, Proforma anfordern 52 |
| en-proforma-success | — | 52 × 324 | 16 | — | View inquiries 52 |
| de-proforma-success | — | 52 × 324 | 16 | — | Anfragen ansehen 52 |

## 1440

| 面 | 输入高度 | 主按钮 | 内容左边距 | 分组间距 | 触控高度 |
|---|---:|---:|---:|---:|---|
| en-login | 52, 52 | 45.5 × 308 | 566 | 20, 20, 20 | Show password 22, Remember me 28, Log in 45.5, Lost your password? 18 |
| en-register-1 | 52, 44, 52 | — | 486 | 20, 20 | — |
| en-register-2 | 52, 52, 44, 52, 52, 52 | — | 486 | -80, 20, 20, 20, 20 | — |
| en-register-3 | 52, 52 | — | 486 | 20 | Show password 22 |
| en-register | 52, 44, 52, 52, 52, 44, 52, 52, 52, 52, 52 | 45.5 × 468 | 486 | 20, 20 | Show password 22, privacy policy 21, Terms of Sale 23.09, Privacy 23.09 |
| en-forgot | 52 | 45.5 × 350 | 545 | 20 | Reset password 45.5, Back to sign in 18 |
| en-contact | 152.34, 40.39, 40.39, 40.39 | 44 × 149.31 | 681.59 | 0, 0, 0 | I agree that my details may  19, Privacy 19, Send message 44 |
| en-contact-success | — | 44 × 204.58 | 681.59 | — | Send another message 44 |
| de-login | 52, 52 | 45.5 × 308 | 566 | 20, 20, 20 | Passwort anzeigen 22, Angemeldet bleiben 28, Anmelden 45.5, Passwort vergessen? 18 |
| de-register-1 | 52, 44, 52 | — | 486 | 20, 20 | — |
| de-register-2 | 52, 52, 44, 52, 52, 52 | — | 486 | -80, 20, 20, 20, 20 | — |
| de-register-3 | 52, 52 | — | 486 | 20 | Passwort anzeigen 22 |
| de-register | 52, 44, 52, 52, 52, 44, 52, 52, 52, 52, 52 | 45.5 × 468 | 486 | 20, 20 | Passwort anzeigen 22, Datenschutzerklärung 21, Verkaufsbedingungen 23.09, Datenschutz 23.09 |
| de-forgot | 52 | 45.5 × 350 | 545 | 20 | Passwort zurücksetzen 45.5, Zurück zur Anmeldung 18 |
| de-contact | 152.34, 40.39, 40.39, 40.39 | 44 × 168.56 | 681.59 | 0, 0, 0 | Ich bin damit einverstanden, 45.25, Datenschutz 19, Nachricht senden 44 |
| de-contact-success | — | 44 × 224.41 | 681.59 | — | Weitere Nachricht senden 44 |
| en-proforma | 48, 48, 48, 48, 48, 58, 48, 48, 48, 48, 48, 48, 104 | 48 × 290.8 | 156 | -82.39, 32, 32, 32, 32, 32, 32, 32, 32, 32 | privacy policy 21, I have read and agree to the 56, terms and conditions 18, Request Proforma 48 |
| de-proforma | 48, 48, 48, 48, 48, 58, 48, 48, 48, 48, 48, 48, 104 | 48 × 290.8 | 156 | -82.39, 32, 32, 32, 32, 32, 32, 32, 32, 32 | Datenschutzerklärung 21, Ich habe die Allgemeine Gesc 84, Allgemeine Geschäftsbedingun 46, Proforma anfordern 48 |
| en-proforma-success | — | 0 × 0 | 0 | — | — |
| de-proforma-success | — | 0 × 0 | 0 | — | — |

## 430

| 面 | 输入高度 | 主按钮 | 内容左边距 | 分组间距 | 触控高度 |
|---|---:|---:|---:|---:|---|
| en-login | 52, 52 | 52 × 364 | 33 | 24, 24, 24 | Show password 52, Remember me 44, Log in 52, Lost your password? 44 |
| en-register-1 | 52, 52, 52 | — | 33 | 24, 24 | — |
| en-register-2 | 52, 52, 52, 52, 52, 52 | — | 33 | 24, 24, 24, 24, 24 | — |
| en-register-3 | 52, 52 | — | 33 | 24 | Show password 52 |
| en-register | 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 52 | 52 × 364 | 33 | 24, 24 | Show password 52, privacy policy 44, Terms of Sale 44, Privacy 44 |
| en-forgot | 52 | 52 × 364 | 33 | 24 | Reset password 52, Back to sign in 44 |
| en-contact | 160, 52, 52, 52 | 52 × 402 | 14 | 24, 24, 24 | I agree that my details may  70.25, Privacy 44, Send message 52 |
| en-contact-success | — | 52 × 368 | 14 | — | Send another message 52 |
| de-login | 52, 52 | 52 × 364 | 33 | 24, 24, 24 | Passwort anzeigen 52, Angemeldet bleiben 44, Anmelden 52, Passwort vergessen? 44 |
| de-register-1 | 52, 52, 52 | — | 33 | 24, 24 | — |
| de-register-2 | 52, 52, 52, 52, 52, 52 | — | 33 | 24, 24, 24, 24, 24 | — |
| de-register-3 | 52, 52 | — | 33 | 24 | Passwort anzeigen 52 |
| de-register | 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 52 | 52 × 364 | 33 | 24, 24 | Passwort anzeigen 52, Datenschutzerklärung 44, Verkaufsbedingungen 44, Datenschutz 44 |
| de-forgot | 52 | 52 × 364 | 33 | 24 | Passwort zurücksetzen 52, Zurück zur Anmeldung 44 |
| de-contact | 160, 52, 52, 52 | 52 × 402 | 14 | 24, 24, 24 | Ich bin damit einverstanden, 96.5, Datenschutz 44, Nachricht senden 52 |
| de-contact-success | — | 52 × 368 | 14 | — | Weitere Nachricht senden 52 |
| en-proforma | 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 67.59 | 52 × 364 | 16 | 24, 24, 24, 24, 24, 24, 24, 24, 24, 24 | privacy policy 44, I have read and agree to the 72, terms and conditions 44, Request Proforma 52 |
| de-proforma | 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 67.59 | 52 × 364 | 16 | 24, 24, 24, 24, 24, 24, 24, 24, 24, 24 | Datenschutzerklärung 44, Ich habe die Allgemeine Gesc 72, Allgemeine Geschäftsbedingun 44, Proforma anfordern 52 |
| en-proforma-success | — | 52 × 364 | 16 | — | View inquiries 52 |
| de-proforma-success | — | 52 × 364 | 16 | — | Anfragen ansehen 52 |

