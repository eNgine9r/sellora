# Pilot operations guide — Sprint 8D

1. Add or verify a product variant with stock.
2. Create an order for a workspace-local customer and active variant.
3. Confirm the order before shipment.
4. Move to shipped only when the parcel is actually being sent; this deducts physical stock and releases reservation.
5. Cancel before shipment to release reservation without changing physical stock.
6. Return after shipment/delivery to restore physical stock once.
7. Create only one local shipment draft per order.
8. Do not enter Nova Poshta provider refs in the local pilot flow.
9. Use explicit inventory reasons for manual stock operations.
10. After QA, cancel/return/archive synthetic records through approved flows and verify active QA8D reservations and shipments are zero.
