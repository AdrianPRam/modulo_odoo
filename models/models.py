# -*- coding: utf-8 -*-

from odoo import api, fields, models

from . import calculos_modelo
from . import funciones_factura_acciones
from . import funciones_factura_validacion
from . import funciones_facturae_xml


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
        calculos_modelo.calcular_porcentaje_valor(self)


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
    emisor_pais = fields.Char(string="Emisor - Pais", default="Espana")
    emisor_telefono = fields.Char(string="Emisor - Telefono")
    emisor_email = fields.Char(string="Emisor - Email")

    receptor_nombre = fields.Char(string="Receptor - Nombre", required=True)
    receptor_nif = fields.Char(string="Receptor - NIF/CIF", required=True)
    receptor_direccion = fields.Char(string="Receptor - Direccion", required=True)
    receptor_cp = fields.Char(string="Receptor - Codigo postal", required=True)
    receptor_ciudad = fields.Char(string="Receptor - Ciudad", required=True)
    receptor_provincia = fields.Char(string="Receptor - Provincia", required=True)
    receptor_pais = fields.Char(string="Receptor - Pais", default="Espana")
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
    def create(self, valores):
        valores = funciones_factura_acciones.preparar_valores_creacion(self, valores)
        return super().create(valores)

    @api.depends("linea_ids.subtotal", "linea_ids.impuesto", "linea_ids.total")
    def _calcular_totales(self):
        calculos_modelo.calcular_totales_factura(self)

    def action_publicar(self):
        return funciones_factura_acciones.publicar_facturas(self)

    def action_borrador(self):
        return funciones_factura_acciones.pasar_facturas_a_borrador(self)

    def action_cancelar(self):
        return funciones_factura_acciones.cancelar_facturas(self)

    def action_imprimir_factura_pdf(self):
        return funciones_factura_acciones.imprimir_factura_pdf(self)

    def action_generar_facturae_xml(self):
        return funciones_factura_acciones.generar_facturae_xml(self)

    def action_exportar_xml(self):
        return funciones_factura_acciones.exportar_xml_factura(self)

    def _obtener_facturae_xml_texto(self):
        return funciones_factura_acciones.obtener_facturae_xml_texto(self)

    def action_descargar_facturae_xml(self):
        return funciones_factura_acciones.descargar_facturae_xml(self)

    def _facturae_validar(self):
        return funciones_factura_validacion.validar_facturae(self)

    def _validar_bloque_tercero(self, nombre, nif, direccion, cp, ciudad, provincia, etiqueta):
        return funciones_factura_validacion.validar_bloque_tercero(
            nombre, nif, direccion, cp, ciudad, provincia, etiqueta
        )

    def _construir_facturae_322_xml(self):
        return funciones_facturae_xml.construir_facturae_322_xml(self)


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
        calculos_modelo.calcular_importes_linea(self)
