# Acceso y pruebas

Todas las identidades de esta guía son sintéticas y están limitadas al entorno local.

## Pacientes existentes

| DNI | Fecha de nacimiento | Establecimiento |
|---|---|---|
| `76543210` | `1999-01-01` | Centro Andino |
| `87654321` | `1990-02-02` | Policlínico Costa |
| `11223344` | `1985-03-03` | Centro Andino |

## Personal sanitario

| Perfil | Usuario | Contraseña | Establecimiento |
|---|---|---|---|
| Enfermería | `nurse.demo` | `Clinica360-N1!` | Centro Andino |
| Médico de triaje | `triage.doctor` | `Clinica360-TD!` | Policlínico Costa |
| Médico tratante | `attending.demo` | `Clinica360-M1!` | Centro Andino |
| Supervisor | `supervisor.demo` | `Clinica360-S1!` | Centro Andino |
| Administrador | `admin.demo` | `Clinica360-A1!` | Centro Andino |

Son contraseñas locales de acceso incluidas deliberadamente para la validación. No reutilice contraseñas reales.

## Paciente nuevo

1. Abra **Registrar nuevo paciente**.
2. Use un DNI sintético nuevo de ocho dígitos.
3. Complete nombres, apellidos, nacimiento, sexo registrado, teléfono, emergencia, aseguramiento y establecimiento.
4. Agregue opcionalmente correo, dirección, alergias, medicamentos y antecedentes.
5. Confirme consentimiento y pulse **Crear registro seguro**.
6. Ingrese como paciente existente con el DNI y la fecha registrada.

## Matriz de recorrido

1. Caso respiratorio: voz o texto; confirme transcripción y bandera prioritaria.
2. Caso general: dolor abdominal, cefalea, lesión o consulta sin dolor.
3. Conversación: responda, use **No sé** y compruebe el motivo del nulo.
4. Fallback: detenga Ollama y verifique que el sistema informe respaldo determinista.
5. Historia: abra **Mi historia clínica**, filtre fecha y establecimiento.
6. Triaje: registre signos, revise prioridad, acepte/modifique/escale/reevalúe con justificación.
7. Médico: revise historia, RAG, pendientes, registro profesional y gráficos descriptivos.
8. Administrador: inspeccione **Estructura de datos**; no deben aparecer secretos.
9. Base de datos: ejecute `scripts/export_schema.py` y `scripts/inspect_database.py`.

## Verificación automática

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\01_PROBAR_TODO.bat
```
