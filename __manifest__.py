# -*- coding: utf-8 -*-
{
    'name': "Mi Modulo Facturae",

    'summary': """
        Modulo para gestionar facturas y generar XML Facturae 3.2.2""",

    'description': """
        Modulo de ejemplo que incluye:
        - Gestion de usuarios y telefonos
        - Pantalla de facturas de cliente
        - Generacion y descarga de factura electronica Facturae 3.2.2
    """,

    'author': "Mi Empresa",
    'website': "https://www.miempresa.com",
    'license': 'LGPL-3',

    # Categoria usada para clasificar el modulo
    'category': 'Accounting',
    'version': '0.1',

    # Modulos necesarios para que este modulo funcione correctamente
    'depends': ['base'],

    # Datos que se cargan siempre
    'data': [
        'data/factura_sequence.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/invoice_views.xml',
        'views/factura_report.xml',
        'security/ir.model.access.csv',
    ],
    # Datos de demostracion
    'demo': [
        'demo/demo.xml',
    ],
}
