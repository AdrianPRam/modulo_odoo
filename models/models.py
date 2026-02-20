# -*- coding: utf-8 -*-

from odoo import models, fields, api


class mi_modulo(models.Model):
     _name = 'mi_modulo.mi_modulo'
     _description = 'mi_modulo.mi_modulo'

     name = fields.Char()
     value = fields.Integer()
     value2 = fields.Float(compute="_value_pc", store=True)
     description = fields.Text()

     @api.depends('value')
     def _value_pc(self):
         for record in self:
             record.value2 = float(record.value) / 100


class Usuario(models.Model):
    _name = 'mi_modulo.usuario'
    _description = 'Es el usuario'

    name = fields.Char(string='Nombre', required=True)
    age = fields.Integer(string='Edad')
    description = fields.Text(string='Descripción')

    telefono = fields.One2many(
        'mi_modulo.telefono',
        'usuario_id',
        string='Teléfonos'
    )

class Telefono(models.Model):
    _name = 'mi_modulo.telefono'
    _description = 'Teléfono'

    numero = fields.Char(string='Número', required=True)
    tipo = fields.Selection([
        ('movil', 'Móvil'),
        ('fijo', 'Fijo')
    ], string='Tipo')

    usuario_id = fields.Many2one(
        'mi_modulo.usuario',
        string='Usuario',
        ondelete='cascade'
    )
  
