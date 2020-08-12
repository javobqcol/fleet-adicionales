# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.osv import expression


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