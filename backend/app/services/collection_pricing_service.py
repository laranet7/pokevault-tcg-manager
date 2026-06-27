from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.collection import Collection
from app.models.collection_item import CollectionItem
from app.models.user import User
from app.repositories.card_price_snapshots_repository import CardPriceSnapshotsRepository
from app.repositories.collection_items_repository import CollectionItemsRepository
from app.repositories.collections_repository import CollectionsRepository
from app.schemas.pricing import (
    CollectionItemVariationRead,
    CollectionPriceVariationRead,
    CollectionRefreshPricesResponse,
    CollectionValuationRead,
    DashboardPriceMoverRead,
    DashboardPriceMoversRead,
    PriceHistoryEntryRead,
)
from app.services.pokemon_tcg_service import PokemonTCGService, PokemonTCGServiceError


ZERO_DECIMAL = Decimal("0.00")


@dataclass
class PriceResolution:
    base_price: Decimal | None
    currency: str
    source: str | None
    marketplace: str | None
    tcgplayer_price: Decimal | None
    tcgplayer_currency: str | None
    tcgplayer_price_label: str | None
    cardmarket_price: Decimal | None
    cardmarket_currency: str | None
    cardmarket_price_label: str | None
    raw_payload_json: str | None


class CollectionPricingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.collections_repository = CollectionsRepository(session)
        self.collection_items_repository = CollectionItemsRepository(session)
        self.snapshots_repository = CardPriceSnapshotsRepository(session)
        self.pokemon_tcg_service = PokemonTCGService()

    async def get_collections_valuation(self, current_user: User) -> list[CollectionValuationRead]:
        accessible_ids = await self.collections_repository.list_accessible_ids(current_user, permission="view")
        if not accessible_ids:
            return []

        valuation_rows = await self.session.execute(
            select(
                Collection.id,
                Collection.name,
                func.count(CollectionItem.id),
                func.coalesce(func.sum(CollectionItem.quantity), 0),
                func.coalesce(func.sum(func.coalesce(CollectionItem.base_price, 0) * func.coalesce(CollectionItem.quantity, 0)), 0),
                func.coalesce(func.sum(func.coalesce(CollectionItem.sale_price, 0) * func.coalesce(CollectionItem.quantity, 0)), 0),
                func.coalesce(func.max(CollectionItem.base_price_currency), "USD"),
            )
            .outerjoin(CollectionItem, CollectionItem.collection_id == Collection.id)
            .where(Collection.id.in_(accessible_ids))
            .group_by(Collection.id)
            .order_by(Collection.name.asc())
        )

        capture_summaries = await self.snapshots_repository.list_collection_capture_summaries(accessible_ids)
        capture_map: dict[int, list[tuple[datetime, Decimal, Decimal]]] = {}
        for collection_id, captured_at, base_total, sale_total in capture_summaries:
            capture_map.setdefault(collection_id, []).append((captured_at, Decimal(base_total), Decimal(sale_total)))

        valuations: list[CollectionValuationRead] = []
        for collection_id, name, total_items, total_quantity, base_value, sale_value, currency in valuation_rows.all():
            captures = capture_map.get(collection_id, [])
            last_price_update = captures[-1][0] if captures else None
            base_difference = None
            base_difference_percent = None
            if len(captures) >= 2:
                previous_base = captures[-2][1]
                current_base = captures[-1][1]
                base_difference = (current_base - previous_base).quantize(Decimal("0.01"))
                if previous_base != ZERO_DECIMAL:
                    base_difference_percent = ((base_difference / previous_base) * Decimal("100")).quantize(Decimal("0.01"))

            valuations.append(
                CollectionValuationRead(
                    collection_id=collection_id,
                    collection_name=name,
                    total_items=int(total_items or 0),
                    total_quantity=int(total_quantity or 0),
                    base_value=Decimal(base_value or 0).quantize(Decimal("0.01")),
                    sale_value=Decimal(sale_value or 0).quantize(Decimal("0.01")),
                    currency=currency or "USD",
                    last_price_update=last_price_update,
                    base_difference=base_difference,
                    base_difference_percent=base_difference_percent,
                )
            )

        valuations = [valuation for valuation in valuations if valuation.total_quantity > 0]
        valuations.sort(
            key=lambda valuation: (
                valuation.base_value,
                valuation.sale_value,
                valuation.collection_name.casefold(),
            ),
            reverse=True,
        )

        return valuations

    async def get_dashboard_price_movers(self, current_user: User, *, days: int = 30, limit: int = 5) -> DashboardPriceMoversRead:
        period_days = max(days, 1)
        row_limit = max(limit, 1)
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
        accessible_ids = await self.collections_repository.list_accessible_ids(current_user, permission="view")
        if not accessible_ids:
            return DashboardPriceMoversRead(period_days=period_days)

        items_result = await self.session.execute(
            select(CollectionItem)
            .options(selectinload(CollectionItem.card), selectinload(CollectionItem.collection))
            .where(CollectionItem.collection_id.in_(accessible_ids))
            .where(CollectionItem.quantity > 0)
        )
        items = list(items_result.scalars().all())

        if not items:
            return DashboardPriceMoversRead(period_days=period_days)

        snapshots = await self.snapshots_repository.list_by_collection_items([item.id for item in items])
        snapshots_by_item: dict[int, list] = {}
        for snapshot in snapshots:
            snapshots_by_item.setdefault(snapshot.collection_item_id, []).append(snapshot)

        movers: list[DashboardPriceMoverRead] = []

        for item in items:
            history = [snapshot for snapshot in snapshots_by_item.get(item.id, []) if snapshot.base_price is not None]
            if len(history) < 2:
                continue

            current_snapshot = history[-1]
            if current_snapshot.captured_at < cutoff:
                continue

            baseline_before_cutoff = [snapshot for snapshot in history if snapshot.captured_at <= cutoff]
            if baseline_before_cutoff:
                baseline_snapshot = baseline_before_cutoff[-1]
            else:
                previous_in_period = [snapshot for snapshot in history if snapshot.captured_at < current_snapshot.captured_at]
                if not previous_in_period:
                    continue
                baseline_snapshot = previous_in_period[0]

            previous_price = Decimal(baseline_snapshot.base_price or 0).quantize(Decimal("0.01"))
            current_price = Decimal(current_snapshot.base_price or 0).quantize(Decimal("0.01"))
            if previous_price == ZERO_DECIMAL:
                continue

            difference = (current_price - previous_price).quantize(Decimal("0.01"))
            if difference == ZERO_DECIMAL:
                continue

            difference_percent = ((difference / previous_price) * Decimal("100")).quantize(Decimal("0.01"))
            trend = "up" if difference > ZERO_DECIMAL else "down"

            movers.append(
                DashboardPriceMoverRead(
                    collection_item_id=item.id,
                    collection_id=item.collection_id,
                    collection_name=item.collection.name,
                    card_id=item.card_id,
                    card_name=item.card.name,
                    card_number=item.card.number,
                    set_name=item.card.set_name,
                    image_small=item.card.image_small,
                    image_large=item.card.image_large,
                    previous_price=previous_price,
                    current_price=current_price,
                    difference=difference,
                    difference_percent=difference_percent,
                    currency=current_snapshot.currency or item.base_price_currency or "USD",
                    from_captured_at=baseline_snapshot.captured_at,
                    to_captured_at=current_snapshot.captured_at,
                    trend=trend,
                )
            )

        top_gainers = sorted(
            [mover for mover in movers if mover.difference > ZERO_DECIMAL],
            key=lambda mover: (mover.difference_percent, mover.difference, mover.card_name.casefold()),
            reverse=True,
        )[:row_limit]
        top_losers = sorted(
            [mover for mover in movers if mover.difference < ZERO_DECIMAL],
            key=lambda mover: (mover.difference_percent, mover.difference, mover.card_name.casefold()),
        )[:row_limit]

        return DashboardPriceMoversRead(
            period_days=period_days,
            top_gainers=top_gainers,
            top_losers=top_losers,
        )

    async def refresh_collection_prices(self, collection_id: int) -> CollectionRefreshPricesResponse:
        collection = await self.collections_repository.get_by_id(collection_id)
        if collection is None:
            raise ValueError("Coleccion no encontrada.")

        items = await self.collection_items_repository.list_by_collection(collection_id)
        captured_at = datetime.now(timezone.utc)
        card_cache: dict[str, dict] = {}
        processed_items = len(items)
        updated_items = 0
        items_without_price = 0
        items_failed = 0

        for item in items:
            try:
                payload = await self._get_card_payload(item.card.external_id, item.card.api_source, card_cache)
                resolution = self._resolve_market_price(payload, item.finish, item.pattern_variant)
            except PokemonTCGServiceError:
                items_failed += 1
                continue

            if resolution.base_price is not None:
                item.base_price = resolution.base_price
                item.base_price_currency = resolution.currency
                item.sale_price = self._compute_sale_price(resolution.base_price, item.sale_margin_percent, item.sale_price)
                item.tcgplayer_price = resolution.tcgplayer_price
                item.tcgplayer_currency = resolution.tcgplayer_currency
                item.tcgplayer_price_label = resolution.tcgplayer_price_label
                item.cardmarket_price = resolution.cardmarket_price
                item.cardmarket_currency = resolution.cardmarket_currency
                item.cardmarket_price_label = resolution.cardmarket_price_label
                updated_items += 1
            else:
                items_without_price += 1
                # Keep the existing valuation when the external API has no usable price.
                # This protects manual market values from being overwritten by empty/zero feeds.

            base_total = self._compute_total(item.base_price, item.quantity)
            sale_total = self._compute_total(item.sale_price, item.quantity)

            await self.snapshots_repository.create(
                collection_id=collection.id,
                collection_item_id=item.id,
                card_id=item.card_id,
                source=resolution.source,
                marketplace=resolution.marketplace,
                currency=item.base_price_currency or resolution.currency,
                tcgplayer_price=resolution.tcgplayer_price,
                tcgplayer_currency=resolution.tcgplayer_currency,
                tcgplayer_price_label=resolution.tcgplayer_price_label,
                cardmarket_price=resolution.cardmarket_price,
                cardmarket_currency=resolution.cardmarket_currency,
                cardmarket_price_label=resolution.cardmarket_price_label,
                finish=item.finish,
                pattern_variant=item.pattern_variant,
                base_price=item.base_price,
                sale_price=item.sale_price,
                quantity=item.quantity,
                base_total=base_total,
                sale_total=sale_total,
                captured_at=captured_at,
                raw_payload_json=resolution.raw_payload_json,
            )

        await self.session.flush()
        valuation = await self._get_collection_current_totals(collection.id, collection.name)

        return CollectionRefreshPricesResponse(
            collection_id=collection.id,
            collection_name=collection.name,
            processed_items=processed_items,
            updated_items=updated_items,
            items_without_price=items_without_price,
            items_failed=items_failed,
            base_value=valuation.base_value,
            sale_value=valuation.sale_value,
            currency=valuation.currency,
            captured_at=captured_at,
        )

    async def get_collection_item_price_history(self, collection_item_id: int) -> list[PriceHistoryEntryRead]:
        snapshots = await self.snapshots_repository.list_by_collection_item(collection_item_id)
        return [
            PriceHistoryEntryRead(
                captured_at=snapshot.captured_at,
                base_price=snapshot.base_price,
                sale_price=snapshot.sale_price,
                currency=snapshot.currency,
            )
            for snapshot in snapshots
        ]

    async def get_collection_price_variation(self, collection_id: int) -> CollectionPriceVariationRead:
        collection = await self.collections_repository.get_by_id(collection_id)
        if collection is None:
            raise ValueError("Coleccion no encontrada.")

        items = await self.collection_items_repository.list_by_collection(collection_id)
        snapshots = await self.snapshots_repository.list_by_collection(collection_id)
        capture_summaries = await self.snapshots_repository.list_collection_capture_summaries()

        snapshots_by_item: dict[int, list] = {}
        for snapshot in snapshots:
            snapshots_by_item.setdefault(snapshot.collection_item_id, []).append(snapshot)

        collection_captures = [
            (captured_at, Decimal(base_total or 0).quantize(Decimal("0.01")), Decimal(sale_total or 0).quantize(Decimal("0.01")))
            for current_collection_id, captured_at, base_total, sale_total in capture_summaries
            if current_collection_id == collection_id
        ]

        items_up = 0
        items_down = 0
        items_equal = 0
        items_without_history = 0
        total_previous_base_value = ZERO_DECIMAL
        total_current_base_value = ZERO_DECIMAL
        item_variations: list[CollectionItemVariationRead] = []

        for item in items:
            history = snapshots_by_item.get(item.id, [])
            if len(history) < 2:
                items_without_history += 1
                item_variations.append(
                    CollectionItemVariationRead(
                        collection_item_id=item.id,
                        card_name=item.card.name,
                        previous_price=None,
                        current_price=history[-1].base_price if history else item.base_price,
                        difference=None,
                        difference_percent=None,
                        previous_total=None,
                        current_total=history[-1].base_total if history else self._compute_total(item.base_price, item.quantity),
                        currency=(history[-1].currency if history else item.base_price_currency) or "USD",
                        trend="no_history",
                    )
                )
                continue

            previous_snapshot = history[-2]
            current_snapshot = history[-1]

            previous_total = Decimal(previous_snapshot.base_total or 0).quantize(Decimal("0.01"))
            current_total = Decimal(current_snapshot.base_total or 0).quantize(Decimal("0.01"))
            difference = (Decimal(current_snapshot.base_price or 0) - Decimal(previous_snapshot.base_price or 0)).quantize(Decimal("0.01"))
            total_difference = (current_total - previous_total).quantize(Decimal("0.01"))
            difference_percent = None
            if previous_snapshot.base_price not in (None, ZERO_DECIMAL):
                difference_percent = ((difference / Decimal(previous_snapshot.base_price)) * Decimal("100")).quantize(Decimal("0.01"))

            if total_difference > ZERO_DECIMAL:
                items_up += 1
                trend = "up"
            elif total_difference < ZERO_DECIMAL:
                items_down += 1
                trend = "down"
            else:
                items_equal += 1
                trend = "equal"

            item_variations.append(
                CollectionItemVariationRead(
                    collection_item_id=item.id,
                    card_name=item.card.name,
                    previous_price=previous_snapshot.base_price,
                    current_price=current_snapshot.base_price,
                    difference=difference,
                    difference_percent=difference_percent,
                    previous_total=previous_total,
                    current_total=current_total,
                    currency=current_snapshot.currency or previous_snapshot.currency or item.base_price_currency or "USD",
                    trend=trend,
                )
            )

        if len(collection_captures) >= 2:
            total_previous_base_value = collection_captures[-2][1]
            total_current_base_value = collection_captures[-1][1]

        total_difference_value = (total_current_base_value - total_previous_base_value).quantize(Decimal("0.01"))
        total_difference_percent = None
        if total_previous_base_value != ZERO_DECIMAL:
            total_difference_percent = ((total_difference_value / total_previous_base_value) * Decimal("100")).quantize(Decimal("0.01"))

        sortable_variations = [variation for variation in item_variations if variation.difference is not None]
        top_increases = sorted(sortable_variations, key=lambda variation: variation.difference or ZERO_DECIMAL, reverse=True)[:5]
        top_decreases = sorted(sortable_variations, key=lambda variation: variation.difference or ZERO_DECIMAL)[:5]

        return CollectionPriceVariationRead(
            collection_id=collection.id,
            collection_name=collection.name,
            total_items=len(items),
            items_up=items_up,
            items_down=items_down,
            items_equal=items_equal,
            items_without_history=items_without_history,
            total_previous_base_value=total_previous_base_value.quantize(Decimal("0.01")),
            total_current_base_value=total_current_base_value.quantize(Decimal("0.01")),
            total_difference=total_difference_value,
            total_difference_percent=total_difference_percent,
            top_increases=top_increases,
            top_decreases=top_decreases,
            item_variations=item_variations,
        )

    async def _get_collection_current_totals(self, collection_id: int, collection_name: str) -> CollectionValuationRead:
        result = await self.session.execute(
            select(
                func.count(CollectionItem.id),
                func.coalesce(func.sum(CollectionItem.quantity), 0),
                func.coalesce(func.sum(func.coalesce(CollectionItem.base_price, 0) * func.coalesce(CollectionItem.quantity, 0)), 0),
                func.coalesce(func.sum(func.coalesce(CollectionItem.sale_price, 0) * func.coalesce(CollectionItem.quantity, 0)), 0),
                func.coalesce(func.max(CollectionItem.base_price_currency), "USD"),
            )
            .where(CollectionItem.collection_id == collection_id)
        )
        total_items, total_quantity, base_value, sale_value, currency = result.one()
        return CollectionValuationRead(
            collection_id=collection_id,
            collection_name=collection_name,
            total_items=int(total_items or 0),
            total_quantity=int(total_quantity or 0),
            base_value=Decimal(base_value or 0).quantize(Decimal("0.01")),
            sale_value=Decimal(sale_value or 0).quantize(Decimal("0.01")),
            currency=currency or "USD",
        )

    async def _get_card_payload(self, external_id: str, api_source: str, cache: dict[str, dict]) -> dict:
        cache_key = f"{api_source}:{external_id}"
        if cache_key not in cache:
            cache[cache_key] = await self.pokemon_tcg_service.get_card_payload(external_id, api_source=api_source)
        return cache[cache_key]

    def _resolve_market_price(self, payload: dict, finish: str | None, pattern_variant: str | None = None) -> PriceResolution:
        tcgplayer_prices = ((payload.get("tcgplayer") or {}).get("prices") or {})
        cardmarket_prices = ((payload.get("cardmarket") or {}).get("prices") or {})
        finish_candidates = {
            "normal": ["normal"],
            "holo": ["holofoil"],
            "reverse holo": ["reverseHolofoil"],
            "full art": ["holofoil", "normal"],
            "illustration rare": ["holofoil", "normal"],
            "special illustration rare": ["holofoil", "normal"],
            "promo": ["holofoil", "normal"],
        }

        normalized_finish = (finish or "normal").strip().lower()
        candidates = finish_candidates.get(normalized_finish, ["normal", "holofoil", "reverseHolofoil"])
        if normalized_finish == "reverse holo" and pattern_variant:
            candidates = ["reverseHolofoil", *candidates]
        fallback_labels = list(dict.fromkeys([*candidates, *tcgplayer_prices.keys()]))

        tcgplayer_price = None
        tcgplayer_label = None
        for label in fallback_labels:
            values = tcgplayer_prices.get(label)
            if not isinstance(values, dict):
                continue
            amount = values.get("market") or values.get("mid") or values.get("low")
            if amount is None:
                continue
            tcgplayer_price = Decimal(str(amount)).quantize(Decimal("0.01"))
            tcgplayer_label = label
            break

        cardmarket_price = self._resolve_cardmarket_price(cardmarket_prices, normalized_finish, pattern_variant)
        cardmarket_label = None
        if cardmarket_price is not None:
            cardmarket_label = self._resolve_cardmarket_label(cardmarket_prices, normalized_finish, pattern_variant)

        if tcgplayer_price is not None:
            marketplace_suffix = f":{pattern_variant}" if normalized_finish == "reverse holo" and pattern_variant else ""
            return PriceResolution(
                base_price=tcgplayer_price,
                currency="USD",
                source="pokemon_tcg",
                marketplace=f"tcgplayer:{tcgplayer_label}{marketplace_suffix}",
                tcgplayer_price=tcgplayer_price,
                tcgplayer_currency="USD",
                tcgplayer_price_label=tcgplayer_label,
                cardmarket_price=cardmarket_price,
                cardmarket_currency="EUR" if cardmarket_price is not None else None,
                cardmarket_price_label=cardmarket_label,
                raw_payload_json=json.dumps({"tcgplayer": tcgplayer_prices, "cardmarket": cardmarket_prices}),
            )

        if cardmarket_price is not None:
            return PriceResolution(
                base_price=cardmarket_price,
                currency="EUR",
                source="pokemon_tcg",
                marketplace="cardmarket",
                tcgplayer_price=tcgplayer_price,
                tcgplayer_currency="USD" if tcgplayer_price is not None else None,
                tcgplayer_price_label=tcgplayer_label,
                cardmarket_price=cardmarket_price,
                cardmarket_currency="EUR",
                cardmarket_price_label=cardmarket_label,
                raw_payload_json=json.dumps({"tcgplayer": tcgplayer_prices, "cardmarket": cardmarket_prices}),
            )

        return PriceResolution(
            base_price=None,
            currency="USD",
            source="pokemon_tcg",
            marketplace=None,
            tcgplayer_price=tcgplayer_price,
            tcgplayer_currency="USD" if tcgplayer_price is not None else None,
            tcgplayer_price_label=tcgplayer_label,
            cardmarket_price=cardmarket_price,
            cardmarket_currency="EUR" if cardmarket_price is not None else None,
            cardmarket_price_label=cardmarket_label,
            raw_payload_json=json.dumps({"tcgplayer": tcgplayer_prices, "cardmarket": cardmarket_prices}),
        )

    def _resolve_cardmarket_price(
        self,
        cardmarket_prices: dict,
        normalized_finish: str,
        pattern_variant: str | None = None,
    ) -> Decimal | None:
        label = self._resolve_cardmarket_label(cardmarket_prices, normalized_finish, pattern_variant)
        if not label:
            return None

        amount = cardmarket_prices.get(label)
        if amount is None:
            return None

        normalized_amount = Decimal(str(amount)).quantize(Decimal("0.01"))
        if normalized_amount <= ZERO_DECIMAL:
            return None

        return normalized_amount

    def _resolve_cardmarket_label(
        self,
        cardmarket_prices: dict,
        normalized_finish: str,
        pattern_variant: str | None = None,
    ) -> str | None:
        preferred_labels = {
            "reverse holo": ["reverseHoloTrend", "reverseHoloSell", "reverseHoloLow", "trendPrice", "averageSellPrice"],
            "holo": ["trendPrice", "averageSellPrice", "lowPrice"],
            "normal": ["trendPrice", "averageSellPrice", "lowPrice"],
            "full art": ["trendPrice", "averageSellPrice", "lowPrice"],
            "illustration rare": ["trendPrice", "averageSellPrice", "lowPrice"],
            "special illustration rare": ["trendPrice", "averageSellPrice", "lowPrice"],
            "promo": ["trendPrice", "averageSellPrice", "lowPrice"],
        }

        labels = preferred_labels.get(normalized_finish, ["trendPrice", "averageSellPrice", "lowPrice"])
        if normalized_finish == "reverse holo" and pattern_variant:
            labels = ["reverseHoloTrend", "reverseHoloSell", "reverseHoloLow", *labels]

        for label in labels:
            if cardmarket_prices.get(label) is not None:
                return label

        return None

    def _compute_sale_price(
        self,
        base_price: Decimal | None,
        sale_margin_percent: Decimal | None,
        current_sale_price: Decimal | None,
    ) -> Decimal | None:
        if base_price is None:
            return current_sale_price
        if sale_margin_percent is None:
            return current_sale_price
        multiplier = Decimal("1") + (Decimal(sale_margin_percent) / Decimal("100"))
        return (Decimal(base_price) * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _compute_total(self, unit_price: Decimal | None, quantity: int) -> Decimal:
        if unit_price is None:
            return ZERO_DECIMAL
        return (Decimal(unit_price) * Decimal(quantity)).quantize(Decimal("0.01"))
