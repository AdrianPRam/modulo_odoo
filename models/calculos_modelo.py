# -*- coding: utf-8 -*-


def calcular_porcentaje_valor(registros):
    for registro in registros:
        registro.porcentaje_valor = float(registro.valor) / 100


def calcular_totales_factura(facturas):
    for factura in facturas:
        factura.subtotal = sum(factura.linea_ids.mapped("subtotal"))
        factura.total_impuestos = sum(factura.linea_ids.mapped("impuesto"))
        factura.total = sum(factura.linea_ids.mapped("total"))


def calcular_importes_linea(lineas):
    for linea in lineas:
        subtotal = float(linea.cantidad or 0.0) * float(linea.precio_unitario or 0.0)
        impuesto = subtotal * (float(linea.impuesto_pct or 0.0) / 100.0)
        linea.subtotal = subtotal
        linea.impuesto = impuesto
        linea.total = subtotal + impuesto
