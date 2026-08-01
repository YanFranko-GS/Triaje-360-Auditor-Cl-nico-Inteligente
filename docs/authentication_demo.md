# Autenticación demostrativa

El acceso usa información exclusivamente sintética. Las contraseñas se almacenan con `scrypt` y salt aleatorio; la base nunca guarda texto plano. Las sesiones tienen identificador aleatorio y se cierran explícitamente. Se registran login correcto/fallido, logout, rol y selección de atención, sin contraseña ni relato clínico en el evento de login.

## Paciente

- identificador: `76543210`
- segundo dato: `1999-01-01`

Su sesión queda vinculada a `DEMO_PAT_01` y sólo muestra portal/seguimiento propios.

## Personal sanitario

| Rol | Usuario | Contraseña demo | Establecimiento |
|---|---|---|---|
| Triaje enfermería | `nurse.demo` | `Clinica360-N1!` | `DEMO_FAC_A` |
| Triaje médico | `triage.doctor` | `Clinica360-TD!` | `DEMO_FAC_B` |
| Médico tratante | `attending.demo` | `Clinica360-M1!` | `DEMO_FAC_A` |
| Supervisor | `supervisor.demo` | `Clinica360-S1!` | `DEMO_FAC_A` |
| Administrador | `admin.demo` | `Clinica360-A1!` | `DEMO_FAC_A` |

Son credenciales públicas de validación, no secretos ni autenticación de producción. Ejecute `scripts/create_demo_accounts.py` para recrearlas idempotentemente.

Antes de producción se requieren un proveedor de identidad real, MFA, rotación, bloqueo de intentos, cookies seguras, expiración, autorización en backend y evaluación de privacidad.
