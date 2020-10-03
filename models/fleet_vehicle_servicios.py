# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.osv import expression


class FleetVehicleProductLine(models.Model):
  """Task Line Model."""

  _name = 'fleet.vehicle.product.line'
  _description = 'Linea de producto'

  # task_id = fields.Many2one('service.task',
  #   string='task reference')
  fleet_service_id = fields.Many2one('fleet.vehicle.log.services',
    string='Servicio')
  product_id = fields.Many2one('product.product', string='Producto')
  qty_hand = fields.Float(string='Cantidad en mano',
    help='Cantidad en mano')
  qty = fields.Float(string='Usado', default=1.0)
  product_uom = fields.Many2one('uom.uom', string='UOM')
  price_unit = fields.Float(string='Costo Unidad')
  total = fields.Float(string='Costo total')
  date_issued = fields.Datetime(string='Fecha emisión')
  issued_by = fields.Many2one('res.users', string='Emitido por',
    default=lambda self: self._uid)
  is_deliver = fields.Boolean(string="Fue entregada?")


  @api.constrains('qty', 'qty_hand')
  def _check_used_qty(self):
    for rec in self:
      if rec.qty <= 0:
        raise Warning(_('You can\'t '
                        'enter used quanity as Zero!'))


  @api.onchange('product_id', 'qty')
  def _onchage_product(self):
    for rec in self:
      if rec.product_id:
        prod = rec.product_id
        # if prod.in_active_part:
        #   rec.product_id = False
        #   raise Warning(_('You can\'t select '
        #                   'part which is In-Active!'))
        rec.qty_hand = prod.qty_available or 0.0
        rec.product_uom = prod.uom_id or False
        rec.price_unit = prod.list_price or 0.0
      if rec.qty and rec.price_unit:
        rec.total = rec.qty * rec.price_unit


  @api.onchange('price_unit')
  def _onchange_price_unit(self):
    for rec in self:
      if rec.qty and rec.price_unit:
        rec.total = rec.qty * rec.price_unit


class FleetVehicleLogServices(models.Model):
  _inherit = 'fleet.vehicle.log.services'
  _name = 'fleet.vehicle.log.services'
  _order = 'date desc, name_seq desc'

  @api.model
  def default_get(self, default_fields):
    res = super().default_get(default_fields)
    service = self.env.ref('fleet-adicionales.type_service_service_8', raise_if_not_found=False)
    dt = fields.Date.context_today(self)
    res.update({'date': dt, 'cost_subtype_id': service and service.id or False, 'cost_type': 'services'})

    return res
  @api.depends('parts_ids')
  def _compute_get_total(self):
      for rec in self:
          total = 0.0
          for line in rec.parts_ids:
              total += line.total
          rec.sub_total = total

  name_seq = fields.Char(string='Consecutivo',
                         required=True,
                         copy=False,
                         readonly=True,
                         index=True,
                         default=lambda self: _('New'))

  documentos_ids = fields.Many2many('ir.attachment',
                                    'fleet_vehicle_service_attachment_rel',
                                    'service_id', 'attachment_id',
                                    string='Documentos Servicio')
  parts_ids = fields.One2many('fleet.vehicle.product.line', 'fleet_service_id',
    string='Parts')
  sub_total = fields.Float(compute="_compute_get_total", string='Total de partes',
    store=True)

  @api.model
  def create(self, vals):
    if vals.get('name_seq', _('New')) == _('New'):
      vals['name_seq'] = self.env['ir.sequence'].next_by_code('fleet-adicionales.service_log.sequence') or _('New')
    result = super(FleetVehicleLogServices, self).create(vals)
    return (result)

  @api.onchange('vehicle_id')
  def _onchange_vehicle(self):
    for rec in self:
      if rec.vehicle_id:
        rec.odometer_unit = rec.vehicle_id.odometer_unit
        rec.purchaser_id = rec.vehicle_id.driver_id.id
        rec.driver_id = rec.vehicle_id.driver_id.id
        trabajo_det = rec.env['fleet.vehicle.work'].search([
          ('state', '=', 'activo'),
          ('detalle_ids.vehicle_id.id', '=', rec.vehicle_id.id)],
          order="fecha_inicio desc",
          limit=1)
        if trabajo_det:
          rec.work_id = trabajo_det.id

  def name_get(self):
    res = []
    for field in self:
      res.append((field.id, '%s (%s) [%s]' % (field.name_seq, field.date or "", field.odometer or "")))
    return res