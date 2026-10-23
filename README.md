# Voice Language

Traductor de voz por turnos para escritorio. Hablas en un idioma, la app transcribe,
traduce y reproduce la traducción con voz. Después puedes contestar en el otro idioma
y el proceso se invierte.

```
micrófono -> WAV -> transcripción -> traducción -> voz sintetizada -> altavoz
```

Hecho con [Flet](https://flet.dev) 1.0 sobre Flutter, y la API de OpenAI para las tres
etapas (STT, traducción y TTS).

## Requisitos

- Windows, macOS o Linux con micrófono y altavoces.
- [uv](https://docs.astral.sh/uv/) (gestiona Python 3.12 por ti).
- Una API key de OpenAI con crédito.

## Puesta en marcha

```powershell
uv sync
uv run flet run main.py
```

La primera ejecución descarga el cliente de escritorio de Flet. Después abre
**Ajustes** (icono de engranaje), pega tu API key y guarda.

Para desarrollo puedes evitar el diálogo con una variable de entorno:

```powershell
$env:OPENAI_API_KEY = "sk-..."
uv run flet run main.py
```

La key nunca se escribe en el repositorio. Si la guardas desde Ajustes, va a tu
carpeta de configuración de usuario (`platformdirs`), en texto plano: es un
trade-off aceptable para una app local, no para una app distribuida. El
endurecimiento pendiente es usar `keyring` del sistema.

## Uso

1. Elige **Idioma A** e **Idioma B**.
2. Pulsa **Hablar en {idioma}** en el panel izquierdo, habla y vuelve a pulsar
   (**Detener**) para procesar. El botón cambia a Detener mientras graba.
3. El texto original aparece en su panel, la traducción en el otro y el audio se
   reproduce solo.
4. Para contestar en el otro idioma, usa el micrófono del panel derecho.
5. `⇄` intercambia los idiomas; el icono de repetir vuelve a reproducir el último audio.

Cada turno admite como máximo 60 segundos. La grabación se detiene sola al llegar
al límite.

## Modelos

Los valores por defecto están en `Ajustes` y se pueden cambiar sin tocar código:

| Etapa | Modelo por defecto |
|---|---|
| Transcripción | `gpt-4o-mini-transcribe` |
| Traducción | `gpt-4o-mini` |
| Voz | `gpt-4o-mini-tts` |

Los nombres de modelo cambian con el tiempo. Si OpenAI devuelve un error de modelo,
cámbialo en Ajustes. La traducción usa `temperature` por defecto y un prompt cerrado:
solo traduce, no responde preguntas ni añade comentarios.

Orientación de coste: el gasto dominante es la voz (TTS), seguido de la
transcripción; la traducción de frases cortas es despreciable. Confirma precios en
el panel de OpenAI antes de un uso intensivo.

## Arquitectura

Puertos y adaptadores para que el motor sea sustituible:

```
src/voice_language/
  core/
    models.py        Language, PipelineResult
    ports.py         SpeechToText, Translator, TextToSpeech (Protocols)
    pipeline.py      orquesta STT -> MT -> TTS y mide cada etapa
    languages.py     catálogo de idiomas y voces
    errors.py        errores con mensaje apto para UI
  adapters/
    openai_engine.py un adaptador que implementa los tres puertos
  services/
    audio.py         grabadora WAV y reproductor MP3 de Flet
    settings.py      ajustes persistidos en la carpeta del usuario
  ui/
    home.py          pantalla principal y máquina de estados
  app.py             composición y ventana
```

El SDK de OpenAI es síncrono, así que el pipeline lo ejecuta con
`asyncio.to_thread`: el hilo de UI de Flet nunca se bloquea. Cambiar a un motor
local (faster-whisper + NLLB + Piper) es escribir otro objeto que cumpla los tres
protocolos y cambiar la composición en `HomeView._load_engine`.

Cada respuesta incluye los tiempos de STT, traducción y TTS, visibles en la barra
de estado. Si un turno tarda demasiado, ahí se ve qué etapa es el cuello de botella.

## Tests y diagnóstico

```powershell
uv run pytest -q          # pipeline y ajustes con adaptadores falsos, sin red
uv run ruff check .
uv run ruff format --check .

# Comprueba permiso de micrófono, soporte WAV y dispositivos (no graba)
uv run flet run -n scripts/check_services.py

# Prueba la cadena completa contra OpenAI (requiere OPENAI_API_KEY)
uv run python scripts/smoke_api.py
```

`scripts/smoke_api.py` sintetiza una frase en español, la transcribe, la traduce al
inglés, sintetiza el resultado y lo traduce de vuelta. Si eso pasa, las dos
direcciones funcionan.

## Empaquetado

```powershell
uv run flet build windows
```

Necesita Flutter (el CLI de Flet lo aporta) y las herramientas de compilación de
Windows. Para Android/iOS hay que declarar el permiso de micrófono en el build:

```powershell
uv run flet build apk --permissions microphone
```

La app está pensada para ejecutarse en local con tu key. No distribuyas un build con
una key embebida.

## Siguientes pasos naturales

1. Streaming de transcripción y traducción por frases para bajar la latencia.
2. Detección de idioma con `whisper-1` + `verbose_json` para el modo automático.
3. Adaptador local para uso sin conexión.
4. Historial de turnos exportable.
5. `keyring` para la API key.
