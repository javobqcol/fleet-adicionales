# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError, Warning
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
  vehicle_id = fields.Many2one('fleet.vehicle',
    string='Vehiculo',
    domain="[('vehicle_type_id.code', '=', 'vehiculo')]")
  work_id = fields.Many2one('fleet.vehicle.work', 'Trabajo',
    domain="[('state', '=', 'activo'), ('detalle_ids.vehicle_id', '=', vehicle_id)]")
  driver_id = fields.Many2one('res.partner', string='Conductor')
  date = fields.Date(string='Fecha viaje')
  material_id = fields.Many2one('fleet.vehicle.material', 'Material')
  km_recorridos = fields.Float('Kilometros recorridos', readonly=False, store=True, compute='_cantidad_viajes')
  m3 = fields.Float(string='Cantidad material', digits='Volume', help='Cantidad material transportado')
  unidad = fields.Selection([
    ('m3', 'Metro cubico'),
    ('ton', 'Tonelada'),
    ('Hor', 'Horas')
  ], 'Unidades material', default='m3', help='Unidades de material trasportado', required=True)
  viajes = fields.Integer(string='Viajes', default=1, help="Cantidad e viajes")
  cantera_id = fields.Many2one('res.partner', 'Origen')
  destino_id = fields.Many2one('res.partner', 'Destino')
  recibo_cantera = fields.Char(string='Recibo cantera')
  recibo_interno = fields.Char(string='Recibo interno')
  Km_inicial = fields.Float(string='Kilometro inicial')
  Km_final = fields.Float(string='Kilometro Final')
  galones = fields.Float(string='Galones', digits='Volume')
  descripcion = fields.Text(string='Notas',
    placeholder='Cualquier informacion pertinente respecto a los viajes del dia')
  total_cantidad = fields.Float(string='Cantidad',
    digits='Volume',
    readonly=False,
    store=True,
    compute='_total_material_trasportado')
  documentos_ids = fields.Many2many(
    'ir.attachment',
    'fleet_vehicle_viajes_attachment_rel',
    'viajes_id',
    'attachment_id',
    string='Recibos')
  tiene_adjunto = fields.Boolean(compute='_set_adjunto')
  liq_id = fields.Many2one('fleet.vehicle.work.liq',
    'liquidacion Trabajo',
    domain="[('work_id','=',work_id)]")
  liq_driver_id = fields.Many2one('fleet.vehicle.driver.liq',
    'liquidacion Conductor',
    domain="[('driver_id','=',driver_id)]")


  def _set_adjunto(self):
    for reg in self:
      reg.tiene_adjunto = False
      if reg.documentos_ids:
        reg.tiene_adjunto = True

  @api.onchange('vehicle_id')
  def _onchange_vehicle(self):
    for rec in self:
      rec.driver_id = rec.vehicle_id.driver_id
      if not rec.m3:
        rec.m3 = rec.vehicle_id.cubicaje

  def name_get(self):
    res = []
    for field in self:
      res.append((field.id, '%s (%s)' % (field.work_id.alias_work, field.vehicle_id.name)))
    return res

  @api.depends('Km_inicial','Km_final')
  def _cantidad_viajes(self):
    for rec in self:
      km_recorridos = (rec.Km_final or 0) - (rec.Km_inicial or 0)
      rec.km_recorridos = km_recorridos

  @api.depends('m3', 'viajes')
  def _total_material_trasportado(self):
    for rec in self:
      total = (rec.m3 or 0) * (rec.viajes or 0)
      rec.total_cantidad = total

  @api.constrains('date', 'cantera_id', 'destino_id')
  def _onchange_date(self):
    for record in self:
      if record.date > fields.Date.context_today(record):
        raise ValidationError("Error, inconsistente registrar viajes a futuro")
      if not record.date:
        raise ValidationError("Error, Debe dar un valor de fecha")
      if not record.cantera_id:
        raise ValidationError("Error, Debe dar un valor de origen")
      if not record.destino_id:
        raise ValidationError("Error, Debe dar un valor de destino, si es viaje interno "
                              "especifique destino igual al origen")

  @api.onchange('date')
  def _onchange_date(self):
    for record in self:
      if record.date:
        fecha_actual = fields.Date.context_today(record)
        if record.date > fecha_actual:
          return {
            'warning': {'title': 'Error:',
                        'message': 'No se pueden dar viajes a futuro', },
            'value': {'date': fecha_actual},
          }

  @api.onchange('recibo_cantera')
  def _onchange_recibo_cantera(self):
    for reg in self:
      if reg.recibo_cantera:
        reg.recibo_cantera = reg.recibo_cantera.upper()
        reg.recibo_cantera = " ".join(reg.recibo_cantera.split())


  @api.onchange('recibo_interno')
  def _onchange_recibo_interno(self):
    res = {}
    for reg in self:
      if reg.recibo_interno:
        reg.recibo_interno = reg.recibo_interno.upper()
        reg.recibo_interno = " ".join(reg.recibo_interno.split())
        hay_recibo = self.search([
          ('recibo_interno', '=', reg.recibo_interno),
          ('work_id', '=', reg.work_id.id),
        ])
        if hay_recibo:
          warning = {'title': 'Atención:',
                     'message': 'En el sistema hay un recibo  de %s con el numero %s'
                                % (hay_recibo.material_id.name or "", reg.recibo_interno or ""),
                     'type': 'notification'}
          res.update({'warning': warning})
      return res

