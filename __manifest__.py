# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'fleet_adicionales',
    'version' : '0.1',
    'sequence': 1,
    'category': 'Human Resources/Fleet',
    'website' : 'https://www.odoo.com/page/fleet',
    'summary' : 'Manage your fleet and track car costs',
    'description' : """
Vehicle, leasing, insurances, cost
==================================
With this module, Odoo helps you managing all your vehicles, the
contracts associated to those vehicle as well as services, fuel log
entries, costs and many other features necessary to the management 
of your fleet of vehicle(s)

Main Features
-------------
* Add vehicles to your fleet
* Manage contracts for vehicles
* Reminder when a contract reach its expiration date
* Add services, fuel log entry, odometer values for all vehicles
* Show all costs associated to a vehicle or to a type of service
* Analysis graph for costs
""",
    'depends': [
        'fleet',
        'web_widget_multi_image',
        'product',
        'l10n_co_toponyms',
    ],
    'data': [
        'views/fleet_vehicle_combustibles.xml',
        'views/fleet_vehicle.xml',
        'views/fleet_vehicle_contratos.xml',
        'views/fleet_vehicle_servicios.xml',
        'views/fleet_vehicle_terceros.xml',
        'views/fleet_vehicle_odometro.xml',
        'views/fleet_vehicle_trabajos.xml',
        'views/fleet_vehicle_viajes.xml',
        'views/res_config_settings_views.xml',
        'data/vehicle_type.xml',
        'data/vehicle_color.xml',
        'data/fleet_presicion.xml',
        'reports/report.xml',
        'reports/work_maquinaria.xml',
        'reports/monitor_part.xml',
        'data/transito.xml',
        'data/sequence.xml',
        'data/car_data.xml',
        'data/product.xml',
        'data/fleet_adicionales_data.xml',
        'data/licencia_res_partner.xml',
        'data/vehicle_template.xml',
        'security/fleet_security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,

}
