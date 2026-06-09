# Cancelación de Transferencias Pendientes desde App Móvil — v0.1 BORRADOR

## 1. Contexto

**⚠️ BORRADOR v0.1 — Sujeto a revisión humana. No es un documento aprobado.**

**Fecha:** 2025-07-14 | **Estado:** BORRADOR | **Versión:** 0.1

---

### Problema
Los clientes no pueden cancelar desde la app móvil transferencias en estado 'pendiente', obligándoles a contactar con atención al cliente. Esto genera fricción, costes operativos y riesgo de error humano.

### Usuarios objetivo
Clientes bancarios titulares de cuentas con transferencias en estado 'pendiente', operando vía app móvil.

### Valor esperado
Reducir fricción y costes operativos. Mejorar experiencia de usuario con un canal seguro, autenticado y auditable para la autogestión de cancelaciones.

### Alcance funcional
1. Visualización de transferencias en estado 'pendiente'.
2. Flujo de cancelación con autenticación fuerte (SCA/PSD2).
3. Confirmación explícita del usuario.
4. Validación de titularidad de la cuenta de origen.
5. Llamada al backend de transferencias para revocar la operación.
6. Notificación al core bancario del cambio de estado.
7. Registro auditable de la operación.
8. Integración con plataforma de observabilidad.

### Restricciones
- Solo transferencias en estado exactamente 'pendiente' son cancelables.
- Requiere SCA conforme a PSD2 (incluido dynamic linking).
- Usuario debe ser titular verificado de la cuenta de origen.
- Auditoría completa con trazabilidad regulatoria.
- SLAs y contratos de API aún **no definidos** — bloqueante.

### Criterios de aceptación (CA originales)
| ID | Descripción |
|----|-------------|
| CA-01 | Solo se muestra opción de cancelación en transferencias con estado exactamente 'pendiente'. |
| CA-02 | El flujo requiere SCA antes de proceder. |
| CA-03 | Verificación de titularidad antes de ejecutar la cancelación. |
| CA-04 | Confirmación explícita en la app. |
| CA-05 | Consistencia entre backend de transferencias y core bancario. |
| CA-06 | Registro auditable con: usuario, timestamp, ID transferencia, resultado, canal. |
| CA-07 | Mensaje de error claro si la transferencia cambió de estado. |
| CA-08 | Eventos publicados en observabilidad. |
| CA-09 | Resistencia a condiciones de carrera. |

### Criterios de aceptación adicionales (recomendados por revisión de seguridad)
| ID | Descripción |
|----|-------------|
| AC-10 | Autorización backend anti-IDOR: validar que el recurso pertenece al usuario autenticado. |
| AC-11 | Bloqueo atómico de estado antes de ejecutar la cancelación. |
| AC-12 | Compensación ante fallo parcial (patrón Saga). |
| AC-13 | SCA con dynamic linking PSD2 vinculado a la operación específica. |
| AC-14 | Data masking en observabilidad — sin exposición de PII ni datos financieros. |
| AC-15 | Auditoría inmutable con política de retención regulatoria definida. |
| AC-16 | Rate limiting en endpoint de cancelación. |
| AC-17 | Mensajes de error genéricos al usuario — sin fuga de información interna. |

## 2. Arquitectura propuesta

### Estilo arquitectónico
API-first, orientado a servicios, con integración controlada a sistemas internos bancarios.

### Componentes principales
| # | Componente | Rol |
|---|-----------|-----|
| 1 | **App Móvil** | Canal digital: visualización, SCA, confirmación de usuario |
| 2 | **API Gateway / BFF** | Autenticación de sesión, rate limiting, routing |
| 3 | **Servicio de Cancelación** *(nuevo)* | Orquestador central del flujo de cancelación |
| 4 | **Servicio de Identidad / SCA** | Autenticación fuerte, validación de titularidad |
| 5 | **Backend de Transferencias** | Consulta y revocación de transferencias pendientes |
| 6 | **Core Bancario** | Notificación de cambio de estado de la operación |
| 7 | **Servicio de Auditoría** | Registro inmutable de eventos regulatorios |
| 8 | **Plataforma de Observabilidad** | Métricas, trazas distribuidas, alertas |

### Flujo secuencial de alto nivel
```
App Móvil
  → API Gateway / BFF          [autenticación sesión, rate limiting]
    → Servicio de Cancelación  [orquestación]
      → Servicio SCA           [autenticación fuerte + dynamic linking PSD2]
      → Servicio Titularidad   [validación de ownership]
      → Re-check estado        [anti race-condition: locking optimista]
      → Backend Transferencias [revocación atómica]
      → Core Bancario          [notificación cambio de estado]
      → Auditoría (async)      [registro inmutable]
      → Observabilidad (async) [métricas + trazas]
  ← App Móvil                  [confirmación o error genérico]
```

### Integraciones
- **Síncronas:** App↔GW, GW↔SvcCancelación, SvcCancelación↔SCA, ↔Titularidad, ↔BackendTransferencias, ↔CoreBancario.
- **Asíncronas:** SvcCancelación→Auditoría, SvcCancelación→Observabilidad.

### Riesgos arquitectónicos críticos
| ID | Riesgo | Mitigación propuesta |
|----|--------|----------------------|
| R01 | Race condition en estado de transferencia | Locking optimista (ETag/versión) + re-validación de estado justo antes de revocar |
| R02 | Inconsistencia entre Backend de Transferencias y Core Bancario | Patrón Saga con compensación / Outbox pattern |
| R03 | SLAs no definidos | **Bloqueante** para dimensionamiento de timeouts, reintentos y circuit breakers |

### Decisiones arquitectónicas bloqueadas (pendientes de información)
| ID | Decisión bloqueada |
|----|-------------------|
| D01 | SLA del Core Bancario → determina si la notificación puede ser síncrona o debe ser asíncrona con Saga |
| D02 | Capacidades del Backend de Transferencias → soporte de ETag, idempotency keys, versionado |
| D03 | Contrato del Servicio de Identidad/SCA → token binding, TTL, dynamic linking disponible |
| D04 | Topología del canal asíncrono → broker corporativo disponible (Kafka, RabbitMQ, etc.) |
| D05 | Ownership del Servicio de Cancelación → nuevo microservicio vs. extensión de servicio existente |

## 3. Validaciones realizadas

### Criterios de validación funcional y técnica

#### Validaciones de estado
- Solo transferencias con estado exactamente igual a `'pendiente'` son elegibles para cancelación.
- Re-validación de estado en el Servicio de Cancelación inmediatamente antes de ejecutar la revocación (protección ante race conditions).
- Si el estado ha cambiado entre la solicitud y la ejecución, devolver error descriptivo al usuario (mensaje genérico, sin exponer detalles internos).

#### Validaciones de identidad y autorización
- Verificación de sesión activa en API Gateway antes de enrutar la solicitud.
- Validación de titularidad de la cuenta de origen en el Servicio de Identidad.
- Autorización backend anti-IDOR: confirmar que la transferencia pertenece al usuario autenticado antes de cualquier acción.

#### Validaciones de integridad transaccional
- Bloqueo atómico del estado de la transferencia antes de proceder a la revocación.
- En caso de fallo parcial (revocación exitosa pero fallo en notificación al Core Bancario), aplicar mecanismo de compensación (Saga / Outbox).
- Uso de idempotency keys para evitar cancelaciones duplicadas ante reintentos.

#### Validaciones de auditoría
- Todo evento de cancelación (exitoso o fallido) debe registrarse con: usuario, timestamp, ID transferencia, resultado, canal, IP origen, device ID, correlationId.
- Los registros de auditoría deben ser inmutables.
- La política de retención regulatoria debe estar definida (pendiente — ver dudas abiertas).

#### Validaciones de observabilidad
- Publicación de eventos en plataforma de observabilidad para cada cancelación procesada.
- Data masking obligatorio: ningún dato PII ni financiero en claro en trazas o métricas.
- Alertas configuradas para anomalías (tasa de errores, latencia, intentos de abuso).

#### Validaciones de seguridad y resiliencia
- SCA con dynamic linking vinculado a la operación específica (PSD2 Art. 97).
- Rate limiting activo en el endpoint de cancelación (umbral por definir).
- Mensajes de error al usuario siempre genéricos — sin fuga de información técnica o interna.

## 4. Consideraciones de seguridad

### Veredicto de seguridad
**⚠️ needs_review — No apto para avanzar a implementación sin remediar los gaps críticos identificados.**

---

### Hallazgos críticos 🔴 (bloqueantes)
| ID | Hallazgo | Riesgo |
|----|---------|--------|
| HAL-01 | Ausencia de modelo de autorización explícito en backend | IDOR: un usuario podría cancelar transferencias de otro titular |
| HAL-02 | Condiciones de carrera sin mecanismo técnico definido | Locking optimista o pesimista requerido antes de avanzar |
| HAL-03 | SLAs y contratos de API de integraciones no definidos | Bloqueante para dimensionamiento, timeouts y decisiones de resiliencia |
| HAL-04 | Consistencia transaccional entre sistemas no garantizada | Falta patrón Saga o 2PC — riesgo de estados inconsistentes entre Backend y Core |
| HAL-05 | SCA insuficiente para PSD2 sin dynamic linking | La operación no está vinculada criptográficamente a la acción específica |

### Hallazgos medios 🟡 (a resolver antes de go-live)
| ID | Hallazgo | Riesgo |
|----|---------|--------|
| HAL-06 | Schema de auditoría incompleto | Faltan IP origen, device ID, correlationId, inmutabilidad y retención regulatoria |
| HAL-07 | Riesgo de exposición de PII/datos financieros en observabilidad | Falta política de data masking en trazas y métricas |
| HAL-08 | Gestión de errores con potencial fuga de información al cliente | Mensajes de error técnicos no deben exponerse al canal móvil |
| HAL-09 | Ausencia de rate limiting y protección anti-abuso | Riesgo de abuso del endpoint de cancelación |

### Controles de seguridad requeridos
- Autorización backend anti-IDOR en cada operación de cancelación (AC-10).
- Locking atómico de estado previo a cancelación (AC-11).
- Mecanismo de compensación ante fallo parcial (AC-12).
- SCA con dynamic linking PSD2 (AC-13).
- Data masking en todos los canales de observabilidad (AC-14).
- Auditoría inmutable con retención regulatoria (AC-15).
- Rate limiting configurado en API Gateway y/o BFF (AC-16).
- Errores genéricos al usuario en todos los casos de fallo (AC-17).

## 5. Dudas abiertas

- [D01 / HAL-03] ¿Cuál es el SLA del Core Bancario? ¿La notificación puede ser síncrona o debe modelarse como Saga asíncrona con compensación?
- [D02 / HAL-02] ¿El Backend de Transferencias soporta ETag, versionado o idempotency keys para implementar locking optimista y evitar race conditions?
- [D03 / HAL-05] ¿El Servicio de Identidad/SCA actual soporta dynamic linking vinculado a una operación específica, conforme a PSD2 Art. 97?
- [D04] ¿Existe un broker de mensajería corporativo disponible (Kafka, RabbitMQ u otro) para los canales asíncronos de Auditoría y Observabilidad?
- [D05] ¿El Servicio de Cancelación se implementa como nuevo microservicio independiente o como extensión de un servicio existente? ¿Qué equipo es el owner?
- [HAL-06] ¿Cuál es la política de retención regulatoria de registros de auditoría en el banco? ¿Qué plataforma de auditoría corporativa está disponible?
- [HAL-07] ¿Qué plataforma de observabilidad corporativa existe y qué formato de eventos acepta? ¿Tiene capacidades nativas de data masking?
- [Alcance] ¿Cómo se gestiona la cancelación para cuentas compartidas, apoderados o tutores legales? ¿Aplica el mismo flujo de titularidad?

## 6. Próximos pasos

- Revisión humana de la especificación.
- Validación con arquitectura.
- Validación con seguridad.
- Refinamiento antes de crear épica/historia técnica.
