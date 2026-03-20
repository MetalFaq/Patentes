"""Cliente SharePoint/Graph para sincronizar PDFs hacia un mirror local.

Instrucciones:
- Usa autenticacion app-only con Microsoft Graph y certificado PFX.
- Primero valida conectividad por GETs simples antes de indexar.
- Mantene este modulo enfocado en sincronizacion y metadatos remotos.
- Nunca registres secretos, passphrases ni tokens.
- El cache local es el contrato hacia el indexador actual del proyecto.
- El resumen de sync debe servir tambien como telemetria operativa:
  requests Graph, descargas, bytes transferidos y reuse del cache.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote, urlparse
import json
import logging
import time

import httpx

from agent.config import Settings, SharePointSettings

try:
    import msal
except ImportError as exc:  # pragma: no cover - depende de entorno local
    raise ImportError("Se requiere msal para usar SharePoint. Instala con: pip install msal") from exc


logger = logging.getLogger(__name__)


class SharePointConfigurationError(RuntimeError):
    """Error de configuracion para la fuente SharePoint."""


class SharePointGraphError(RuntimeError):
    """Error al interactuar con Microsoft Graph."""


@dataclass(frozen=True)
class SharePointSiteInfo:
    """Datos basicos del site objetivo en SharePoint."""

    site_id: str
    name: str
    web_url: str


@dataclass(frozen=True)
class SharePointDriveInfo:
    """Metadatos minimos de una biblioteca/drive de SharePoint."""

    drive_id: str
    name: str
    web_url: str


@dataclass(frozen=True)
class SharePointFile:
    """Archivo PDF listado desde la carpeta objetivo de SharePoint."""

    item_id: str
    name: str
    relative_path: str
    etag: Optional[str]
    last_modified: Optional[str]
    size: int
    web_url: Optional[str]
    drive_id: str


@dataclass
class SharePointTelemetry:
    """Contadores operativos para monitorear syncs de SharePoint.

    No representa costos monetarios directos de Microsoft Graph. Sirve para
    dimensionar volumen operativo: requests, descargas, bytes y throttling.
    """

    token_acquisitions: int = 0
    graph_json_requests: int = 0
    graph_download_requests: int = 0
    throttled_responses: int = 0
    bytes_downloaded: int = 0
    status_codes: Dict[str, int] = field(default_factory=dict)


class SharePointClient:
    """Cliente de alto nivel para Graph orientado a PDFs del agente.

    Flujo esperado:
    - autenticarse contra Graph
    - resolver site y drive
    - listar la carpeta de PDFs
    - sincronizar al cache local
    - dejar el cache listo para `PlateIndex`
    """

    def __init__(self, settings: SharePointSettings):
        self.settings = settings
        self.cache_dir = settings.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.cache_dir / ".manifest.json"
        self._client = httpx.Client(
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
        )
        self._token: Optional[str] = None
        self._site_info: Optional[SharePointSiteInfo] = None
        self._drive_info: Optional[SharePointDriveInfo] = None
        self._telemetry = SharePointTelemetry()

    @classmethod
    def from_settings(cls, settings: Settings) -> "SharePointClient":
        """Construye el cliente a partir de la configuracion global del proyecto."""
        return cls(settings.sharepoint)

    def close(self) -> None:
        """Cierra el cliente HTTP subyacente."""
        self._client.close()

    def __enter__(self) -> "SharePointClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def validate_configuration(self) -> None:
        """Valida la configuracion minima para usar SharePoint."""
        required_fields = {
            "SHAREPOINT_TENANT_ID": self.settings.tenant_id,
            "SHAREPOINT_CLIENT_ID": self.settings.client_id,
            "SHAREPOINT_SITE_URL": self.settings.site_url,
            "SHAREPOINT_LIBRARY_NAME": self.settings.library_name,
            "SHAREPOINT_FOLDER_PATH": self.settings.folder_path,
            "SHAREPOINT_CERT_PFX_PATH": str(self.settings.cert_pfx_path or ""),
            "SHAREPOINT_CERT_PFX_PASSWORD": self.settings.cert_pfx_password,
        }
        missing = [name for name, value in required_fields.items() if not value]
        if missing:
            raise SharePointConfigurationError(
                "Faltan variables SharePoint: " + ", ".join(sorted(missing))
            )
        if not self.settings.cert_pfx_path or not self.settings.cert_pfx_path.exists():
            raise SharePointConfigurationError(
                f"No existe el certificado PFX: {self.settings.cert_pfx_path}"
            )

    def _authority(self) -> str:
        self.validate_configuration()
        return f"https://login.microsoftonline.com/{self.settings.tenant_id}"

    def _reset_telemetry(self) -> None:
        """Resetea contadores para medir una operacion puntual."""
        self._telemetry = SharePointTelemetry()

    def _track_status(self, status_code: int) -> None:
        """Acumula codigos HTTP observados durante la corrida actual."""
        key = str(status_code)
        self._telemetry.status_codes[key] = self._telemetry.status_codes.get(key, 0) + 1
        if status_code == 429:
            self._telemetry.throttled_responses += 1

    def current_telemetry(self) -> Dict[str, Any]:
        """Devuelve la telemetria actual en formato JSON-friendly."""
        graph_requests = (
            self._telemetry.graph_json_requests + self._telemetry.graph_download_requests
        )
        bytes_downloaded_mb = round(self._telemetry.bytes_downloaded / (1024 * 1024), 3)
        return {
            "token_acquisitions": self._telemetry.token_acquisitions,
            "graph_json_requests": self._telemetry.graph_json_requests,
            "graph_download_requests": self._telemetry.graph_download_requests,
            "graph_requests_total": graph_requests,
            "throttled_responses": self._telemetry.throttled_responses,
            "bytes_downloaded": self._telemetry.bytes_downloaded,
            "bytes_downloaded_mb": bytes_downloaded_mb,
            "status_codes": dict(sorted(self._telemetry.status_codes.items())),
        }

    def _acquire_token(self) -> str:
        """Obtiene un token app-only para Microsoft Graph."""
        if self._token:
            return self._token

        self._telemetry.token_acquisitions += 1
        app = msal.ConfidentialClientApplication(
            client_id=self.settings.client_id,
            authority=self._authority(),
            client_credential={
                "private_key_pfx_path": str(self.settings.cert_pfx_path),
                "passphrase": self.settings.cert_pfx_password,
            },
        )
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        token = result.get("access_token")
        if not token:
            message = result.get("error_description") or result.get("error") or "sin detalle"
            raise SharePointGraphError(f"No se pudo obtener token Graph: {message}")
        self._token = token
        return token

    def _request(
        self,
        method: str,
        path_or_url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ejecuta una llamada JSON a Graph con autenticacion bearer."""
        token = self._acquire_token()
        url = (
            path_or_url
            if path_or_url.startswith("http")
            else f"{self.settings.graph_base_url}/{path_or_url.lstrip('/')}"
        )
        response = self._client.request(
            method,
            url,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        self._telemetry.graph_json_requests += 1
        self._track_status(response.status_code)
        if response.status_code >= 400:
            raise SharePointGraphError(
                f"Graph {response.status_code} en {url}: {response.text}"
            )
        if not response.content:
            return {}
        return response.json()

    def _paginate(
        self,
        path_or_url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Recorre paginas Graph que usan `@odata.nextLink`."""
        items: List[Dict[str, Any]] = []
        next_url: Optional[str] = path_or_url
        current_params = params
        while next_url:
            payload = self._request("GET", next_url, params=current_params)
            items.extend(payload.get("value", []))
            next_url = payload.get("@odata.nextLink")
            current_params = None
        return items

    def get_site_info(self) -> SharePointSiteInfo:
        """Resuelve el site configurado a partir de la URL de SharePoint."""
        if self._site_info is not None:
            return self._site_info
        self.validate_configuration()

        parsed = urlparse(self.settings.site_url or "")
        if not parsed.scheme or not parsed.netloc or not parsed.path:
            raise SharePointConfigurationError(
                "SHAREPOINT_SITE_URL no tiene un formato valido"
            )

        site_path = quote(parsed.path.lstrip("/"), safe="/")
        payload = self._request("GET", f"/sites/{parsed.netloc}:/{site_path}")
        self._site_info = SharePointSiteInfo(
            site_id=payload["id"],
            name=payload.get("name", ""),
            web_url=payload.get("webUrl", self.settings.site_url or ""),
        )
        return self._site_info

    def list_drives(self) -> List[SharePointDriveInfo]:
        """Lista drives/bibliotecas disponibles en el site objetivo."""
        site = self.get_site_info()
        drives = self._paginate(f"/sites/{site.site_id}/drives")
        return [
            SharePointDriveInfo(
                drive_id=item["id"],
                name=item.get("name", ""),
                web_url=item.get("webUrl", ""),
            )
            for item in drives
        ]

    @staticmethod
    def _normalize_name(value: str) -> str:
        return " ".join((value or "").strip().lower().split())

    @classmethod
    def _drive_aliases(cls, value: str) -> set[str]:
        """Devuelve alias razonables para bibliotecas comunes de SharePoint.

        SharePoint suele exponer la biblioteca por URL como `Shared Documents`,
        mientras que el nombre real del drive en Graph puede figurar como
        `Documents` o incluso `Documentos` segun idioma/tenant.
        """
        normalized = cls._normalize_name(value)
        aliases = {normalized}
        shared_variants = {"shared documents", "documents", "documentos"}
        if normalized in shared_variants:
            aliases.update(shared_variants)
        return aliases

    def get_drive_info(self) -> SharePointDriveInfo:
        """Resuelve la biblioteca configurada contra la lista real de drives."""
        if self._drive_info is not None:
            return self._drive_info

        aliases = self._drive_aliases(self.settings.library_name or "")

        for drive in self.list_drives():
            if self._normalize_name(drive.name) in aliases:
                self._drive_info = drive
                return drive

        available = ", ".join(sorted(drive.name for drive in self.list_drives()))
        raise SharePointGraphError(
            "No se encontro la biblioteca SharePoint configurada. "
            f"Buscada: {self.settings.library_name}. Disponibles: {available}"
        )

    def list_folder_children(self, folder_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista hijos inmediatos de la carpeta objetivo."""
        drive = self.get_drive_info()
        relative = (folder_path or self.settings.folder_path or "").strip("/").replace("\\", "/")
        encoded = quote(relative, safe="/")
        return self._paginate(f"/drives/{drive.drive_id}/root:/{encoded}:/children")

    def iter_folder_pdfs(
        self,
        *,
        limit: Optional[int] = None,
    ) -> Iterable[SharePointFile]:
        """Recorre recursivamente la carpeta objetivo y devuelve solo PDFs."""
        drive = self.get_drive_info()
        base_path = (self.settings.folder_path or "").strip("/").replace("\\", "/")
        pending: List[tuple[str, str]] = [("", base_path)]
        yielded = 0

        while pending:
            relative_prefix, remote_path = pending.pop(0)
            for item in self.list_folder_children(remote_path):
                name = item.get("name", "")
                current_relative = (
                    str(PurePosixPath(relative_prefix) / name) if relative_prefix else name
                )
                if item.get("folder"):
                    pending.append((current_relative, f"{remote_path}/{name}".strip("/")))
                    continue
                if not name.lower().endswith(".pdf"):
                    continue
                yielded += 1
                yield SharePointFile(
                    item_id=item["id"],
                    name=name,
                    relative_path=current_relative,
                    etag=item.get("eTag"),
                    last_modified=item.get("lastModifiedDateTime"),
                    size=int(item.get("size", 0)),
                    web_url=item.get("webUrl"),
                    drive_id=drive.drive_id,
                )
                if limit is not None and yielded >= limit:
                    return

    def download_file(self, file_info: SharePointFile, destination: Path) -> None:
        """Descarga el contenido de un item PDF a disco."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        token = self._acquire_token()
        url = (
            f"{self.settings.graph_base_url}/drives/{file_info.drive_id}/items/"
            f"{file_info.item_id}/content"
        )
        response = self._client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )
        self._telemetry.graph_download_requests += 1
        self._track_status(response.status_code)
        if response.status_code >= 400:
            raise SharePointGraphError(
                f"No se pudo descargar {file_info.relative_path}: "
                f"{response.status_code} {response.text}"
            )
        self._telemetry.bytes_downloaded += len(response.content)
        destination.write_bytes(response.content)

    def _load_manifest(self) -> Dict[str, Any]:
        if not self.manifest_path.exists():
            return {"items": {}}
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning(
                "Manifest SharePoint invalido en %s; se recreara",
                self.manifest_path,
            )
            return {"items": {}}

    def _save_manifest(self, manifest: Dict[str, Any]) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    @staticmethod
    def _safe_local_path(cache_dir: Path, relative_path: str) -> Path:
        parts = [part for part in PurePosixPath(relative_path).parts if part not in {"", "."}]
        if any(part == ".." for part in parts):
            raise SharePointGraphError(f"Ruta remota invalida: {relative_path}")
        return cache_dir.joinpath(*parts)

    def sync_folder_to_cache(
        self,
        *,
        force: bool = False,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Sincroniza PDFs de SharePoint hacia el cache local.

        Devuelve un resumen JSON-friendly con:
        - totales de archivos encontrados/descargados/omitidos/eliminados
        - tiempo total
        - telemetria basica de requests y bytes
        - detalle por archivo
        - rutas locales sincronizadas
        """
        start = time.perf_counter()
        self._reset_telemetry()
        manifest = self._load_manifest()
        manifest_items = manifest.setdefault("items", {})

        files = list(self.iter_folder_pdfs(limit=limit))
        remote_ids = {file_info.item_id for file_info in files}
        sync_details: List[Dict[str, Any]] = []
        local_paths: List[str] = []
        downloaded = 0
        skipped = 0
        deleted = 0
        changed_local_paths: List[str] = []
        deleted_relative_paths: List[str] = []

        site = self.get_site_info()
        drive = self.get_drive_info()
        logger.info(
            "Sincronizando SharePoint | site=%s | drive=%s | folder=%s | archivos=%s",
            site.name or site.site_id,
            drive.name,
            self.settings.folder_path,
            len(files),
        )

        for file_info in files:
            item_start = time.perf_counter()
            local_path = self._safe_local_path(self.cache_dir, file_info.relative_path)
            previous = manifest_items.get(file_info.item_id)
            if previous:
                old_relative = previous.get("relative_path")
                if old_relative and old_relative != file_info.relative_path:
                    old_path = self._safe_local_path(self.cache_dir, old_relative)
                    if old_path.exists() and old_path != local_path:
                        old_path.unlink()

            should_download = (
                force
                or previous is None
                or not local_path.exists()
                or previous.get("etag") != file_info.etag
                or previous.get("last_modified") != file_info.last_modified
                or int(previous.get("size", -1)) != file_info.size
            )

            if should_download:
                self.download_file(file_info, local_path)
                downloaded += 1
                status = "downloaded"
                changed_local_paths.append(str(local_path))
            else:
                skipped += 1
                status = "skipped"

            manifest_items[file_info.item_id] = {
                "relative_path": file_info.relative_path,
                "etag": file_info.etag,
                "last_modified": file_info.last_modified,
                "size": file_info.size,
                "web_url": file_info.web_url,
                "name": file_info.name,
                "drive_id": file_info.drive_id,
            }
            local_paths.append(str(local_path))
            sync_details.append(
                {
                    "relative_path": file_info.relative_path,
                    "status": status,
                    "elapsed_seconds": round(time.perf_counter() - item_start, 3),
                    "size": file_info.size,
                    "etag": file_info.etag,
                }
            )

        if limit is None:
            stale_ids = [item_id for item_id in manifest_items if item_id not in remote_ids]
            for item_id in stale_ids:
                stale = manifest_items.pop(item_id)
                relative_path = stale.get("relative_path")
                if relative_path:
                    stale_path = self._safe_local_path(self.cache_dir, relative_path)
                    if stale_path.exists():
                        stale_path.unlink()
                        deleted += 1
                        deleted_relative_paths.append(relative_path)

        manifest.update(
            {
                "site_url": self.settings.site_url,
                "library_name": drive.name,
                "folder_path": self.settings.folder_path,
                "site_id": site.site_id,
                "drive_id": drive.drive_id,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        self._save_manifest(manifest)

        telemetry = self.current_telemetry()
        report = {
            "source": "sharepoint",
            "site_url": self.settings.site_url,
            "drive_name": drive.name,
            "folder_path": self.settings.folder_path,
            "files_found": len(files),
            "downloaded": downloaded,
            "skipped": skipped,
            "deleted": deleted,
            "sync_time_seconds": round(time.perf_counter() - start, 3),
            "cache_hit_ratio": round((skipped / len(files)), 3) if files else 0.0,
            "telemetry": telemetry,
            "details": sync_details,
            "local_paths": local_paths,
            "changed_local_paths": changed_local_paths,
            "deleted_relative_paths": deleted_relative_paths,
        }
        logger.info(
            "Sync SharePoint finalizado | encontrados=%s | descargados=%s | omitidos=%s | eliminados=%s | requests=%s | descargas=%s | bytes_mb=%.3f | tokens=%s | tiempo_total=%.3fs",
            report["files_found"],
            report["downloaded"],
            report["skipped"],
            report["deleted"],
            telemetry["graph_requests_total"],
            telemetry["graph_download_requests"],
            telemetry["bytes_downloaded_mb"],
            telemetry["token_acquisitions"],
            report["sync_time_seconds"],
        )
        return report
