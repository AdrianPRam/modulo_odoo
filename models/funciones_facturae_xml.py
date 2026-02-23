# -*- coding: utf-8 -*-

import re
from decimal import Decimal, ROUND_HALF_UP
from xml.etree import ElementTree as ET

from odoo import fields


ESPACIO_NOMBRES_FACTURAE = "http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml"


def construir_facturae_322_xml(factura):
    factura.ensure_one()
    ET.register_namespace("", ESPACIO_NOMBRES_FACTURAE)

    fecha_emision = factura.fecha or fields.Date.context_today(factura)
    codigo_moneda = (factura.moneda or "EUR").upper()
    subtotal = Decimal(str(factura.subtotal))
    impuestos = Decimal(str(factura.total_impuestos))
    total = Decimal(str(factura.total))

    raiz = ET.Element(_fe_etiqueta("Facturae"))
    cabecera_fichero = _fe_agregar(raiz, "FileHeader")
    _fe_agregar(cabecera_fichero, "SchemaVersion", "3.2.2")
    _fe_agregar(cabecera_fichero, "Modality", "I")
    _fe_agregar(cabecera_fichero, "InvoiceIssuerType", "EM")

    lote = _fe_agregar(cabecera_fichero, "Batch")
    _fe_agregar(lote, "BatchIdentifier", ("%s%s" % (factura.emisor_nif, factura.nombre))[:70])
    _fe_agregar(lote, "InvoicesCount", "1")
    _fe_agregar_importe(lote, "TotalInvoicesAmount", total)
    _fe_agregar_importe(lote, "TotalOutstandingAmount", total)
    _fe_agregar_importe(lote, "TotalExecutableAmount", total)
    _fe_agregar(lote, "InvoiceCurrencyCode", codigo_moneda)

    partes = _fe_agregar(raiz, "Parties")
    _fe_construir_parte(
        partes,
        "SellerParty",
        factura.emisor_nombre,
        factura.emisor_nif,
        factura.emisor_direccion,
        factura.emisor_cp,
        factura.emisor_ciudad,
        factura.emisor_provincia,
        factura.emisor_telefono,
        factura.emisor_email,
    )
    _fe_construir_parte(
        partes,
        "BuyerParty",
        factura.receptor_nombre,
        factura.receptor_nif,
        factura.receptor_direccion,
        factura.receptor_cp,
        factura.receptor_ciudad,
        factura.receptor_provincia,
        factura.receptor_telefono,
        factura.receptor_email,
    )

    facturas = _fe_agregar(raiz, "Invoices")
    factura_xml = _fe_agregar(facturas, "Invoice")
    cabecera_factura = _fe_agregar(factura_xml, "InvoiceHeader")
    _fe_agregar(cabecera_factura, "InvoiceNumber", (factura.nombre or "")[:20])
    _fe_agregar(cabecera_factura, "InvoiceDocumentType", "FC")
    _fe_agregar(cabecera_factura, "InvoiceClass", "OO")

    datos_emision = _fe_agregar(factura_xml, "InvoiceIssueData")
    _fe_agregar(datos_emision, "IssueDate", fecha_emision.isoformat())
    _fe_agregar(datos_emision, "InvoiceCurrencyCode", codigo_moneda)
    _fe_agregar(datos_emision, "TaxCurrencyCode", codigo_moneda)
    _fe_agregar(datos_emision, "LanguageName", "es")

    impuestos_repercutidos = _fe_agregar(factura_xml, "TaxesOutputs")
    mapa_impuestos = {}
    for linea in factura.linea_ids:
        clave = _fe_decimal(Decimal(str(linea.impuesto_pct)))
        if clave not in mapa_impuestos:
            mapa_impuestos[clave] = {
                "tipo": Decimal(str(linea.impuesto_pct)),
                "base": Decimal("0"),
                "cuota": Decimal("0"),
            }
        mapa_impuestos[clave]["base"] += Decimal(str(linea.subtotal))
        mapa_impuestos[clave]["cuota"] += Decimal(str(linea.impuesto))

    for datos in mapa_impuestos.values():
        nodo_impuesto = _fe_agregar(impuestos_repercutidos, "Tax")
        _fe_agregar(nodo_impuesto, "TaxTypeCode", "01")
        _fe_agregar(nodo_impuesto, "TaxRate", _fe_decimal(datos["tipo"]))
        _fe_agregar_importe(nodo_impuesto, "TaxableBase", datos["base"])
        _fe_agregar_importe(nodo_impuesto, "TaxAmount", datos["cuota"])

    totales = _fe_agregar(factura_xml, "InvoiceTotals")
    _fe_agregar(totales, "TotalGrossAmount", _fe_decimal(subtotal))
    _fe_agregar(totales, "TotalGrossAmountBeforeTaxes", _fe_decimal(subtotal))
    _fe_agregar(totales, "TotalTaxOutputs", _fe_decimal(impuestos))
    _fe_agregar(totales, "TotalTaxesWithheld", _fe_decimal(Decimal("0")))
    _fe_agregar(totales, "InvoiceTotal", _fe_decimal(total))
    _fe_agregar(totales, "TotalOutstandingAmount", _fe_decimal(total))
    _fe_agregar(totales, "TotalExecutableAmount", _fe_decimal(total))

    items = _fe_agregar(factura_xml, "Items")
    for linea in factura.linea_ids:
        linea_xml = _fe_agregar(items, "InvoiceLine")
        _fe_agregar(linea_xml, "ItemDescription", (linea.descripcion or "")[:2500])
        _fe_agregar(linea_xml, "Quantity", _fe_decimal(Decimal(str(linea.cantidad))))
        _fe_agregar(
            linea_xml,
            "UnitPriceWithoutTax",
            _fe_decimal(Decimal(str(linea.precio_unitario))),
        )
        _fe_agregar(linea_xml, "TotalCost", _fe_decimal(Decimal(str(linea.subtotal))))
        _fe_agregar(linea_xml, "GrossAmount", _fe_decimal(Decimal(str(linea.subtotal))))

        impuestos_linea = _fe_agregar(linea_xml, "TaxesOutputs")
        nodo_impuesto_linea = _fe_agregar(impuestos_linea, "Tax")
        _fe_agregar(nodo_impuesto_linea, "TaxTypeCode", "01")
        _fe_agregar(
            nodo_impuesto_linea,
            "TaxRate",
            _fe_decimal(Decimal(str(linea.impuesto_pct))),
        )
        _fe_agregar_importe(nodo_impuesto_linea, "TaxableBase", Decimal(str(linea.subtotal)))
        _fe_agregar_importe(nodo_impuesto_linea, "TaxAmount", Decimal(str(linea.impuesto)))

    bytes_xml = ET.tostring(raiz, encoding="utf-8", xml_declaration=True)
    nombre_seguro = re.sub(r"[^A-Za-z0-9_.-]+", "_", (factura.nombre or "factura").strip())
    nombre_archivo = "%s_facturae_3_2_2.xml" % nombre_seguro
    return bytes_xml, nombre_archivo


def _fe_etiqueta(nombre_etiqueta):
    return "{%s}%s" % (ESPACIO_NOMBRES_FACTURAE, nombre_etiqueta)


def _fe_agregar(nodo_padre, nombre_etiqueta, texto=None):
    nodo = ET.SubElement(nodo_padre, _fe_etiqueta(nombre_etiqueta))
    if texto is not None:
        nodo.text = str(texto)
    return nodo


def _fe_agregar_importe(nodo_padre, nombre_etiqueta, importe):
    nodo_importe = _fe_agregar(nodo_padre, nombre_etiqueta)
    _fe_agregar(nodo_importe, "TotalAmount", _fe_decimal(Decimal(str(importe))))
    return nodo_importe


def _fe_decimal(valor, decimales=8):
    cuantizador = Decimal("1." + ("0" * decimales))
    valor_normalizado = Decimal(str(valor)).quantize(cuantizador, rounding=ROUND_HALF_UP)
    texto = format(valor_normalizado, "f").rstrip("0").rstrip(".")
    return texto if texto else "0"


def _fe_construir_parte(
    nodo_padre,
    nombre_nodo,
    nombre,
    nif,
    direccion,
    cp,
    ciudad,
    provincia,
    telefono,
    email,
):
    parte = _fe_agregar(nodo_padre, nombre_nodo)
    fiscal = _fe_agregar(parte, "TaxIdentification")
    _fe_agregar(fiscal, "PersonTypeCode", "J")
    _fe_agregar(fiscal, "ResidenceTypeCode", "R")
    _fe_agregar(fiscal, "TaxIdentificationNumber", (nif or "")[:30])

    entidad = _fe_agregar(parte, "LegalEntity")
    _fe_agregar(entidad, "CorporateName", (nombre or "")[:80])
    direccion_nacional = _fe_agregar(entidad, "AddressInSpain")
    _fe_agregar(direccion_nacional, "Address", (direccion or "")[:80])
    _fe_agregar(direccion_nacional, "PostCode", (cp or "")[:5])
    _fe_agregar(direccion_nacional, "Town", (ciudad or "")[:50])
    _fe_agregar(direccion_nacional, "Province", (provincia or "")[:20])
    _fe_agregar(direccion_nacional, "CountryCode", "ESP")

    if telefono or email:
        contacto = _fe_agregar(entidad, "ContactDetails")
        if telefono:
            _fe_agregar(contacto, "Telephone", re.sub(r"\s+", "", telefono)[:15])
        if email:
            _fe_agregar(contacto, "ElectronicMail", email[:60])
