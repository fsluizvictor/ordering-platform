from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from product_service.adapters.outbound.persistence.models import ProductModel
from product_service.domain.entities.product import Product
from product_service.domain.ports.product_repository import ProductRepository


class SQLAlchemyProductRepository(ProductRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, product: Product) -> Product:
        model = _to_model(product)
        self._session.add(model)
        self._session.flush()
        return product

    def find_by_id(self, product_id: uuid.UUID) -> Product | None:
        model = self._session.get(ProductModel, product_id)
        return _to_entity(model) if model else None

    def find_by_name(self, name: str) -> list[Product]:
        # Case-insensitive partial match so callers can search by partial name.
        stmt = select(ProductModel).where(ProductModel.name.ilike(f"%{name}%"))
        return [_to_entity(m) for m in self._session.scalars(stmt).all()]

    def find_all(self) -> list[Product]:
        stmt = select(ProductModel)
        return [_to_entity(m) for m in self._session.scalars(stmt).all()]

    def update(self, product: Product) -> Product:
        model = self._session.get(ProductModel, product.id)
        if model is None:
            raise ValueError(f"Product not found in persistence: {product.id}")
        model.name = product.name
        model.description = product.description
        model.price = product.price
        model.stock = product.stock
        model.updated_at = product.updated_at
        self._session.flush()
        return product

    def delete(self, product_id: uuid.UUID) -> None:
        model = self._session.get(ProductModel, product_id)
        if model is not None:
            self._session.delete(model)
            self._session.flush()

    def count(self) -> int:
        stmt = select(func.count()).select_from(ProductModel)
        return self._session.scalar(stmt) or 0


def _to_model(product: Product) -> ProductModel:
    return ProductModel(
        id=product.id,
        name=product.name,
        description=product.description,
        price=product.price,
        stock=product.stock,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _to_entity(model: ProductModel) -> Product:
    return Product(
        id=model.id,
        name=model.name,
        description=model.description,
        price=model.price,
        stock=model.stock,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
