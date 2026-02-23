# -*- coding: utf-8 -*-

from odoo import _
from odoo.exceptions import UserError


def validar_facturae(factura):
    factura.ensure_one()
    if factura.estado != "publicada":
        raise UserError(_("La factura debe estar publicada antes de generar Facturae."))
    if not factura.linea_ids:
        raise UserError(_("La factura debe tener al menos una linea."))
    if len((factura.moneda or "").strip()) != 3:
        raise UserError(_("La moneda debe ser un codigo ISO-4217 valido (por ejemplo, EUR)."))

    validar_bloque_tercero(
        factura.emisor_nombre,
        factura.emisor_nif,
        factura.emisor_direccion,
        factura.emisor_cp,
        factura.emisor_ciudad,
        factura.emisor_provincia,
        "Emisor",
    )
    validar_bloque_tercero(
        factura.receptor_nombre,
        factura.receptor_nif,
        factura.receptor_direccion,
        factura.receptor_cp,
        factura.receptor_ciudad,
        factura.receptor_provincia,
        "Receptor",
    )


def validar_bloque_tercero(nombre, nif, direccion, cp, ciudad, provincia, etiqueta):
    faltantes = []
    if not nombre:
        faltantes.append("nombre")
    if not nif:
        faltantes.append("NIF/CIF")
    if not direccion:
        faltantes.append("direccion")
    if not cp:
        faltantes.append("codigo postal")
    if not ciudad:
        faltantes.append("ciudad")
    if not provincia:
        faltantes.append("provincia")

    if faltantes:
        raise UserError(
            _("%s: faltan datos obligatorios para Facturae: %s")
            % (etiqueta, ", ".join(faltantes))
        )
