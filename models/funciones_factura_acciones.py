# -*- coding: utf-8 -*-

import base64

from odoo import _
from odoo.exceptions import UserError


def preparar_valores_creacion(modelo_factura, valores):
    if valores.get("nombre", "Nueva") == "Nueva":
        valores["nombre"] = modelo_factura.env["ir.sequence"].next_by_code("mi_modulo.factura") or "FACT-00001"
    return valores


def publicar_facturas(facturas):
    for factura in facturas:
        if not factura.linea_ids:
            raise UserError(_("Debes agregar al menos una linea antes de publicar la factura."))
        factura.estado = "publicada"


def pasar_facturas_a_borrador(facturas):
    facturas.write({"estado": "borrador"})


def cancelar_facturas(facturas):
    facturas.write({"estado": "cancelada"})


def imprimir_factura_pdf(factura):
    factura.ensure_one()
    compania = factura.env.company.sudo()
    if not compania.external_report_layout_id:
        layout_estandar = factura.env.ref("web.external_layout_standard", raise_if_not_found=False)
        if layout_estandar:
            compania.external_report_layout_id = layout_estandar.id
    return factura.env.ref("mi_modulo.action_report_factura_pdf").report_action(factura)


def generar_facturae_xml(factura):
    factura.ensure_one()
    factura._facturae_validar()

    bytes_xml, nombre_archivo = factura._construir_facturae_322_xml()
    factura.write(
        {
            "facturae_xml_datos": base64.b64encode(bytes_xml),
            "facturae_xml_nombre_archivo": nombre_archivo,
        }
    )
    return factura.action_descargar_facturae_xml()


def exportar_xml_factura(factura):
    factura.ensure_one()
    return generar_facturae_xml(factura)


def obtener_facturae_xml_texto(factura):
    factura.ensure_one()
    factura._facturae_validar()
    bytes_xml, _nombre_archivo = factura._construir_facturae_322_xml()
    return bytes_xml.decode("utf-8")


def descargar_facturae_xml(factura):
    factura.ensure_one()
    if not factura.facturae_xml_datos:
        raise UserError(_("Primero genera el XML Facturae."))

    url_descarga = (
        "/web/content/?model=mi_modulo.factura&id=%s&field=facturae_xml_datos"
        "&filename_field=facturae_xml_nombre_archivo&download=true"
    ) % factura.id
    return {"type": "ir.actions.act_url", "url": url_descarga, "target": "self"}
