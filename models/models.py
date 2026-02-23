# -*- coding: utf-8 -*-

import base64
import re
from decimal import Decimal, ROUND_HALF_UP
from xml.etree import ElementTree as ET

from odoo import _, api, fields, models
from odoo.exceptions import UserError


ESPACIO_NOMBRES_FACTURAE = "http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml"

CODIGO_ALPHA3_POR_ALPHA2 = {
    "ES": "ESP", "FR": "FRA", "PT": "PRT", "IT": "ITA", "DE": "DEU",
    "GB": "GBR", "US": "USA", "MX": "MEX", "AR": "ARG", "CL": "CHL",
    "CO": "COL", "PE": "PER", "UY": "URY", "BR": "BRA", "CN": "CHN",
    "JP": "JPN", "KR": "KOR", "IN": "IND",
}


class MiModulo(models.Model):
    _name = "mi_modulo.mi_modulo"
    _description = "Registro base de ejemplo"

    nombre = fields.Char(string="Nombre")
    valor = fields.Integer(string="Valor")
    porcentaje_valor = fields.Float(
        string="Porcentaje",
        compute="_calcular_porcentaje_valor",
        store=True,
    )
    descripcion = fields.Text(string="Descripcion")

    @api.depends("valor")
    def _calcular_porcentaje_valor(self):
        for registro in self:
            registro.porcentaje_valor = float(registro.valor) / 100


class Usuario(models.Model):
    _name = "mi_modulo.usuario"
    _description = "Usuario"

    nombre = fields.Char(string="Nombre", required=True)
    edad = fields.Integer(string="Edad")
    descripcion = fields.Text(string="Descripcion")
    telefono = fields.One2many(
        "mi_modulo.telefono",
        "usuario_id",
        string="Telefonos",
    )


class Telefono(models.Model):
    _name = "mi_modulo.telefono"
    _description = "Telefono"

    numero = fields.Char(string="Numero", required=True)
    tipo = fields.Selection(
        [
            ("movil", "Movil"),
            ("fijo", "Fijo"),
        ],
        string="Tipo",
        default="movil",
    )
    usuario_id = fields.Many2one(
        "mi_modulo.usuario",
        string="Usuario",
        ondelete="cascade",
    )


class Factura(models.Model):
    _name = "mi_modulo.factura"
    _description = "Factura"
    _order = "fecha desc, id desc"

    nombre = fields.Char(string="Numero", default="Nueva", readonly=True, copy=False)
    fecha = fields.Date(string="Fecha", default=fields.Date.context_today, required=True)
    fecha_vencimiento = fields.Date(string="Fecha de vencimiento")
    estado = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("publicada", "Publicada"),
            ("cancelada", "Cancelada"),
        ],
        string="Estado",
        default="borrador",
        required=True,
    )
    moneda = fields.Char(string="Moneda", default="EUR", required=True)

    emisor_nombre = fields.Char(string="Emisor - Nombre", required=True)
    emisor_nif = fields.Char(string="Emisor - NIF/CIF", required=True)
    emisor_direccion = fields.Char(string="Emisor - Direccion", required=True)
    emisor_cp = fields.Char(string="Emisor - Codigo postal", required=True)
    emisor_ciudad = fields.Char(string="Emisor - Ciudad", required=True)
    emisor_provincia = fields.Char(string="Emisor - Provincia", required=True)
    emisor_pais = fields.Char(string="Emisor - Pais (alpha-2)", default="ES", required=True)
    emisor_telefono = fields.Char(string="Emisor - Telefono")
    emisor_email = fields.Char(string="Emisor - Email")

    receptor_nombre = fields.Char(string="Receptor - Nombre", required=True)
    receptor_nif = fields.Char(string="Receptor - NIF/CIF", required=True)
    receptor_direccion = fields.Char(string="Receptor - Direccion", required=True)
    receptor_cp = fields.Char(string="Receptor - Codigo postal", required=True)
    receptor_ciudad = fields.Char(string="Receptor - Ciudad", required=True)
    receptor_provincia = fields.Char(string="Receptor - Provincia", required=True)
    receptor_pais = fields.Char(string="Receptor - Pais (alpha-2)", default="ES", required=True)
    receptor_telefono = fields.Char(string="Receptor - Telefono")
    receptor_email = fields.Char(string="Receptor - Email")

    linea_ids = fields.One2many("mi_modulo.factura.linea", "factura_id", string="Lineas")
    subtotal = fields.Float(string="Subtotal", compute="_calcular_totales", store=True)
    total_impuestos = fields.Float(string="Impuestos", compute="_calcular_totales", store=True)
    total = fields.Float(string="Total", compute="_calcular_totales", store=True)
    notas = fields.Text(string="Notas")

    facturae_xml_datos = fields.Binary(string="Facturae XML", copy=False, readonly=True)
    facturae_xml_nombre_archivo = fields.Char(
        string="Nombre archivo Facturae",
        copy=False,
        readonly=True,
    )

    @api.model
    def create(self, vals):
        if vals.get("nombre", "Nueva") == "Nueva":
            vals["nombre"] = self.env["ir.sequence"].next_by_code("mi_modulo.factura") or "FACT-00001"
        return super().create(vals)

    @api.depends("linea_ids.subtotal", "linea_ids.impuesto", "linea_ids.total")
    def _calcular_totales(self):
        for factura in self:
            factura.subtotal = sum(factura.linea_ids.mapped("subtotal"))
            factura.total_impuestos = sum(factura.linea_ids.mapped("impuesto"))
            factura.total = sum(factura.linea_ids.mapped("total"))

    def action_publicar(self):
        for factura in self:
            if not factura.linea_ids:
                raise UserError(_("Debes agregar al menos una linea antes de publicar la factura."))
            factura.estado = "publicada"

    def action_borrador(self):
        self.write({"estado": "borrador"})

    def action_cancelar(self):
        self.write({"estado": "cancelada"})

    def action_imprimir_factura_pdf(self):
        self.ensure_one()
        return self.env.ref("mi_modulo.action_report_factura_pdf").report_action(self)

    def action_generar_facturae_xml(self):
        self.ensure_one()
        self._facturae_validar()

        bytes_xml, nombre_archivo = self._construir_facturae_322_xml()
        self.write(
            {
                "facturae_xml_datos": base64.b64encode(bytes_xml),
                "facturae_xml_nombre_archivo": nombre_archivo,
            }
        )
        return self.action_descargar_facturae_xml()

    def action_descargar_facturae_xml(self):
        self.ensure_one()
        if not self.facturae_xml_datos:
            raise UserError(_("Primero genera el XML Facturae."))

        url_descarga = (
            "/web/content/?model=mi_modulo.factura&id=%s&field=facturae_xml_datos"
            "&filename_field=facturae_xml_nombre_archivo&download=true"
        ) % self.id
        return {"type": "ir.actions.act_url", "url": url_descarga, "target": "self"}

    def _facturae_validar(self):
        self.ensure_one()
        if self.estado != "publicada":
            raise UserError(_("La factura debe estar publicada antes de generar Facturae."))
        if not self.linea_ids:
            raise UserError(_("La factura debe tener al menos una linea."))
        if len((self.moneda or "").strip()) != 3:
            raise UserError(_("La moneda debe ser un codigo ISO-4217 valido (por ejemplo, EUR)."))

        self._validar_bloque_tercero(
            self.emisor_nombre,
            self.emisor_nif,
            self.emisor_direccion,
            self.emisor_cp,
            self.emisor_ciudad,
            self.emisor_provincia,
            self.emisor_pais,
            "Emisor",
        )
        self._validar_bloque_tercero(
            self.receptor_nombre,
            self.receptor_nif,
            self.receptor_direccion,
            self.receptor_cp,
            self.receptor_ciudad,
            self.receptor_provincia,
            self.receptor_pais,
            "Receptor",
        )

    def _validar_bloque_tercero(
        self,
        nombre,
        nif,
        direccion,
        cp,
        ciudad,
        provincia,
        pais,
        etiqueta,
    ):
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
        if not pais:
            faltantes.append("pais")

        if faltantes:
            raise UserError(
                _("%s: faltan datos obligatorios para Facturae: %s")
                % (etiqueta, ", ".join(faltantes))
            )

    def _construir_facturae_322_xml(self):
        self.ensure_one()
        ET.register_namespace("", ESPACIO_NOMBRES_FACTURAE)

        fecha_emision = self.fecha or fields.Date.context_today(self)
        codigo_moneda = (self.moneda or "EUR").upper()
        subtotal = Decimal(str(self.subtotal))
        impuestos = Decimal(str(self.total_impuestos))
        total = Decimal(str(self.total))

        raiz = ET.Element(self._fe_etiqueta("Facturae"))
        cabecera_fichero = self._fe_agregar(raiz, "FileHeader")
        self._fe_agregar(cabecera_fichero, "SchemaVersion", "3.2.2")
        self._fe_agregar(cabecera_fichero, "Modality", "I")
        self._fe_agregar(cabecera_fichero, "InvoiceIssuerType", "EM")

        lote = self._fe_agregar(cabecera_fichero, "Batch")
        self._fe_agregar(lote, "BatchIdentifier", ("%s%s" % (self.emisor_nif, self.nombre))[:70])
        self._fe_agregar(lote, "InvoicesCount", "1")
        self._fe_agregar_importe(lote, "TotalInvoicesAmount", total)
        self._fe_agregar_importe(lote, "TotalOutstandingAmount", total)
        self._fe_agregar_importe(lote, "TotalExecutableAmount", total)
        self._fe_agregar(lote, "InvoiceCurrencyCode", codigo_moneda)

        partes = self._fe_agregar(raiz, "Parties")
        self._fe_construir_parte(
            partes,
            "SellerParty",
            self.emisor_nombre,
            self.emisor_nif,
            self.emisor_direccion,
            self.emisor_cp,
            self.emisor_ciudad,
            self.emisor_provincia,
            self.emisor_pais,
            self.emisor_telefono,
            self.emisor_email,
        )
        self._fe_construir_parte(
            partes,
            "BuyerParty",
            self.receptor_nombre,
            self.receptor_nif,
            self.receptor_direccion,
            self.receptor_cp,
            self.receptor_ciudad,
            self.receptor_provincia,
            self.receptor_pais,
            self.receptor_telefono,
            self.receptor_email,
        )

        facturas = self._fe_agregar(raiz, "Invoices")
        factura = self._fe_agregar(facturas, "Invoice")
        cabecera_factura = self._fe_agregar(factura, "InvoiceHeader")
        self._fe_agregar(cabecera_factura, "InvoiceNumber", (self.nombre or "")[:20])
        self._fe_agregar(cabecera_factura, "InvoiceDocumentType", "FC")
        self._fe_agregar(cabecera_factura, "InvoiceClass", "OO")

        datos_emision = self._fe_agregar(factura, "InvoiceIssueData")
        self._fe_agregar(datos_emision, "IssueDate", fecha_emision.isoformat())
        self._fe_agregar(datos_emision, "InvoiceCurrencyCode", codigo_moneda)
        self._fe_agregar(datos_emision, "TaxCurrencyCode", codigo_moneda)
        self._fe_agregar(datos_emision, "LanguageName", "es")

        impuestos_repercutidos = self._fe_agregar(factura, "TaxesOutputs")
        mapa_impuestos = {}
        for linea in self.linea_ids:
            clave = self._fe_decimal(Decimal(str(linea.impuesto_pct)))
            if clave not in mapa_impuestos:
                mapa_impuestos[clave] = {"tipo": Decimal(str(linea.impuesto_pct)), "base": Decimal("0"), "cuota": Decimal("0")}
            mapa_impuestos[clave]["base"] += Decimal(str(linea.subtotal))
            mapa_impuestos[clave]["cuota"] += Decimal(str(linea.impuesto))

        for datos in mapa_impuestos.values():
            nodo_impuesto = self._fe_agregar(impuestos_repercutidos, "Tax")
            self._fe_agregar(nodo_impuesto, "TaxTypeCode", "01")
            self._fe_agregar(nodo_impuesto, "TaxRate", self._fe_decimal(datos["tipo"]))
            self._fe_agregar_importe(nodo_impuesto, "TaxableBase", datos["base"])
            self._fe_agregar_importe(nodo_impuesto, "TaxAmount", datos["cuota"])

        totales = self._fe_agregar(factura, "InvoiceTotals")
        self._fe_agregar(totales, "TotalGrossAmount", self._fe_decimal(subtotal))
        self._fe_agregar(totales, "TotalGrossAmountBeforeTaxes", self._fe_decimal(subtotal))
        self._fe_agregar(totales, "TotalTaxOutputs", self._fe_decimal(impuestos))
        self._fe_agregar(totales, "TotalTaxesWithheld", self._fe_decimal(Decimal("0")))
        self._fe_agregar(totales, "InvoiceTotal", self._fe_decimal(total))
        self._fe_agregar(totales, "TotalOutstandingAmount", self._fe_decimal(total))
        self._fe_agregar(totales, "TotalExecutableAmount", self._fe_decimal(total))

        items = self._fe_agregar(factura, "Items")
        for linea in self.linea_ids:
            linea_xml = self._fe_agregar(items, "InvoiceLine")
            self._fe_agregar(linea_xml, "ItemDescription", (linea.descripcion or "")[:2500])
            self._fe_agregar(linea_xml, "Quantity", self._fe_decimal(Decimal(str(linea.cantidad))))
            self._fe_agregar(linea_xml, "UnitPriceWithoutTax", self._fe_decimal(Decimal(str(linea.precio_unitario))))
            self._fe_agregar(linea_xml, "TotalCost", self._fe_decimal(Decimal(str(linea.subtotal))))
            self._fe_agregar(linea_xml, "GrossAmount", self._fe_decimal(Decimal(str(linea.subtotal))))

            impuestos_linea = self._fe_agregar(linea_xml, "TaxesOutputs")
            nodo_impuesto_linea = self._fe_agregar(impuestos_linea, "Tax")
            self._fe_agregar(nodo_impuesto_linea, "TaxTypeCode", "01")
            self._fe_agregar(nodo_impuesto_linea, "TaxRate", self._fe_decimal(Decimal(str(linea.impuesto_pct))))
            self._fe_agregar_importe(nodo_impuesto_linea, "TaxableBase", Decimal(str(linea.subtotal)))
            self._fe_agregar_importe(nodo_impuesto_linea, "TaxAmount", Decimal(str(linea.impuesto)))

        bytes_xml = ET.tostring(raiz, encoding="utf-8", xml_declaration=True)
        nombre_seguro = re.sub(r"[^A-Za-z0-9_.-]+", "_", (self.nombre or "factura").strip())
        nombre_archivo = "%s_facturae_3_2_2.xml" % nombre_seguro
        return bytes_xml, nombre_archivo

    def _facturae_codigo_pais_alpha3(self, codigo_alpha2):
        codigo = (codigo_alpha2 or "").upper()
        if codigo in CODIGO_ALPHA3_POR_ALPHA2:
            return CODIGO_ALPHA3_POR_ALPHA2[codigo]
        if len(codigo) == 3:
            return codigo
        raise UserError(_("El codigo de pais '%s' no es valido para Facturae.") % (codigo_alpha2,))

    def _fe_etiqueta(self, nombre_etiqueta):
        return "{%s}%s" % (ESPACIO_NOMBRES_FACTURAE, nombre_etiqueta)

    def _fe_agregar(self, nodo_padre, nombre_etiqueta, texto=None):
        nodo = ET.SubElement(nodo_padre, self._fe_etiqueta(nombre_etiqueta))
        if texto is not None:
            nodo.text = str(texto)
        return nodo

    def _fe_agregar_importe(self, nodo_padre, nombre_etiqueta, importe):
        nodo_importe = self._fe_agregar(nodo_padre, nombre_etiqueta)
        self._fe_agregar(nodo_importe, "TotalAmount", self._fe_decimal(Decimal(str(importe))))
        return nodo_importe

    def _fe_decimal(self, valor, decimales=8):
        cuantizador = Decimal("1." + ("0" * decimales))
        valor_normalizado = Decimal(str(valor)).quantize(cuantizador, rounding=ROUND_HALF_UP)
        texto = format(valor_normalizado, "f").rstrip("0").rstrip(".")
        return texto if texto else "0"

    def _fe_construir_parte(
        self,
        nodo_padre,
        nombre_nodo,
        nombre,
        nif,
        direccion,
        cp,
        ciudad,
        provincia,
        pais_alpha2,
        telefono,
        email,
    ):
        parte = self._fe_agregar(nodo_padre, nombre_nodo)
        fiscal = self._fe_agregar(parte, "TaxIdentification")
        self._fe_agregar(fiscal, "PersonTypeCode", "J")
        self._fe_agregar(fiscal, "ResidenceTypeCode", "R" if (pais_alpha2 or "").upper() == "ES" else "E")
        self._fe_agregar(fiscal, "TaxIdentificationNumber", (nif or "")[:30])

        entidad = self._fe_agregar(parte, "LegalEntity")
        self._fe_agregar(entidad, "CorporateName", (nombre or "")[:80])
        direccion_nacional = self._fe_agregar(entidad, "AddressInSpain")
        self._fe_agregar(direccion_nacional, "Address", (direccion or "")[:80])
        self._fe_agregar(direccion_nacional, "PostCode", (cp or "")[:5])
        self._fe_agregar(direccion_nacional, "Town", (ciudad or "")[:50])
        self._fe_agregar(direccion_nacional, "Province", (provincia or "")[:20])
        self._fe_agregar(direccion_nacional, "CountryCode", self._facturae_codigo_pais_alpha3(pais_alpha2))

        if telefono or email:
            contacto = self._fe_agregar(entidad, "ContactDetails")
            if telefono:
                self._fe_agregar(contacto, "Telephone", re.sub(r"\s+", "", telefono)[:15])
            if email:
                self._fe_agregar(contacto, "ElectronicMail", email[:60])


class FacturaLinea(models.Model):
    _name = "mi_modulo.factura.linea"
    _description = "Linea de factura"
    _order = "id asc"

    factura_id = fields.Many2one("mi_modulo.factura", string="Factura", required=True, ondelete="cascade")
    descripcion = fields.Char(string="Descripcion", required=True)
    cantidad = fields.Float(string="Cantidad", default=1.0, required=True)
    precio_unitario = fields.Float(string="Precio unitario", required=True)
    impuesto_pct = fields.Float(string="Impuesto (%)", default=21.0)
    subtotal = fields.Float(string="Subtotal", compute="_calcular_importes", store=True)
    impuesto = fields.Float(string="Impuesto", compute="_calcular_importes", store=True)
    total = fields.Float(string="Total", compute="_calcular_importes", store=True)

    @api.depends("cantidad", "precio_unitario", "impuesto_pct")
    def _calcular_importes(self):
        for linea in self:
            subtotal = float(linea.cantidad or 0.0) * float(linea.precio_unitario or 0.0)
            impuesto = subtotal * (float(linea.impuesto_pct or 0.0) / 100.0)
            linea.subtotal = subtotal
            linea.impuesto = impuesto
            linea.total = subtotal + impuesto
