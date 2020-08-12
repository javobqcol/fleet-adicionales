# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.osv import expression
import pytz
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class FleetVehicleMaterial(models.Model):
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
  viaje = fields.Integer('cantidad de viajes', readonly=True, compute='_cantidad_viajes')
  km = fields.Integer('kilometros recorridos', readonly=True, compute='_cantidad_viajes')
  descripcion=fields.Text(string='Notas', placeholder='Cualquier informacion pertinente respecto a los viajes del dia')
  viajedet_ids = fields.One2many('fleet.vehicle.viaje.det', 'viaje_id')



  def _cantidad_viajes(self):
    self.viaje = 0.0
    self.km= 0.0
    for record in self:
      total_viajes = [parts_line.id
                      for parts_line in record.viajedet_ids
                      if parts_line]
      record.viaje = len(total_viajes)
      # suma2 = 0.0
      # if record.viajedet_ids:
      #   for line in record.viajedet_ids:
      #     suma1 += 1
      #     suma2 += line.km_recorridos or 0.0
      # record.viaje = suma1
      # record.km = suma2

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


class FleetVehicleViajeDet(models.Model):
  _name = 'fleet.vehicle.viaje.det'
  _description = 'Viajes a facturar realizados por la flota de camiones detalle'

  viaje_id = fields.Many2one('fleet.vehicle.viaje', 'viajes')
  material_id = fields.Many2one('fleet.vehicle.material', 'Material Trasportado')
  km_recorridos = fields.Float('Kilometros recorridos')
  m3 = fields.Float('Metros cubicos trasportados')
  cantera_id = fields.Many2one('res.partner', 'Cantera')
  recibo_cantera = fields.Char('Número recibo cantera')
  recibo_interno = fields.Char('Número recibo interno')
  countrydesde_id = fields.Many2one('res.country', string='Pais origen', ondelete='restrict')
  statedesde_id = fields.Many2one("res.country.state", string='Departamento origen', ondelete='restrict',
    domain="[('country_id', '=', countrydesde_id)]")
  citydesde = fields.Char('Ubicacion detallada desde')
  countryhasta_id = fields.Many2one('res.country', string='Pais destino', ondelete='restrict')
  statehasta_id = fields.Many2one('res.country.state', string='Departamento destino', ondelete='restrict',
    domain="[('country_id', '=', countryhasta_id)]")
  cityhasta = fields.Char('Ubicacion detallada hasta')

  @api.model
  def default_get(self, default_fields):
    res = super().default_get(default_fields)
    country = self.env.ref('base.co', raise_if_not_found=False)
    res.update({
      'countrydesde_id': country and country.id or False,
      'countryhasta_id': country and country.id or False
    })
    return res
