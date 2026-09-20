from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from product_service.domain.entities.product import Product
from product_service.domain.exceptions import ProductNotFoundError
from product_service.domain.ports.product_repository import ProductRepository

logger = logging.getLogger(__name__)


class ProductService:
    def __init__(self, repository: ProductRepository) -> None:
        self._repo = repository

    def create_product(
        self,
        name: str,
        price: Decimal | float | str,
        stock: int,
        description: str = "",
    ) -> Product:
        product = Product.create(
            name=name,
            price=price,
            stock=stock,
            description=description,
        )
        saved = self._repo.save(product)
        logger.info("Product created: %s", saved.id)
        return saved

    def get_product(self, product_id: uuid.UUID) -> Product:
        product = self._repo.find_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(str(product_id))
        return product

    def find_by_name(self, name: str) -> list[Product]:
        return self._repo.find_by_name(name)

    def list_products(self) -> list[Product]:
        return self._repo.find_all()

    def update_product(
        self,
        product_id: uuid.UUID,
        name: str | None = None,
        price: Decimal | float | str | None = None,
        stock: int | None = None,
        description: str | None = None,
    ) -> Product:
        product = self._repo.find_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(str(product_id))

        product.update(
            name=name,
            price=price,
            stock=stock,
            description=description,
        )
        updated = self._repo.update(product)
        logger.info("Product updated: %s", product_id)
        return updated

    def delete_product(self, product_id: uuid.UUID) -> None:
        product = self._repo.find_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(str(product_id))
        self._repo.delete(product_id)
        logger.info("Product deleted: %s", product_id)

    def count_products(self) -> int:
        return self._repo.count()
