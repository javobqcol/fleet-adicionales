# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.osv import expression
import pytz
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

Class FleetVehicleMaterial(models.Model):
  _name = 'fleet.vehicle.material'
  _description = 'Viajes a facturar realizados por la flota de camiones'
  name = fields.Char('Material')

class FleetVehiculeViaje(models.Model):
  _name = 'fleet.vehicle.viaje'
  _order = 'date desc'
  company_id = fields.Many2one('res.company', 'Compañia', default=lambda self: self.env.company)
  work_id = fields.Many2one('fleet.vehicle.work', 'Trabajo', domain="[('state', '=', 'activo')]")
  driver_id = fields.Many2one('res.partner', string='Conductor')
  vehicle_id = fields.Many2one('fleet.vehicle', string='Vehiculo')
  date = fields.Date(string='Fecha viaje')
  material_id = fields.Many2one('fleet.vehicle.material', 'Material Trasportado')
  km_recorridos = fields.Float('Kilometros recorridos', readonly=False, store=True, compute='_cantidad_viajes')
  m3 = fields.Float('Metros cubicos trasportados')
  viajes = fields.Integer('Cantidad de viaje', default=1)
  cantera_id = fields.Many2one('res.partner', 'Origen')
  destino_id = fields.Many2one('res.partner', 'Destino')
  recibo_cantera = fields.Char('Número recibo cantera')
  recibo_interno = fields.Char('Número recibo interno')
  Km_inicial = fields.Float('Kilometro inicial')
  Km_final = fields.Float('Kilometro Final')
  galones = fields.Float('Galones')
  descripcion = fields.Text(string='Notas',
    placeholder='Cualquier informacion pertinente respecto a los viajes del dia')

  @api.onchange('vehicle_id')
  def _onchange_vehicle(self):
    for rec in self:
      if rec.vehicle_id:
        rec.driver_id = rec.vehicle_id.driver_id
        trabajo_det = rec.env['fleet.vehicle.work'].search([
          ('state', '=', 'activo'),
          ('detalle_ids.vehicle_id.id', '=', rec.vehicle_id.id)],
          order="fecha_inicio desc",
          limit=1)
        if trabajo_det:
          rec.work_id = trabajo_det.id

  def _cantidad_viajes(self):
    for rec in self:
      km_recorridos = (rec.Km_final or 0) - (rec.Km_inicial or 0)
      if (rec.km_recorridos or 0) == 0:
        rec.km_recorridos = km_recorridos


