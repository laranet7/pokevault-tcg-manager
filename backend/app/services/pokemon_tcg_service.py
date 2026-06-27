import asyncio
from decimal import Decimal
import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.card import CardPrice, CardSearchResult

CARD_CODE_REGEX = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")
PROMO_CODE_REGEX = re.compile(r"^\s*(?:[A-Za-z-]{2,10}\s*/\s*)?(\d+)\s*$")
SPECIAL_CARD_CODE_REGEX = re.compile(r"^\s*([A-Za-z]{1,5}\d{1,3})\s*/\s*([A-Za-z]{0,5}\d{1,3})\s*$")
ALPHANUMERIC_NUMBER_REGEX = re.compile(r"^[A-Za-z]{1,5}\d{1,3}$")
GENERAL_SET_REFERENCE_REGEX = re.compile(r"^\s*(.+?)\s+([A-Za-z]{2,6})\s+(\d{1,3})\s*$")
SET_LOCAL_ID_REFERENCE_REGEX = re.compile(r"^\s*([A-Za-z]{2,6})\s+(\d{1,3})\s*$")
PROMO_SET_ID = "svp"


class PokemonTCGServiceError(Exception):
    pass


class InvalidCardCodeError(PokemonTCGServiceError):
    pass


class PokemonTCGService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def parse_card_code(self, code: str) -> tuple[str, str]:
        match = CARD_CODE_REGEX.match(code)
        if not match:
            raise InvalidCardCodeError("El codigo debe tener formato number/printedTotal, por ejemplo 160/165.")
        return match.group(1), match.group(2)

    def parse_promo_code(self, code: str) -> str:
        match = PROMO_CODE_REGEX.match(code)
        if not match:
            raise InvalidCardCodeError("El codigo promo debe tener formato 088 o SVP/088.")

        normalized = str(int(match.group(1)))
        return normalized

    def parse_special_card_code(self, code: str) -> tuple[str, str]:
        match = SPECIAL_CARD_CODE_REGEX.match(code)
        if not match:
            raise InvalidCardCodeError("El codigo especial debe tener formato TG01/TG30 o GG12/GG70.")

        number = match.group(1).upper()
        printed_total = str(int(re.sub(r"\D", "", match.group(2))))
        return number, printed_total

    async def search_by_code(self, code: str) -> list[CardSearchResult]:
        number, printed_total = self.parse_card_code(code)
        params = {"q": f"number:{number} set.printedTotal:{printed_total}"}
        return await self._search_with_fallback(
            lambda: self._search(params, code),
            lambda: self._search_tcgdex_by_number_and_total(number, printed_total),
        )

    async def search_by_name(self, name: str) -> list[CardSearchResult]:
        normalized_name = " ".join(name.strip().split())
        if not normalized_name:
            raise PokemonTCGServiceError("Debes indicar un nombre para buscar.")

        tokens = [self._normalize_name_token(token) for token in normalized_name.split(" ")]
        query = " ".join(f"name:{token}" for token in tokens if token)
        if not query:
            raise PokemonTCGServiceError("Debes indicar un nombre valido para buscar.")

        params = {"q": query, "orderBy": "name,number"}
        return await self._search_with_fallback(
            lambda: self._search(params, normalized_name),
            lambda: self._search_tcgdex_by_name(normalized_name),
        )

    async def search_promo_by_code(self, code: str) -> list[CardSearchResult]:
        number = self.parse_promo_code(code)
        params = {"q": f"number:{number} set.id:{PROMO_SET_ID}"}
        return await self._search_with_fallback(
            lambda: self._search(params, f"SVP/{number}"),
            lambda: self._search_tcgdex_by_set_and_local_id(PROMO_SET_ID, number),
        )

    async def search_promo_by_name(self, name: str) -> list[CardSearchResult]:
        normalized_name = " ".join(name.strip().split())
        if not normalized_name:
            raise PokemonTCGServiceError("Debes indicar un nombre para buscar promos.")

        tokens = [self._normalize_name_token(token) for token in normalized_name.split(" ")]
        query = " ".join(f"name:{token}" for token in tokens if token)
        if not query:
            raise PokemonTCGServiceError("Debes indicar un nombre valido para buscar promos.")

        params = {"q": f"{query} set.id:{PROMO_SET_ID}"}
        return await self._search_with_fallback(
            lambda: self._search(params, normalized_name),
            lambda: self._search_tcgdex_by_name(normalized_name, set_id=PROMO_SET_ID),
        )

    async def search_special_by_code(self, code: str) -> list[CardSearchResult]:
        number, printed_total = self.parse_special_card_code(code)
        params = {"q": f'number:"{number}" set.printedTotal:{printed_total}'}
        return await self._search_with_fallback(
            lambda: self._search(params, code),
            lambda: self._search_tcgdex_by_number_and_total(number, printed_total),
        )

    async def search_by_card_number(self, number: str) -> list[CardSearchResult]:
        normalized_number = number.strip().upper()
        if not ALPHANUMERIC_NUMBER_REGEX.fullmatch(normalized_number):
            raise InvalidCardCodeError("El numero de carta debe tener formato TG01, GG12 o similar.")

        params = {"q": f'number:"{normalized_number}"'}
        return await self._search_with_fallback(
            lambda: self._search(params, normalized_number),
            lambda: self._search_tcgdex_by_local_id(normalized_number),
        )

    async def search_general(self, query: str) -> list[CardSearchResult]:
        normalized_query = " ".join(query.strip().split())
        if not normalized_query:
            raise PokemonTCGServiceError("Debes indicar un termino para buscar.")

        upper_query = normalized_query.upper()

        if CARD_CODE_REGEX.fullmatch(normalized_query):
            return await self.search_by_code(normalized_query)

        if upper_query.startswith("SVP/") or upper_query.startswith("PR-SV/"):
            return await self.search_promo_by_code(upper_query)

        special_match = SPECIAL_CARD_CODE_REGEX.fullmatch(upper_query)
        if special_match:
            left_code = special_match.group(1)
            if left_code.startswith("SVP"):
                return await self.search_promo_by_code(upper_query)
            return await self.search_special_by_code(upper_query)

        if ALPHANUMERIC_NUMBER_REGEX.fullmatch(upper_query):
            if upper_query.startswith("SVP"):
                return await self.search_promo_by_code(upper_query)
            return await self.search_by_card_number(upper_query)

        general_set_reference = GENERAL_SET_REFERENCE_REGEX.fullmatch(normalized_query)
        if general_set_reference:
            card_name = general_set_reference.group(1).strip()
            set_id = general_set_reference.group(2).strip().lower()
            local_id = general_set_reference.group(3).strip()
            direct_match = await self._search_tcgdex_by_set_and_local_id(set_id, local_id)
            if direct_match:
                return direct_match
            return await self.search_by_name(card_name)

        set_local_reference = SET_LOCAL_ID_REFERENCE_REGEX.fullmatch(normalized_query)
        if set_local_reference:
            set_id = set_local_reference.group(1).strip().lower()
            local_id = set_local_reference.group(2).strip()
            direct_match = await self._search_tcgdex_by_set_and_local_id(set_id, local_id)
            if direct_match:
                return direct_match

        return await self.search_by_name(normalized_query)

    async def get_card_payload(self, external_id: str, api_source: str = "pokemon_tcg") -> dict[str, Any]:
        if api_source == "tcgdex":
            return await self._get_tcgdex_card_payload(external_id)

        headers: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": "PokeVault-TCG/1.0 (+https://pokevault.local)",
        }

        if self.settings.pokemon_tcg_api_key:
            headers["X-Api-Key"] = self.settings.pokemon_tcg_api_key

        async with httpx.AsyncClient(base_url=self.settings.pokemon_tcg_api_url, timeout=20.0) as client:
            try:
                response = await client.get(f"/cards/{external_id}", headers=headers)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 403:
                    raise PokemonTCGServiceError(
                        "Pokemon TCG API rechazo la solicitud externa (403). Intenta nuevamente en unos segundos."
                    ) from exc
                raise PokemonTCGServiceError(
                    f"Pokemon TCG API devolvio {exc.response.status_code} al consultar la carta {external_id}."
                ) from exc
            except httpx.HTTPError as exc:
                raise PokemonTCGServiceError("No fue posible conectar con Pokemon TCG API.") from exc

        payload = response.json()
        return payload.get("data", {})

    async def _search_with_fallback(
        self,
        primary_search: Any,
        fallback_search: Any,
    ) -> list[CardSearchResult]:
        primary_error: PokemonTCGServiceError | None = None

        try:
            primary_results = await primary_search()
        except PokemonTCGServiceError as exc:
            primary_error = exc
            primary_results = []

        if primary_results:
            return primary_results

        try:
            fallback_results = await fallback_search()
        except PokemonTCGServiceError:
            fallback_results = []

        if fallback_results:
            return fallback_results

        if primary_error is not None:
            raise primary_error

        return []

    async def _search(self, params: dict[str, str], query_label: str) -> list[CardSearchResult]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": "PokeVault-TCG/1.0 (+https://pokevault.local)",
        }

        if self.settings.pokemon_tcg_api_key:
            headers["X-Api-Key"] = self.settings.pokemon_tcg_api_key

        async with httpx.AsyncClient(base_url=self.settings.pokemon_tcg_api_url, timeout=20.0) as client:
            try:
                response = await client.get("/cards", params=params, headers=headers)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 403:
                    raise PokemonTCGServiceError(
                        "Pokemon TCG API rechazo la solicitud externa (403). Intenta nuevamente en unos segundos."
                    ) from exc
                raise PokemonTCGServiceError(
                    f"Pokemon TCG API devolvio {exc.response.status_code} para la busqueda {query_label}."
                ) from exc
            except httpx.HTTPError as exc:
                raise PokemonTCGServiceError("No fue posible conectar con Pokemon TCG API.") from exc

        payload = response.json()
        cards = payload.get("data", [])
        return [self._normalize_card(card) for card in cards]

    async def _search_tcgdex_by_name(self, name: str, set_id: str | None = None) -> list[CardSearchResult]:
        params: dict[str, str] = {"name": name}
        if set_id:
            params["set.id"] = set_id
        return await self._tcgdex_search_cards(params)

    async def _search_tcgdex_by_local_id(self, local_id: str) -> list[CardSearchResult]:
        return await self._tcgdex_search_cards(
            {"localId": local_id},
            exact_local_id=local_id,
        )

    async def _search_tcgdex_by_number_and_total(self, local_id: str, printed_total: str) -> list[CardSearchResult]:
        total_matches = await self._tcgdex_search_cards(
            {"localId": local_id, "set.cardCount.total": printed_total},
            exact_local_id=local_id,
            printed_total=printed_total,
        )
        if total_matches:
            return total_matches

        official_matches = await self._tcgdex_search_cards(
            {"localId": local_id, "set.cardCount.official": printed_total},
            exact_local_id=local_id,
            printed_total=printed_total,
        )
        if official_matches:
            return official_matches

        return await self._tcgdex_search_cards(
            {"localId": local_id},
            exact_local_id=local_id,
            printed_total=printed_total,
        )

    async def _search_tcgdex_by_set_and_local_id(self, set_id: str, local_id: str) -> list[CardSearchResult]:
        normalized_set_id = set_id.strip().lower()
        candidates = self._build_local_id_candidates(local_id)

        for candidate in candidates:
            card = await self._tcgdex_get_card_from_set(normalized_set_id, candidate)
            if card is not None:
                return [self._normalize_tcgdex_card(card)]

        return []

    async def _tcgdex_search_cards(
        self,
        params: dict[str, str],
        *,
        exact_local_id: str | None = None,
        printed_total: str | None = None,
        set_id: str | None = None,
        limit: int = 24,
    ) -> list[CardSearchResult]:
        brief_cards = await self._tcgdex_list_cards(params)
        if not brief_cards:
            return []

        detail_ids: list[str] = []
        for card in brief_cards:
            card_id = card.get("id")
            if isinstance(card_id, str) and card_id:
                detail_ids.append(card_id)
            if len(detail_ids) >= limit:
                break

        details = await asyncio.gather(*(self._tcgdex_get_card(card_id) for card_id in detail_ids))
        filtered_cards = [
            card
            for card in details
            if card is not None and self._matches_tcgdex_card(card, exact_local_id=exact_local_id, printed_total=printed_total, set_id=set_id)
        ]
        return [self._normalize_tcgdex_card(card) for card in filtered_cards]

    async def _tcgdex_list_cards(self, params: dict[str, str]) -> list[dict[str, Any]]:
        payload = await self._tcgdex_get_json("/cards", params=params)
        normalized = self._coerce_tcgdex_results(payload)
        if normalized:
            return normalized
        return []

    async def _tcgdex_get_card(self, card_id: str) -> dict[str, Any] | None:
        try:
            payload = await self._tcgdex_get_json(f"/cards/{card_id}")
        except PokemonTCGServiceError:
            return None
        return payload if isinstance(payload, dict) and payload.get("id") else None

    async def _tcgdex_get_card_from_set(self, set_id: str, local_id: str) -> dict[str, Any] | None:
        try:
            payload = await self._tcgdex_get_json(f"/sets/{set_id}/{local_id}")
        except PokemonTCGServiceError:
            return None
        return payload if isinstance(payload, dict) and payload.get("id") else None

    async def _get_tcgdex_card_payload(self, external_id: str) -> dict[str, Any]:
        payload = await self._tcgdex_get_card(external_id)
        if payload is None:
            raise PokemonTCGServiceError(f"TCGdex no encontro la carta {external_id}.")
        return self._normalize_tcgdex_payload_for_pricing(payload)

    async def _tcgdex_get_json(self, path: str, params: dict[str, str] | None = None) -> Any:
        base_url = f"{self.settings.tcgdex_api_url}/{self.settings.tcgdex_api_language}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "PokeVault-TCG/1.0 (+https://pokevault.local)",
        }

        async with httpx.AsyncClient(base_url=base_url, timeout=20.0) as client:
            try:
                response = await client.get(path, params=params, headers=headers)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    raise PokemonTCGServiceError("TCGdex no encontro resultados para la carta solicitada.") from exc
                raise PokemonTCGServiceError(
                    f"TCGdex devolvio {exc.response.status_code} para la solicitud externa."
                ) from exc
            except httpx.HTTPError as exc:
                raise PokemonTCGServiceError("No fue posible conectar con TCGdex.") from exc

        return response.json()

    def _coerce_tcgdex_results(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [entry for entry in payload if isinstance(entry, dict)]
        if isinstance(payload, dict) and payload.get("id"):
            return [payload]
        return []

    def _matches_tcgdex_card(
        self,
        card: dict[str, Any],
        *,
        exact_local_id: str | None = None,
        printed_total: str | None = None,
        set_id: str | None = None,
    ) -> bool:
        if exact_local_id is not None:
            if self._normalize_local_id(card.get("localId")) != self._normalize_local_id(exact_local_id):
                return False

        if printed_total is not None:
            card_total = ((card.get("set") or {}).get("cardCount") or {}).get("official")
            card_total = card_total or ((card.get("set") or {}).get("cardCount") or {}).get("total")
            if card_total is None or str(card_total) != str(int(printed_total)):
                return False

        if set_id is not None:
            if str((card.get("set") or {}).get("id", "")).strip().lower() != set_id.strip().lower():
                return False

        return True

    def _build_local_id_candidates(self, local_id: str) -> list[str]:
        normalized = str(local_id).strip().upper()
        candidates = [normalized]

        digits_only = re.sub(r"\D", "", normalized)
        if digits_only:
            stripped = str(int(digits_only))
            if stripped not in candidates:
                candidates.append(stripped)
            padded = digits_only.zfill(3)
            if padded not in candidates:
                candidates.append(padded)

        return candidates

    def _normalize_card(self, card: dict[str, Any]) -> CardSearchResult:
        prices = self._extract_prices(card)
        national_pokedex_numbers = card.get("nationalPokedexNumbers") or []
        pokedex_number = next(
            (int(value) for value in national_pokedex_numbers if isinstance(value, int) or str(value).isdigit()),
            None,
        )

        return CardSearchResult(
            external_id=card["id"],
            api_source="pokemon_tcg",
            name=card["name"],
            number=card["number"],
            set_id=(card.get("set") or {}).get("id"),
            set_name=(card.get("set") or {}).get("name"),
            printed_total=(card.get("set") or {}).get("printedTotal"),
            supertype=card.get("supertype"),
            pokedex_number=pokedex_number,
            rarity=card.get("rarity"),
            image_small=(card.get("images") or {}).get("small"),
            image_large=(card.get("images") or {}).get("large"),
            prices=prices,
            raw_prices={
                "tcgplayer": (card.get("tcgplayer") or {}).get("prices"),
                "cardmarket": (card.get("cardmarket") or {}).get("prices"),
            },
        )

    def _normalize_tcgdex_card(self, card: dict[str, Any]) -> CardSearchResult:
        normalized_payload = self._normalize_tcgdex_payload_for_pricing(card)
        prices = self._extract_prices(normalized_payload)
        dex_ids = card.get("dexId") or []
        pokedex_number = next((int(value) for value in dex_ids if isinstance(value, int) or str(value).isdigit()), None)
        image_url = card.get("image")
        image_small = self._build_tcgdex_image_url(image_url, quality="low")
        image_large = self._build_tcgdex_image_url(image_url, quality="high")
        rarity = self._normalize_rarity(card.get("rarity"))

        return CardSearchResult(
            external_id=card["id"],
            api_source="tcgdex",
            name=card["name"],
            number=str(card.get("localId") or ""),
            set_id=(card.get("set") or {}).get("id"),
            set_name=(card.get("set") or {}).get("name"),
            printed_total=((card.get("set") or {}).get("cardCount") or {}).get("official")
            or ((card.get("set") or {}).get("cardCount") or {}).get("total"),
            supertype=card.get("category"),
            pokedex_number=pokedex_number,
            rarity=rarity,
            image_small=image_small,
            image_large=image_large,
            prices=prices,
            raw_prices={
                "tcgplayer": (normalized_payload.get("tcgplayer") or {}).get("prices"),
                "cardmarket": (normalized_payload.get("cardmarket") or {}).get("prices"),
            },
        )

    def _normalize_tcgdex_payload_for_pricing(self, card: dict[str, Any]) -> dict[str, Any]:
        tcgplayer_prices = self._normalize_tcgdex_tcgplayer_prices((card.get("pricing") or {}).get("tcgplayer"))
        cardmarket_prices = self._normalize_tcgdex_cardmarket_prices((card.get("pricing") or {}).get("cardmarket"))

        return {
            "id": card.get("id"),
            "name": card.get("name"),
            "number": card.get("localId"),
            "tcgplayer": {"prices": tcgplayer_prices},
            "cardmarket": {"prices": cardmarket_prices},
        }

    def _normalize_tcgdex_tcgplayer_prices(self, pricing: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(pricing, dict):
            return {}

        variant_mapping = {
            "normal": "normal",
            "holofoil": "holofoil",
            "reverse": "reverseHolofoil",
            "reverse-holofoil": "reverseHolofoil",
            "1st-edition": "1stEdition",
            "1st-edition-holofoil": "1stEditionHolofoil",
            "unlimited": "unlimited",
            "unlimited-holofoil": "unlimitedHolofoil",
        }

        normalized: dict[str, Any] = {}
        for source_label, target_label in variant_mapping.items():
            value = pricing.get(source_label)
            if not isinstance(value, dict):
                continue
            normalized[target_label] = {
                "market": value.get("marketPrice"),
                "mid": value.get("midPrice"),
                "low": value.get("lowPrice"),
                "high": value.get("highPrice"),
                "directLow": value.get("directLowPrice"),
            }

        return normalized

    def _normalize_tcgdex_cardmarket_prices(self, pricing: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(pricing, dict):
            return {}

        return {
            "averageSellPrice": pricing.get("avg"),
            "lowPrice": pricing.get("low"),
            "trendPrice": pricing.get("trend"),
            "reverseHoloSell": pricing.get("avg-holo"),
            "reverseHoloLow": pricing.get("low-holo"),
            "reverseHoloTrend": pricing.get("trend-holo"),
        }

    def _extract_prices(self, card: dict[str, Any]) -> list[CardPrice]:
        normalized: list[CardPrice] = []

        tcgplayer_prices = (card.get("tcgplayer") or {}).get("prices") or {}
        for label, value in tcgplayer_prices.items():
            if not isinstance(value, dict):
                continue
            market_price = value.get("market") or value.get("mid") or value.get("low")
            if market_price is None:
                continue
            normalized.append(
                CardPrice(source="tcgplayer", currency="USD", label=label, amount=Decimal(str(market_price)))
            )

        cardmarket_prices = (card.get("cardmarket") or {}).get("prices") or {}
        average_sell_price = cardmarket_prices.get("averageSellPrice") or cardmarket_prices.get("trendPrice")
        if average_sell_price is not None:
            normalized.append(
                CardPrice(
                    source="cardmarket",
                    currency="EUR",
                    label="market",
                    amount=Decimal(str(average_sell_price)),
                )
            )

        return normalized

    def _normalize_name_token(self, token: str) -> str:
        cleaned = token.strip()
        if not cleaned:
            return ""
        return re.sub(r'([:\\"])', r"\\\1", cleaned)

    def _normalize_local_id(self, value: Any) -> str:
        normalized = str(value or "").strip().upper()
        if re.fullmatch(r"\d+", normalized):
            return str(int(normalized))
        return normalized

    def _normalize_rarity(self, value: Any) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()
        if not normalized or normalized.lower() == "none":
            return None

        return normalized

    def _build_tcgdex_image_url(self, base_url: Any, *, quality: str) -> str | None:
        if not isinstance(base_url, str):
            return None

        normalized = base_url.strip().rstrip("/")
        if not normalized:
            return None

        if normalized.endswith((".png", ".jpg", ".jpeg", ".webp")):
            return normalized

        return f"{normalized}/{quality}.webp"
