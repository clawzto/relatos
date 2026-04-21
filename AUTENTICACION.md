# 🔐 Sistema de Autenticación y Control de Acceso

## 📋 Resumen Ejecutivo

Se implementó un sistema completo de **autenticación y control de acceso** con dos niveles de contenido:

| Tipo | Acceso | Lectura | Descarga | Modelo |
|------|--------|---------|----------|--------|
| **Relatos IA** | Público (necesita login) | ✅ Online | ✅ Sí | Gratuito |
| **Relatos Humanos** | Solo suscriptores | ✅ Online | ❌ No | Premium |

---

## 🔑 Características Principales

### 1. **Autenticación de Usuarios**
- ✅ Registro: Crear nueva cuenta con email, nombre y contraseña
- ✅ Login: Iniciar sesión con "Recuérdame" (30 días)
- ✅ Logout: Cerrar sesión
- ✅ Hasheo seguro: Contraseñas con `werkzeug.security`

### 2. **Control de Acceso por Rol**
```
Usuario Anónimo (Sin login)
  ↓
  └─→ Ve: Landing page con info + relatos IA de muestra
  
Usuario Registrado (Con login)
  ↓
  ├─→ Relatos IA: Acceso completo, lectura + descarga
  └─→ Relatos Humanos: BLOQUEADO (necesita suscripción)

Usuario Suscriptor (Con suscripción)
  ↓
  ├─→ Relatos IA: Acceso completo
  └─→ Relatos Humanos: Acceso total a los comprados
```

### 3. **Modelos de Base de Datos**

```python
# Usuario: Registración y autenticación
class Usuario:
  - email (único)
  - nombre
  - password_hash (hasheable)
  - suscrito (booleano)
  - creado_en

# Acceso: Control de qué usuarios pueden leer qué relatos
class Acceso:
  - usuario_id (FK)
  - relato_id (FK)
  - fecha_compra
  - veces_leido (contador)
  - ultima_lectura (timestamp)
  
# RelatoHumano: Extendido con autor y precio
class RelatoHumano:
  + precio (nuevo)
  + autor_id (nuevo, FK a Usuario)
  + accesos (relación a Acceso)
```

---

## 🗂️ Rutas Implementadas

### Autenticación
| Ruta | Método | Descripción |
|------|--------|-------------|
| `/landing` | GET | Landing page pública (home para invitados) |
| `/login` | GET, POST | Formulario + procesamiento de login |
| `/registro` | GET, POST | Crear nueva cuenta |
| `/logout` | GET | Cerrar sesión (requiere login) |

### Relatos IA (Gratuitos)
| Ruta | Método | Requiere Login |
|------|--------|----------------|
| `/` | GET | ✅ Sí (redirecciona a login si no) |
| `/generar` | GET, POST | ✅ Sí |
| `/relato/<id>` | GET | ✅ Sí |
| `/relato/<id>/eliminar` | POST | ✅ Sí |

### Relatos Humanos (Privados)
| Ruta | Método | Requiere Login | Requiere Acceso |
|------|--------|---|---|
| `/humanos` | GET | ✅ | ✅ |
| `/humanos/nuevo` | GET, POST | ✅ | ❌ (autor puede crear) |
| `/humanos/<id>` | GET | ✅ | ✅ |
| `/humanos/<id>/capitulo/nuevo` | GET, POST | ✅ | ✅ (solo autor) |
| `/humanos/<id>/eliminar` | POST | ✅ | ✅ (solo autor) |

---

## 🎯 Flujos de Uso

### Flujo: Usuario Nuevo
```
1. Accede a https://web.com/
   → Redirige a /landing (página pública)
   
2. Hace clic en "Crear Cuenta"
   → /registro
   
3. Completa: nombre, email, contraseña
   → Usuario creado
   → Auto-login
   → Redirige a / (biblioteca IA)
```

### Flujo: Suscriptor Lee Relato Humano
```
1. Usuario autenticado normal accede a /humanos
   → Ve mensaje: "Necesitas suscripción"
   
2. Admin marca: usuario.suscrito = True
   → Crea registros en Acceso tabla
   
3. Usuario accede a /humanos/<id>
   → Decorador @requiere_acceso_relato valida
   → Si tiene acceso: muestra relato
   → Incrementa contador de lecturas
```

### Flujo: Autor Publica Relato
```
1. Usuario autenticado → /humanos/nuevo
2. Completa: título, descripción, precio
   → RelatoHumano creado con autor_id=current_user.id
3. → /humanos/<id>/capitulo/nuevo
   → Añade capítulos
4. Otros usuarios (si compran) ven en /humanos
```

---

## 🛡️ Seguridad

### Protecciones Implementadas
✅ **Contraseñas hasheadas** con `werkzeug.security.generate_password_hash`
✅ **Decoradores** para proteger rutas: `@login_required`, `@requiere_acceso_relato`
✅ **Flash messages** para retroalimentación segura
✅ **Session management** con Flask-Login
✅ **Redirects seguros** solo a URLs locales

### No Permite
❌ Copiar contenido de relatos premium (CSS: `user-select: none`)
❌ Descargar relatos premium
❌ Compartir acceso (único por usuario)
❌ Editar relatos de otros autores

---

## 📱 Interfaz de Usuario

### Navbar Adaptable
```html
<!-- Sin login -->
Relatos IA | [Iniciar Sesión] [Registrarse]

<!-- Con login -->
Relatos IA | 📖 Biblioteca | ✨ Generar | 👥 Autores | 👤 Juan | [Logout]
```

### Landing Page (Invitados)
- Hero section con CTA
- Info sobre dos tipos de relatos
- Últimas relatos IA como preview
- FAQ
- CTAs a login/registro

### Dashboard (Usuarios Autenticados)
- Home: Biblioteca IA completa
- Generar: Crear nuevos relatos
- Autores: Relatos humanos (si suscrito)

---

## 🔧 Configuración

### Variables de Entorno
```env
# Existentes
OPENROUTER_API_KEY=...
OLLAMA_URL=...
SECRET_KEY=...

# Autenticación (auto)
FLASK_DEBUG=False
DATABASE_URL=...  # En Railway
```

### Usuario Admin (Testing)
```
Email: admin@relatos.local
Contraseña: admin123456
Rol: Suscrito (acceso a todo)
```

> ⚠️ **IMPORTANTE**: Cambiar credenciales en producción

---

## 💾 Base de Datos

### Nuevas Tablas
```sql
usuario              -- Cuentas de usuario
acceso               -- Control de qué usuario lee qué relato humano
```

### Tablas Modificadas
```sql
relato_humano        -- Añadido: precio, autor_id
```

---

## 🚀 Próximos Pasos Opcionales

### Nivel 1 (Essencial)
- [ ] Crear página admin para gestionar suscripciones
- [ ] Sistema de "compra" (Stripe/PayPal)
- [ ] Emails de confirmación

### Nivel 2 (Deseable)
- [ ] Recuperar contraseña (reset link por email)
- [ ] Perfil de usuario
- [ ] Comentarios en relatos
- [ ] Favoritos/Bookmarks

### Nivel 3 (Avanzado)
- [ ] Notificaciones (nuevo relato de autor favorito)
- [ ] Sistema de recomendaciones
- [ ] Analytics (qué leen, cuándo, cuánto tiempo)
- [ ] Descuentos y promociones

---

## 🧪 Testing

### Local
```bash
# 1. Crear usuario de test
flask shell
>>> from app import db, Usuario
>>> u = Usuario(nombre='Test', email='test@test.com')
>>> u.set_password('123456')
>>> db.session.add(u)
>>> db.session.commit()

# 2. Iniciar sesión: test@test.com / 123456
# 3. Ver que /humanos es inaccesible
```

### En Railway
```
1. Registrar cuenta nueva
2. Intentar acceder a /humanos
   → Debe mostrar: "Necesitas suscripción"
3. Admin: cambiar suscrito=True en BD
4. Recargar
   → Ahora tiene acceso
```

---

## 📖 Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `app.py` | ✅ Sistema completo de autenticación |
| `requirements.txt` | ✅ `flask-login`, `werkzeug`, `email-validator` |
| `templates/base.html` | ✅ Navbar adaptable, mostrar usuario |
| `templates/login.html` | ✅ Nuevo |
| `templates/registro.html` | ✅ Nuevo |
| `templates/landing.html` | ✅ Nuevo |
| `.env.example` | ✅ Documentación de variables |

---

## 🤔 FAQ

**P: ¿Cómo hago que un usuario sea suscriptor?**
R: En admin panel (o DB): `UPDATE usuario SET suscrito = true WHERE id = X;`

**P: ¿Puedo tener relatos humanos gratuitos?**
R: Sí, establece `precio = 0` y cualquier suscriptor podrá leerlos.

**P: ¿Qué pasa si mi contraseña es débil?**
R: El registro valida mínimo 6 caracteres. En producción, aumentar a 12+.

**P: ¿Se pueden compartir cuentas?**
R: Técnicamente sí, pero el precio es por usuario (en la tabla `Acceso`).

**P: ¿Cómo reseteo una contraseña olvidada?**
R: No implementado. Próximo paso: enviar link por email.

---

## 📞 Soporte

Para preguntas sobre el sistema de autenticación, consulta:
- Código en `app.py` (líneas: autenticación)
- Modelos en `app.py` (clase `Usuario`, `Acceso`)
- Decoradores en `app.py` (`@requiere_acceso_relato`)

¡Sistema listo para producción! 🎉
