import logging
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.models.card import Card

logger = logging.getLogger(__name__)


class CardMediaServiceError(Exception):
    pass


class CardMediaService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.media_root = Path(self.settings.media_root).resolve()
        self.cards_root = (self.media_root / self.settings.media_cards_dir).resolve()

    def ensure_storage_dirs(self) -> None:
        self.cards_root.mkdir(parents=True, exist_ok=True)

    def get_local_image_path(self, card: Card, size: str) -> Path | None:
        relative_path = card.local_image_large_path if size == "large" else card.local_image_small_path
        if not relative_path:
            return None

        path = (self.media_root / relative_path).resolve()
        try:
            path.relative_to(self.media_root)
        except ValueError:
            logger.warning("Se detecto una ruta local fuera del media root para la carta %s", card.external_id)
            return None

        return path

    def has_local_image(self, card: Card, size: str) -> bool:
        local_path = self.get_local_image_path(card, size)
        return bool(local_path and local_path.exists())

    async def ensure_local_images(self, card: Card) -> bool:
        self.ensure_storage_dirs()
        changed = False

        small_path = await self._ensure_image_copy(
            external_id=card.external_id,
            size="small",
            source_url=card.image_small or card.image_large,
            current_relative_path=card.local_image_small_path,
        )
        if small_path != card.local_image_small_path:
            card.local_image_small_path = small_path
            changed = True

        large_path = await self._ensure_image_copy(
            external_id=card.external_id,
            size="large",
            source_url=card.image_large or card.image_small,
            current_relative_path=card.local_image_large_path,
        )
        if large_path != card.local_image_large_path:
            card.local_image_large_path = large_path
            changed = True

        return changed

    def save_uploaded_images(
        self,
        card: Card,
        *,
        content: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> bool:
        self.ensure_storage_dirs()

        if not content:
            raise CardMediaServiceError("La imagen subida esta vacia.")

        if content_type and not content_type.startswith("image/"):
            raise CardMediaServiceError("El archivo subido no es una imagen valida.")

        extension = self._resolve_upload_extension(filename, content_type)
        card_dir = (self.cards_root / self._sanitize_external_id(card.external_id)).resolve()
        card_dir.mkdir(parents=True, exist_ok=True)

        for size in ("small", "large"):
            for stale_path in card_dir.glob(f"{size}.*"):
                if stale_path.is_file():
                    stale_path.unlink()

            file_path = (card_dir / f"{size}{extension}").resolve()
            file_path.write_bytes(content)
            relative_path = file_path.relative_to(self.media_root).as_posix()

            if size == "small":
                card.local_image_small_path = relative_path
            else:
                card.local_image_large_path = relative_path

        return True

    async def _ensure_image_copy(
        self,
        *,
        external_id: str,
        size: str,
        source_url: str | None,
        current_relative_path: str | None,
    ) -> str | None:
        if not source_url:
            return current_relative_path

        current_path = None
        if current_relative_path:
            current_path = (self.media_root / current_relative_path).resolve()
            if current_path.exists():
                return current_relative_path

        content, content_type = await self.download_image(source_url)
        extension = self._resolve_extension(source_url, content_type)
        card_dir = (self.cards_root / self._sanitize_external_id(external_id)).resolve()
        card_dir.mkdir(parents=True, exist_ok=True)

        for stale_path in card_dir.glob(f"{size}.*"):
            if stale_path.is_file():
                stale_path.unlink()

        file_path = (card_dir / f"{size}{extension}").resolve()
        file_path.write_bytes(content)
        return file_path.relative_to(self.media_root).as_posix()

    async def download_image(self, image_url: str) -> tuple[bytes, str | None]:
        parsed = urlparse(image_url)
        if parsed.scheme not in {"http", "https"}:
            raise CardMediaServiceError("URL de imagen invalida.")

        headers = {
            "Accept": "image/*",
            "User-Agent": "PokeVault-TCG/1.0 (+https://pokevault.local)",
        }

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            try:
                response = await client.get(image_url, headers=headers)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise CardMediaServiceError(
                    f"No fue posible descargar la imagen externa ({exc.response.status_code})."
                ) from exc
            except httpx.HTTPError as exc:
                raise CardMediaServiceError("No fue posible descargar la imagen.") from exc

        return response.content, response.headers.get("content-type")

    def _sanitize_external_id(self, external_id: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", external_id.strip())
        normalized = normalized.strip("-")
        return normalized or "card"

    def _resolve_extension(self, image_url: str, content_type: str | None) -> str:
        if content_type:
            guessed_extension = mimetypes.guess_extension(content_type.split(";")[0].strip())
            if guessed_extension:
                return guessed_extension

        suffix = Path(urlparse(image_url).path).suffix
        if suffix and len(suffix) <= 5:
            return suffix.lower()

        return ".png"

    def _resolve_upload_extension(self, filename: str | None, content_type: str | None) -> str:
        if content_type:
            guessed_extension = mimetypes.guess_extension(content_type.split(";")[0].strip())
            if guessed_extension:
                return guessed_extension

        if filename:
            suffix = Path(filename).suffix
            if suffix and len(suffix) <= 5:
                return suffix.lower()

        return ".png"
