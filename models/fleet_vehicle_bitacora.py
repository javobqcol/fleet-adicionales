# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError, Warning
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.osv import expression
import pytz
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class FleetVehiculebitacora(models.Model):
    _name = 'fleet.vehicle.bitacora'
    _order = 'date desc'

    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehiculo',
        domain="[('vehicle_type_id.code','in',['vehiculo', 'maquinaria'])]",
        ondelete='restrict',
        required=True
    )
    driver_id = fields.Many2one(
        comodel_name='res.partner',
        string='Conductor',
        ondelete='restrict'
    )
    date = fields.Date(
        string='Fecha viaje',
        required=True
    )
    work_id = fields.Many2one(
        comodel_name='fleet.vehicle.work',
        string='Trabajo',
        domain="[('state','=','activo'), ('detalle_ids.vehicle_id','=',vehicle_id)]",
        ondelete='restrict'
    )
    viajes = fields.Integer(
        string='Numero de viajes',
    )
    galones = fields.Float(
        string='Galones',
        digits='Volume',
        copy=False
    )
    nota = fields.Text(
        string='Notas',
        placeholder='Cualquier informacion pertinente respecto a los viajes del dia',
        copy=False
    )

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        for rec in self:
            rec.driver_id = rec.vehicle_id.driver_id