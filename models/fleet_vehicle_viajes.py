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
    domain="[('vehicle_type_id.code', '=', 'vehiculo')]",
    ondelete='restrict',
    required=True)
  work_id = fields.Many2one('fleet.vehicle.work', 'Trabajo',
    domain="[('state', '=', 'activo'), ('detalle_ids.vehicle_id', '=', vehicle_id)]", ondelete='restrict')
  driver_id = fields.Many2one('res.partner', string='Conductor', ondelete='restrict')
  date = fields.Date(string='Fecha viaje', required=True)
  material_id = fields.Many2one('fleet.vehicle.material', 'Material', ondelete='restrict')
  km_recorridos = fields.Float('Kilometros recorridos', readonly=False, store=True, compute='_cantidad_viajes')
  m3 = fields.Float(string='Cantidad',
    compute='_diferencia',
    readonly=False,
    store=True,
    digits='Volume',
    help='Cantidad transportada por viaje')
  inicial = fields.Float(string='Inicial', digits='Volume', help='Peso vacio')
  final = fields.Float(string='Final', digits='Volume', help='Peso cargado', copy=False)
  unidad = fields.Selection([
    ('m3', 'Metro cubico'),
    ('ton', 'Tonelada'),
    ('Hor', 'Horas')
  ], 'Unidad', default='m3', help='Unidades de material trasportado', required=True)
  viajes = fields.Integer(string='Viajes', default=1, help="Cantidad e viajes", copy=False)
  cantera_id = fields.Many2one('res.partner', 'Origen', ondelete='restrict')
  destino_id = fields.Many2one('res.partner', 'Destino', ondelete='restrict')
  recibo_cantera = fields.Char(string='Recibo cantera', copy=False)
  recibo_interno = fields.Char(string='Recibo interno', copy=False)
  Km_inicial = fields.Float(string='Kilometro inicial', copy=False)
  Km_final = fields.Float(string='Kilometro Final', copy=False)
  galones = fields.Float(string='Galones', digits='Volume', copy=False)
  descripcion = fields.Text(string='Notas',
    placeholder='Cualquier informacion pertinente respecto a los viajes del dia', copy=False)
  total_cantidad = fields.Float(string='Total Trasp.',
    digits='Volume',
    readonly=False,
    store=True,
    compute='_total_material_trasportado')
  documentos_ids = fields.Many2many(
    'ir.attachment',
    'fleet_vehicle_viajes_attachment_rel',
    'viajes_id',
    'attachment_id',
    string='Recibos', copy=False)
  tiene_adjunto = fields.Boolean(compute='_set_adjunto')
  liq_id = fields.Many2one('fleet.vehicle.work.liq',
    'liquidacion Trabajo',
    domain="[('work_id','=',work_id)]", ondelete='restrict', copy=False)
  liq_driver_id = fields.Many2one('fleet.vehicle.driver.liq',
    'liquidacion Conductor',
    domain="[('driver_id','=',driver_id)]", ondelete='restrict', copy=False)

  @api.model
  def default_get(self, default_fields):
    res = super().default_get(default_fields)
    res.update({
        'inicial': self.vehicle_id.peso or 0
    })
    return res


  @api.depends('inicial', 'final')
  def _diferencia(self):
    for rec in self:
      if rec.unidad == 'ton':
        resultado = (rec.final or 0) - (rec.inicial or 0)
        rec.m3 = resultado if resultado > 0 else 0
      elif rec.unidad == 'm3':
        rec.m3 = rec.vehicle_id.cubicaje
      else:
        rec.m3 = 0.0

  def _set_adjunto(self):
    for reg in self:
      reg.tiene_adjunto = False
      if reg.documentos_ids:
        reg.tiene_adjunto = True

  @api.onchange('unidad')
  def _onchange_unidad(self):
    for reg in self:
      if reg.unidad == 'ton':
        reg.inicial = reg.vehicle_id.peso or 0
        reg.m3 = 0
      else:
        reg.m3 = reg.vehicle_id.cubicaje


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
      rec.km_recorridos = km_recorridos if km_recorridos > 0 else 0

  @api.depends('m3', 'viajes')
  def _total_material_trasportado(self):
    for rec in self:
      rec.total_cantidad = (rec.m3 or 0) * (rec.viajes or 0)

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
                     }
          res.update({'warning': warning})
      return res

  @api.onchange('recibo_cantera')
  def _onchange_recibo_cantera(self):
    res = {}
    for reg in self:
      if reg.recibo_cantera:
        reg.recibo_cantera = reg.recibo_cantera.upper()
        reg.recibo_cantera = " ".join(reg.recibo_cantera.split())
        hay_recibo = self.search([
          ('cantera_id', '=', reg.cantera_id.id),
          ('recibo_cantera', '=', reg.recibo_cantera),
          ('work_id', '=', reg.work_id.id),
        ])
        if hay_recibo:
          warning = {'title': 'Atención:',
                     'message': 'En el sistema hay un recibo de la cantera: %s, material %s, con el número %s'
                                % (hay_recibo.cantera_id.name or " ", hay_recibo.material_id.name or "", reg.recibo_cantera or ""),
                     }
          res.update({'warning': warning})
      return res