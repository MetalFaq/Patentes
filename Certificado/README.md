# Certificados para Autenticación de SharePoint (Microsoft Graph)

Esta carpeta está destinada a almacenar el certificado digital (`.pfx`) necesario para autenticar la aplicación registrada en Microsoft Entra ID (Azure AD) contra Microsoft Graph API.

## Instrucciones para el desarrollador:

1. **Generación / Obtención del Certificado:**
   - Genere un certificado X.509 auto-firmado o emitido por su Autoridad Certificadora interna.
   - Cargue la clave pública (`.cer` o `.crt`) en el registro de la aplicación en el portal de Microsoft Entra ID (*App Registrations -> Certificates & secrets -> Certificates*).
   - Exporte la clave privada en formato PKCS#12 (`.pfx`) protegido por contraseña.

2. **Ubicación del archivo:**
   - Coloque el archivo `.pfx` en este directorio con el nombre configurado en `.env`:
     ```bash
     Certificado/agente_patentes_cert.pfx
     ```

3. **Configuración en `.env`:**
   - Defina las variables correspondientes:
     ```env
     SHAREPOINT_CERT_PFX_PATH=./Certificado/agente_patentes_cert.pfx
     SHAREPOINT_CERT_PFX_PASSWORD=su_password_pfx
     SHAREPOINT_CERT_THUMBPRINT=HUELLA_DIGITAL_DEL_CERTIFICADO_SHA1
     ```

> [!WARNING]
> Los archivos `.pfx`, `.pem` y `.key` están estrictamente ignorados por `.gitignore` y **NUNCA** deben ser commiteados al repositorio.
