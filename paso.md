# Guía paso a paso para correr el programa

Sigue estos pasos exactamente en orden.

## 1. Abrir la carpeta del proyecto
Abre la carpeta del proyecto en Visual Studio Code o en tu terminal.

## 2. Verificar que Python esté instalado
Ejecuta este comando en la terminal:

```bash
python --version
```

Si no aparece la versión de Python, instala Python 3.10 o superior.

## 3. Entrar a la carpeta del proyecto
Si estás en otra carpeta, entra a la carpeta del proyecto con:

```bash
cd /home/yanfranko/Escritorio/Triaje-360-Auditor-Cl-nico-Inteligente
```

## 4. Crear un entorno virtual
Ejecuta:

```bash
python -m venv .venv
```

## 5. Activar el entorno virtual
En Linux o Mac:

```bash
source .venv/bin/activate
```

En Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

## 6. Actualizar pip
Ejecuta:

```bash
python -m pip install --upgrade pip
```

## 7. Instalar las dependencias del proyecto
Ejecuta:

```bash
pip install -r requirements.txt
```

Si el proyecto usa dependencias adicionales de voz, también puedes instalar:

```bash
pip install -r requirements-voice.txt
```

## 8. Verificar que las dependencias se instalaron
Puedes revisar que todo quedó bien instalado con:

```bash
pip list
```

## 9. Ejecutar la aplicación
Para iniciar el programa, ejecuta:

```bash
python app.py
```

## 10. Esperar a que se abra la interfaz
Si el programa tiene interfaz gráfica o web, se abrirá en tu navegador o en una ventana local.

## 11. Si el programa no inicia
Si aparece algún error, revisa lo siguiente:

- Asegúrate de haber activado el entorno virtual.
- Asegúrate de haber instalado todas las dependencias.
- Revisa si faltan variables de entorno o archivos de configuración.

## 12. Detener la aplicación
Si necesitas cerrar la aplicación, presiona:

```bash
Ctrl + C
```

## 13. Volver a ejecutar el programa más tarde
Cuando quieras volver a correrlo, solo repite estos pasos:

```bash
cd /home/yanfranko/Escritorio/Triaje-360-Auditor-Cl-nico-Inteligente
source .venv/bin/activate
python app.py
```
