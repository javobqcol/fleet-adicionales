# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError, UserError, Warning
from dateutil.relativedelta import relativedelta
from odoo.osv import expression
import pytz
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging


class FleetVehicleAnalisis(models.Model):
    _name = 'fleet.vehicle.analisis'
    _auto = False
    _descripcion = 'analisis de viajes/horas maquina'

    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehiculo',
        readonly= True
    )
    name = fields.Char(
        string= 'Nombre del vehiculo',
        readonly=True
    )
    license_plate = fields.Char(
        string= 'placa',
        readonly=True
    )
    driver_id = fields.Many2one(
        comodel_name='res.partner',
        string='Conductor',
        readonly=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañia',
        readonly=True
    )
    work_id = fields.Many2one(
        comodel_name='fleet.vehicle.work',
        string='Trabajo',
        readonly=True
    )
    date = fields.Date(
        string='Fecha',
        readonly=True
    )
    state = fields.Selection(
        selection=[
            ('active', 'Activo'),
            ('inactive', 'Inactivo'),
            ('available', 'Disponible'),
            ('fuel', 'Combustible'),
            ('odometer', 'Odometro'),
            ('services', 'Servicio')],
        string='Estado',
        readonly=True
    )
    total = fields.Float(
        string='Total',
        readonly=True
    )
    liq_id = fields.Many2one(
        comodel_name='fleet.vehicle.work.liq',
        string='liquidacion Trabajo',
        readonly=True
    )
    liq_driver_id = fields.Many2one(
        comodel_name='fleet.vehicle.driver.liq',
        string='liquidacion Conductor',
        readonly=True
    )
    active = fields.Boolean(
        string='Activo',
        readonly=True
    )

    def init(self):
         tools.drop_view_if_exists(self.env.cr, 'product_vehicle_analisis')
         self.env.cr.execute("""
            CREATE OR REPLACE VIEW fleet_vehicle_analisis as (
                SELECT 
                    row_number() OVER () as id,
                    tabla.vehicle_id,
                    tabla.name,
                    tabla.license_plate,
                    tabla.vehicle_type_id, 
                    tabla.driver_id,
                    tabla.company_id,
                    tabla.work_id,
                    tabla.date,
                    tabla.state,
                    tabla.total,
                    tabla.liq_id,
                    tabla.liq_driver_id,
                    tabla.active
                    FROM (
                        SELECT 
                            fvo.vehicle_id AS vehicle_id,
                            fv.name AS name,
                            fv.license_plate AS license_plate,
                            fv.vehicle_type_id AS vehicle_type_id, 
                            fvo.driver_id AS driver_id,
                            fvo.company_id AS company_id,
                            fvo.work_id AS work_id,
                            fvo.date AS date,
                            fvo.tipo_odometro AS state,
                            fvo.total_unidades AS total,
                            fvo.liq_id AS liq_id,
                            fvo.liq_driver_id AS liq_driver_id,
                            fvo.active AS active
                            FROM 
                                fleet_vehicle AS fv  
                                JOIN 
                                    fleet_vehicle_odometer AS fvo 
                                    ON (
                                        fv.id = fvo.vehicle_id
                                    )
                            WHERE
                                fvo.tipo_odometro = 'odometer'
                        UNION
                        SELECT 
                            fvv.vehicle_id AS vehicle_id,
                            fv.name AS name,
                            fv.license_plate AS license_plate,
                            fv.vehicle_type_id AS vehicle_type_id, 
                            fvv.driver_id AS driver_id,
                            fvv.company_id AS company_id,
                            fvv.work_id AS work_id,
                            fvv.date AS date,
                            fvv.state AS state,
                            fvv.viaje::float AS total,
                            fvv.liq_id AS liq_id,
                            fvv.liq_driver_id AS liq_driver_id,
                            fvv.active AS active
                        FROM 
                            fleet_vehicle AS fv  
                            JOIN
                                fleet_vehicle_viaje AS fvv 
                                ON ( 
                                    fv.id = fvv.vehicle_id
                                ) 
                    ) AS tabla
            )
         """)